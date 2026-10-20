from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .answer import ABSTAIN, deterministic_answer
from .change_impact import assess_change_impact
from .io import read_json, read_jsonl
from .paths import CHUNKS_PATH, EVAL_PATH, MANIFEST_PATH, REPORT_PATH, SUMMARY_PATH
from .retrieval import LocalTfidfRetriever


def load_manifest() -> list[dict[str, Any]]:
    value = read_json(MANIFEST_PATH)
    return value if isinstance(value, list) else []


def load_chunks() -> list[dict[str, Any]]:
    return read_jsonl(CHUNKS_PATH)


def load_eval_records() -> list[dict[str, Any]]:
    return read_jsonl(EVAL_PATH)


def load_evaluation_report() -> dict[str, Any]:
    if not REPORT_PATH.exists():
        return {}
    value = read_json(REPORT_PATH)
    return value if isinstance(value, dict) else {}


def load_test_summary() -> str:
    return SUMMARY_PATH.read_text(encoding="utf-8") if SUMMARY_PATH.exists() else ""


def runtime_summary() -> dict[str, Any]:
    manifest = load_manifest()
    chunks = load_chunks()
    eval_records = load_eval_records()
    indexed_source_ids = sorted({chunk["source_id"] for chunk in chunks})
    non_indexed = [source for source in manifest if source.get("source_id") not in indexed_source_ids]
    return {
        "product_name": "LabelAI Regulatory Knowledge Prototype",
        "description": "Evidence-grounded labeling review workflow for illustrative medical-device changes.",
        "indexed_chunks": len(chunks),
        "indexed_sources": len(indexed_source_ids),
        "indexed_source_ids": indexed_source_ids,
        "manifest_sources": len(manifest),
        "non_indexed_sources": non_indexed,
        "evaluation_questions": len(eval_records),
        "answerable_questions": sum(1 for row in eval_records if row.get("answerable_from_corpus")),
        "unanswerable_questions": sum(1 for row in eval_records if not row.get("answerable_from_corpus")),
        "evaluation_report": load_evaluation_report(),
        "test_summary": load_test_summary(),
    }


def build_change_request(
    change_id: str,
    product_name: str,
    device_category: str,
    target_market: str,
    change_category: str,
    change_description: str,
    current_label_elements: list[str],
    optional_context: str = "",
    reviewer_notes: str = "",
    approved_product_facts: dict[str, Any] | None = None,
    existing_label_version: str | None = None,
) -> dict[str, Any]:
    product_context: dict[str, Any] = {
        "product": product_name,
        "market": target_market,
        "device_type": device_category,
        "change_category": change_category,
        "data_classification": "fictional demo input; no patient data",
    }
    if optional_context.strip():
        product_context["additional_context"] = optional_context.strip()
    if reviewer_notes.strip():
        product_context["reviewer_notes"] = reviewer_notes.strip()
    req: dict[str, Any] = {
        "change_id": change_id,
        "product_context": product_context,
        "change_description": change_description,
        "current_label_elements": current_label_elements,
    }
    if approved_product_facts:
        req["approved_product_facts"] = approved_product_facts
    if existing_label_version:
        req["existing_label_version"] = existing_label_version
    return req



def run_change_impact(request: dict[str, Any]) -> dict[str, Any]:
    return assess_change_impact(request)


def result_to_json_bytes(result: dict[str, Any]) -> bytes:
    return (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def retrieved_evidence_for_question(question: str, top_k: int = 5, target_market: str | None = None) -> list[dict[str, Any]]:
    retriever = LocalTfidfRetriever.load()
    jurisdiction = None
    if target_market:
        normalized = target_market.strip().lower()
        if normalized in {"eu", "european union"}:
            jurisdiction = "European Union"
        elif normalized in {"international", "global"}:
            jurisdiction = "International"
        elif normalized in {"us", "united states", "usa"}:
            jurisdiction = "United States"
    results = retriever.search(question, top_k=top_k, jurisdiction=jurisdiction)
    evidence: list[dict[str, Any]] = []
    for result in results:
        chunk = asdict(result.chunk)
        evidence.append(
            {
                "rank": result.rank,
                "score": round(result.score, 4),
                "chunk_id": chunk["chunk_id"],
                "source_id": chunk["source_id"],
                "source_title": chunk["title"],
                "publisher": chunk["publisher"],
                "jurisdiction": chunk["jurisdiction"],
                "url": chunk["url"],
                "page": chunk["page"],
                "section": chunk["section"],
                "document_date": chunk.get("metadata", {}).get("document_date"),
                "excerpt": chunk["text"][:1200],
            }
        )
    return evidence


def ask_regulatory_question(question: str, target_market: str | None = None, top_k: int = 5) -> dict[str, Any]:
    if not question or not question.strip():
        raise ValueError("Question is required.")
    evidence = retrieved_evidence_for_question(question, top_k=top_k, target_market=target_market)
    retriever = LocalTfidfRetriever.load()
    jurisdiction = None
    normalized = (target_market or "").strip().lower()
    if normalized in {"eu", "european union"}:
        jurisdiction = "European Union"
    elif normalized in {"international", "global"}:
        jurisdiction = "International"
    elif normalized in {"us", "united states", "usa"}:
        jurisdiction = "United States"
    results = retriever.search(question, top_k=top_k, jurisdiction=jurisdiction)
    answer = deterministic_answer(question, results)
    insufficient = ABSTAIN in answer
    return {
        "question": question,
        "target_market": target_market,
        "answer": answer,
        "insufficient_evidence": insufficient,
        "evidence": evidence,
        "interpretation_note": "Source-backed retrieval summary only; qualified regulatory review is required.",
    }


def load_sample_change_request(path: Path | None = None) -> dict[str, Any]:
    sample_path = path or Path("data/change_impact/sample_change_request.json")
    return json.loads(sample_path.read_text(encoding="utf-8"))


def load_sample_existing_label(path: Path | None = None) -> dict[str, Any]:
    sample_path = path or Path("data/label_authoring/sample_existing_label.json")
    return json.loads(sample_path.read_text(encoding="utf-8"))


def load_sample_approved_facts(path: Path | None = None) -> dict[str, Any]:
    sample_path = path or Path("data/label_authoring/sample_approved_facts.json")
    return json.loads(sample_path.read_text(encoding="utf-8"))


def run_label_authoring(
    approved_product_facts: dict[str, Any],
    existing_label: dict[str, Any],
    target_jurisdiction: str = "US",
    impact_assessment: dict[str, Any] | None = None,
    requested_sections: list[str] | None = None,
    target_version: str | None = None,
) -> dict[str, Any]:
    from .label_authoring import draft_label_update, export_diff_to_markdown

    proposed_doc, report = draft_label_update(
        approved_product_facts=approved_product_facts,
        existing_label=existing_label,
        target_jurisdiction=target_jurisdiction,
        impact_assessment=impact_assessment,
        requested_sections_to_revise=requested_sections,
        target_version=target_version,
    )
    return {
        "proposed_label": proposed_doc.to_dict(),
        "comparison_report": report.to_dict(),
        "markdown_report": export_diff_to_markdown(report),
        "overall_human_review_required": True,
    }


def update_label_field_review(
    report_dict: dict[str, Any],
    field_id: str,
    decision: str,
    reviewer_notes: str = "",
) -> dict[str, Any]:
    from .label_authoring import export_diff_to_markdown, update_field_review_decision

    updated_report = update_field_review_decision(report_dict, field_id, decision, reviewer_notes)
    updated_report_dict = updated_report if isinstance(updated_report, dict) else updated_report.to_dict()
    return {
        "comparison_report": updated_report_dict,
        "markdown_report": export_diff_to_markdown(updated_report_dict),
    }

