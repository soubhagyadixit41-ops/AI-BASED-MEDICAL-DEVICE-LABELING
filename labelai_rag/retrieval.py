from __future__ import annotations

import pickle
import re
from dataclasses import asdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .io import read_jsonl
from .models import Chunk, RetrievalResult
from .paths import CHUNKS_PATH, INDEX_PATH


def chunk_from_row(row: dict) -> Chunk:
    return Chunk(**row)


class LocalTfidfRetriever:
    def __init__(self, chunks: list[Chunk], vectorizer: TfidfVectorizer, matrix) -> None:
        self.chunks = chunks
        self.vectorizer = vectorizer
        self.matrix = matrix

    @classmethod
    def from_chunks(cls, chunks: list[Chunk]) -> "LocalTfidfRetriever":
        docs = [
            f"{chunk.title}\n{chunk.jurisdiction}\n{chunk.section or ''}\n{chunk.text}"
            for chunk in chunks
        ]
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=50000)
        matrix = vectorizer.fit_transform(docs)
        return cls(chunks, vectorizer, matrix)

    @classmethod
    def load(cls) -> "LocalTfidfRetriever":
        with INDEX_PATH.open("rb") as handle:
            payload = pickle.load(handle)
        chunks = [chunk_from_row(row) for row in payload["chunks"]]
        return cls(chunks, payload["vectorizer"], payload["matrix"])

    def save(self) -> None:
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunks": [asdict(chunk) for chunk in self.chunks],
            "vectorizer": self.vectorizer,
            "matrix": self.matrix,
        }
        with INDEX_PATH.open("wb") as handle:
            pickle.dump(payload, handle)

    def search(self, question: str, top_k: int = 5, jurisdiction: str | None = None) -> list[RetrievalResult]:
        if not question or not question.strip():
            raise ValueError("Question must be a non-empty string.")
        query_vec = self.vectorizer.transform([question])
        raw_scores = cosine_similarity(query_vec, self.matrix).ravel()

        q_lower = question.lower()
        exact_terms = re.findall(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?|21\s+cfr\s+[0-9]+(?:\.[0-9]+)?", q_lower)

        boosted_scores: list[tuple[int, float]] = []
        for idx, base_score in enumerate(raw_scores):
            chunk = self.chunks[idx]
            score = float(base_score)
            chunk_text = f"{chunk.title} {chunk.jurisdiction} {chunk.section or ''} {chunk.text}".lower()

            # Exact section / clause number matching (e.g., 21 CFR 801.1, 5.2.9)
            for term in exact_terms:
                if term in chunk_text:
                    score += 0.35

            # Jurisdiction / source alignment boost to prevent cross-jurisdiction confusion
            if "imdrf" in q_lower and "fda" not in q_lower:
                if chunk.source_id.startswith("imdrf"):
                    score += 0.15
                elif chunk.source_id.startswith("fda"):
                    score -= 0.10
            elif "fda" in q_lower and "imdrf" not in q_lower:
                if chunk.source_id.startswith("fda"):
                    score += 0.15
                elif chunk.source_id.startswith("imdrf"):
                    score -= 0.10
            elif "eudamed" in q_lower or "emdn" in q_lower:
                if "ec_udi" in chunk.source_id:
                    score += 0.20

            boosted_scores.append((idx, score))

        ranked = sorted(boosted_scores, key=lambda item: item[1], reverse=True)
        results: list[RetrievalResult] = []
        for idx, score in ranked:
            chunk = self.chunks[idx]
            if jurisdiction and jurisdiction.lower() not in chunk.jurisdiction.lower():
                continue
            results.append(RetrievalResult(chunk=chunk, score=float(score), rank=len(results) + 1))
            if len(results) >= top_k:
                break
        return results


def build_index() -> LocalTfidfRetriever:
    chunks = [chunk_from_row(row) for row in read_jsonl(CHUNKS_PATH)]
    if not chunks:
        raise RuntimeError("No chunks available. Run ingestion first.")
    retriever = LocalTfidfRetriever.from_chunks(chunks)
    retriever.save()
    return retriever
