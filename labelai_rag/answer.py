from __future__ import annotations

import os
import re

from .models import RetrievalResult
from .retrieval import LocalTfidfRetriever


DISCLAIMER = "Informational only; requires qualified regulatory review and is not a regulatory compliance determination."
ABSTAIN = "Insufficient evidence in the indexed sources."

# Terms and topics known to be unindexed / outside corpus authority
UNAVAILABLE_SOURCE_TERMS = (
    "iso 15223",
    "iso 20417",
    "eur-lex",
    "mdr text",
    "india",
    "certif",
    "compliant",
    "cardiac stent",
    "data delimiter",
)

STOPWORDS = {
    "what", "does", "the", "say", "about", "page", "requirement", "requirements",
    "for", "and", "with", "from", "this", "under", "how", "can", "are", "which",
    "who", "should", "must", "where", "when", "why", "according", "document",
    "exact", "applies", "apply", "have", "been", "will", "would", "could", "also",
    "into", "than", "them", "then", "there", "these", "they", "that", "were",
    "general", "labeling", "label", "labels", "device", "devices", "medical",
    "fda", "imdrf", "guidance", "rule", "rules", "regulation", "regulations",
}


def requires_unavailable_source(question: str) -> bool:
    lower = question.lower()
    return any(term in lower for term in UNAVAILABLE_SOURCE_TERMS)


def _sentence_score(sentence: str, question_terms: set[str]) -> int:
    words = set(re.findall(r"[a-zA-Z0-9-]{3,}", sentence.lower()))
    return len(words & question_terms)


def deterministic_answer(question: str, results: list[RetrievalResult], min_score: float | None = None) -> str:
    threshold = min_score if min_score is not None else float(os.getenv("LABELAI_MIN_SCORE", "0.05"))
    if requires_unavailable_source(question):
        return f"{ABSTAIN}\n\n{DISCLAIMER}"

    # Filter out results below score threshold
    supported = [result for result in results if result.score >= threshold]
    if not supported:
        return f"{ABSTAIN}\n\n{DISCLAIMER}"

    # If asking specifically about FDA / US, require at least one US-grounded chunk
    q_lower = question.lower()
    if ("fda" in q_lower or "21 cfr" in q_lower) and "imdrf" not in q_lower and "compare" not in q_lower:
        us_chunks = [r for r in supported if "united states" in r.chunk.jurisdiction.lower()]
        if not us_chunks:
            return f"{ABSTAIN}\n\n{DISCLAIMER}"
        supported = us_chunks

    # Check that distinctive topic terms in the question appear in at least one retrieved chunk
    q_words = set(re.findall(r"[a-zA-Z0-9-]{3,}", q_lower))
    distinctive_terms = q_words - STOPWORDS
    if distinctive_terms:
        all_retrieved_text = " ".join(r.chunk.text.lower() for r in supported)
        if not any(term in all_retrieved_text for term in distinctive_terms):
            return f"{ABSTAIN}\n\n{DISCLAIMER}"

    question_terms = set(re.findall(r"[a-zA-Z0-9-]{3,}", q_lower))
    evidence_lines: list[str] = []
    for result in supported[:3]:
        sentences = re.split(r"(?<=[.!?])\s+", result.chunk.text)
        best = sorted(sentences, key=lambda s: _sentence_score(s, question_terms), reverse=True)[:2]
        quote = " ".join(s.strip() for s in best if s.strip())[:600]
        location = f"page {result.chunk.page}" if result.chunk.page else result.chunk.section or "section unavailable"
        evidence_lines.append(
            f"- {quote} [Source: {result.chunk.title}; {location}; {result.chunk.url}]"
        )
    return "Source-supported evidence:\n" + "\n".join(evidence_lines) + f"\n\n{DISCLAIMER}"


def answer_question(question: str, top_k: int = 5) -> str:
    retriever = LocalTfidfRetriever.load()
    return deterministic_answer(question, retriever.search(question, top_k=top_k))
