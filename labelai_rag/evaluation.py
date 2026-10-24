from __future__ import annotations

import json
from statistics import mean

from .answer import ABSTAIN, deterministic_answer
from .io import read_jsonl, write_json
from .paths import EVAL_PATH, REPORT_PATH, SUMMARY_PATH
from .retrieval import LocalTfidfRetriever


def key_fact_hit(text: str, facts: list[str]) -> bool:
    lower = text.lower()
    required = [fact.lower() for fact in facts if fact.strip()]
    if not required:
        return True
    return any(fact in lower for fact in required)


def evaluate(top_k: int = 5) -> dict:
    retriever = LocalTfidfRetriever.load()
    records = read_jsonl(EVAL_PATH)
    if not records:
        raise RuntimeError("No evaluation records found. Run make-eval first.")

    answerable = [row for row in records if row["answerable_from_corpus"]]
    unanswerable = [row for row in records if not row["answerable_from_corpus"]]
    recall_hits = 0
    reciprocal_ranks: list[float] = []
    citation_hits = 0
    key_fact_hits = 0
    abstention_hits = 0
    wrong_jurisdiction_flags = 0
    details: list[dict] = []

    for row in records:
        results = retriever.search(row["question"], top_k=top_k)
        returned_sources = [result.chunk.source_id for result in results]
        expected_sources = row["expected_source_ids"]
        relevant_ranks = [i + 1 for i, sid in enumerate(returned_sources) if sid in expected_sources]
        topk_hit = bool(relevant_ranks) if row["answerable_from_corpus"] else True
        if row["answerable_from_corpus"] and topk_hit:
            recall_hits += 1
            reciprocal_ranks.append(1.0 / min(relevant_ranks))
        elif row["answerable_from_corpus"]:
            reciprocal_ranks.append(0.0)

        retrieved_text = "\n".join(result.chunk.text for result in results)
        if row["answerable_from_corpus"] and key_fact_hit(retrieved_text, row["expected_key_facts"]):
            key_fact_hits += 1

        answer = deterministic_answer(row["question"], results)
        if row["answerable_from_corpus"]:
            if all(result.chunk.title and result.chunk.url for result in results[: min(3, len(results))]):
                citation_hits += 1
        elif ABSTAIN in answer:
            abstention_hits += 1

        if "compare" in row["question"].lower() and len(set(expected_sources)) > 1:
            missing = set(expected_sources) - set(returned_sources)
            if missing:
                wrong_jurisdiction_flags += 1

        details.append(
            {
                "question_id": row["question_id"],
                "top_sources": returned_sources,
                "top_scores": [round(result.score, 4) for result in results],
                "topk_expected_source_hit": topk_hit,
            }
        )

    report = {
        "evaluation_set_size": len(records),
        "answerable_questions": len(answerable),
        "unanswerable_questions": len(unanswerable),
        "top_k": top_k,
        "retrieval_recall_at_k": recall_hits / max(1, len(answerable)),
        "retrieval_mrr": mean(reciprocal_ranks) if reciprocal_ranks else 0.0,
        "retrieved_evidence_key_fact_hit_rate": key_fact_hits / max(1, len(answerable)),
        "citation_metadata_correctness": citation_hits / max(1, len(answerable)),
        "abstention_accuracy": abstention_hits / max(1, len(unanswerable)),
        "comparison_questions_missing_expected_source_count": wrong_jurisdiction_flags,
        "methodology": "TF-IDF retrieval over official-source chunks. Answerable metrics check whether expected source IDs and key facts appear in top-k retrieved passages. Abstention metric checks deterministic answer behavior for unanswerable records.",
        "limitations": [
            "Metrics are retrieval-grounded and deterministic; no paid LLM answer quality is claimed.",
            "ISO standards are metadata-only because the full standards are copyrighted/paywalled.",
            "EUR-Lex access can vary; the manifest records the actual download status.",
        ],
        "details": details,
    }
    write_json(REPORT_PATH, report)
    SUMMARY_PATH.write_text(
        "\n".join(
            [
                "# Round 1 Test Results Summary",
                "",
                f"Evaluation records: {report['evaluation_set_size']} ({report['answerable_questions']} answerable, {report['unanswerable_questions']} unanswerable)",
                f"Recall@{top_k}: {report['retrieval_recall_at_k']:.3f}",
                f"MRR: {report['retrieval_mrr']:.3f}",
                f"Evidence key-fact hit rate: {report['retrieved_evidence_key_fact_hit_rate']:.3f}",
                f"Citation metadata correctness: {report['citation_metadata_correctness']:.3f}",
                f"Abstention accuracy: {report['abstention_accuracy']:.3f}",
                "",
                "No LLM accuracy percentage is claimed; this report separates retrieval and abstention checks.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def print_report(report: dict) -> None:
    print(json.dumps(report, indent=2))
