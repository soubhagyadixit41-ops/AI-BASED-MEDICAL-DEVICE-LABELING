from __future__ import annotations

import json

import pytest

from labelai_rag import streamlit_service as svc
from labelai_rag.answer import ABSTAIN


def test_runtime_summary_uses_current_artifacts() -> None:
    summary = svc.runtime_summary()
    assert summary["indexed_chunks"] >= 1
    assert summary["indexed_sources"] >= 1
    assert summary["evaluation_questions"] >= 34
    assert "imdrf_grrp_wg_n52_2024" in summary["indexed_source_ids"]


def test_successful_change_impact_invocation_from_service() -> None:
    request = svc.load_sample_change_request()
    assessment = svc.run_change_impact(request)
    assert assessment["change_id"] == request["change_id"]
    assert assessment["affected_label_elements"]
    assert assessment["supporting_evidence"]
    assert assessment["human_review_required"] is True


def test_service_missing_or_invalid_change_fields() -> None:
    request = svc.build_change_request("", "", "", "", "", "", [])
    with pytest.raises(ValueError):
        svc.run_change_impact(request)


def test_empty_evidence_result_for_unmatched_change() -> None:
    request = svc.build_change_request(
        "DEMO-NO-MATCH",
        "illustrative cardiac stent",
        "illustrative medical device",
        "US",
        "Administrative",
        "Correct a typo in an internal training slide that is not labeling.",
        ["manufacturer name/address"],
    )
    assessment = svc.run_change_impact(request)
    assert assessment["affected_label_elements"] == []
    assert "manual triage" in " ".join(assessment["missing_information"]).lower()


def test_unsupported_target_market_disclosure() -> None:
    request = svc.build_change_request(
        "DEMO-INDIA",
        "illustrative cardiac stent",
        "illustrative medical device",
        "India",
        "Address update",
        "Manufacturer address updated.",
        ["manufacturer name/address"],
    )
    assessment = svc.run_change_impact(request)
    assert any("India" in item for item in assessment["source_coverage_limitations"])


def test_source_references_are_preserved() -> None:
    qa = svc.ask_regulatory_question("What does IMDRF say about manufacturer address?", "International")
    assert qa["evidence"]
    first = qa["evidence"][0]
    assert first["source_id"]
    assert first["source_title"]
    assert first["url"].startswith("https://")


def test_json_serialization_of_assessment_results() -> None:
    assessment = svc.run_change_impact(svc.load_sample_change_request())
    payload = svc.result_to_json_bytes(assessment)
    assert json.loads(payload.decode("utf-8"))["change_id"] == assessment["change_id"]


def test_insufficient_evidence_behavior_in_qa() -> None:
    qa = svc.ask_regulatory_question("What exact FDA rule applies to this US cardiac stent label?", "US")
    assert qa["insufficient_evidence"] is True
    assert ABSTAIN in qa["answer"]


def test_live_assessment_is_not_sample_fixture() -> None:
    request = svc.build_change_request(
        "LIVE-RUN-001",
        "illustrative cardiac stent",
        "illustrative medical device",
        "US",
        "Address update",
        "Manufacturer address updated.",
        ["manufacturer name/address"],
    )
    assessment = svc.run_change_impact(request)
    assert assessment["change_id"] == "LIVE-RUN-001"


def test_missing_optional_api_credentials_do_not_block_deterministic_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    qa = svc.ask_regulatory_question("What does IMDRF say a UDI allows?", "International")
    assert qa["answer"]
    assert "Source-supported evidence" in qa["answer"] or qa["insufficient_evidence"]


def test_service_run_label_authoring_and_review() -> None:
    facts = svc.load_sample_approved_facts()
    label = svc.load_sample_existing_label()
    res = svc.run_label_authoring(facts, label, "US")

    assert "proposed_label" in res
    assert "comparison_report" in res
    assert "markdown_report" in res
    assert res["overall_human_review_required"] is True

    # Test review update
    rep = res["comparison_report"]
    updated = svc.update_label_field_review(rep, "manufacturer_info", "Accepted", "Verified")
    diff_map = {d["field_id"]: d for d in updated["comparison_report"]["field_diffs"]}
    assert diff_map["manufacturer_info"]["review_status"] == "Accepted"

