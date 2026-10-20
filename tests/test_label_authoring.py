from __future__ import annotations

import json
from pathlib import Path

import pytest

from labelai_rag.label_authoring import (
    draft_label_update,
    export_diff_to_markdown,
    update_field_review_decision,
)
from labelai_rag.label_models import (
    FieldDiff,
    LabelDocument,
    VersionComparisonReport,
)


def load_cardioflex_label() -> dict:
    p = Path("data/label_authoring/sample_existing_label.json")
    return json.loads(p.read_text(encoding="utf-8"))


def load_cardioflex_facts() -> dict:
    p = Path("data/label_authoring/sample_approved_facts.json")
    return json.loads(p.read_text(encoding="utf-8"))


def load_cardioflex_impact() -> dict:
    p = Path("data/change_impact/sample_change_request_impact_assessment.json")
    return json.loads(p.read_text(encoding="utf-8"))


def test_draft_generation_from_sufficient_approved_facts() -> None:
    orig = load_cardioflex_label()
    facts = load_cardioflex_facts()
    impact = load_cardioflex_impact()

    proposed, report = draft_label_update(
        approved_product_facts=facts,
        existing_label=orig,
        target_jurisdiction="US",
        impact_assessment=impact,
    )

    assert proposed.version == "Rev C"
    assert proposed.status == "draft_for_review"
    assert "450 Enterprise Boulevard" in proposed.get_field("manufacturer_info")
    assert "Boston, MA 02110" in proposed.get_field("manufacturer_info")

    diff_map = {d.field_id: d for d in report.field_diffs}
    mfg_diff = diff_map["manufacturer_info"]
    assert mfg_diff.change_type == "modified"
    assert mfg_diff.evidence_state == "evidence_supported"
    assert "21 CFR 801.1" in mfg_diff.reason_for_change
    assert report.overall_human_review_required is True


def test_missing_product_information() -> None:
    orig = load_cardioflex_label()
    empty_facts: dict = {"change_id": "CHG-EMPTY"}  # No manufacturer_address!
    impact = load_cardioflex_impact()

    proposed, report = draft_label_update(
        approved_product_facts=empty_facts,
        existing_label=orig,
        target_jurisdiction="US",
        impact_assessment=impact,
    )

    diff_map = {d.field_id: d for d in report.field_diffs}
    mfg_diff = diff_map["manufacturer_info"]

    # Must NOT invent an address; must preserve original
    assert mfg_diff.change_type == "unchanged"
    assert proposed.get_field("manufacturer_info") == orig["fields"]["manufacturer_info"]
    assert any("missing new manufacturer physical street address" in m for m in report.missing_information)
    assert mfg_diff.evidence_state == "evidence_gap"


def test_unsupported_jurisdiction() -> None:
    orig = load_cardioflex_label()
    facts = load_cardioflex_facts()

    proposed, report = draft_label_update(
        approved_product_facts=facts,
        existing_label=orig,
        target_jurisdiction="Australia",
    )

    assert any("australia" in lim.lower() for lim in report.limitations)
    assert report.target_jurisdiction == "Australia"
    assert report.overall_human_review_required is True


def test_insufficient_regulatory_evidence_for_symbols() -> None:
    orig = load_cardioflex_label()
    facts = {"symbols_update": "New sterile barrier symbol"}
    symbol_impact = {
        "affected_label_elements": [
            {"element": "symbols", "impact": "review_required"}
        ]
    }

    proposed, report = draft_label_update(
        approved_product_facts=facts,
        existing_label=orig,
        target_jurisdiction="US",
        impact_assessment=symbol_impact,
    )

    diff_map = {d.field_id: d for d in report.field_diffs}
    sym_diff = diff_map["symbols_descriptions"]
    assert sym_diff.evidence_state == "evidence_gap"
    assert any("ISO 15223-1" in lim for lim in report.limitations)
    # Must preserve existing symbol description rather than hallucinating
    assert proposed.get_field("symbols_descriptions") == orig["fields"]["symbols_descriptions"]


def test_preservation_of_unchanged_fields() -> None:
    orig = load_cardioflex_label()
    facts = load_cardioflex_facts()
    impact = load_cardioflex_impact()

    proposed, report = draft_label_update(
        approved_product_facts=facts,
        existing_label=orig,
        target_jurisdiction="US",
        impact_assessment=impact,
    )

    # These fields must remain completely identical
    unchanged_keys = [
        "product_name_identifier",
        "intended_purpose",
        "device_description",
        "storage_handling",
        "sterilization_info",
        "shelf_life_expiry",
        "udi_identifiers",
        "symbols_descriptions",
    ]
    for key in unchanged_keys:
        assert proposed.get_field(key) == orig["fields"][key]

    assert report.unchanged_fields >= len(unchanged_keys)


def test_prevention_of_invented_identifiers_and_product_facts() -> None:
    orig = load_cardioflex_label()
    impact = {
        "affected_label_elements": [
            {"element": "UDI", "impact": "review_required"},
            {"element": "warnings", "impact": "review_required"},
        ]
    }
    # No UDI or warnings in approved facts
    blank_facts: dict = {}

    proposed, report = draft_label_update(
        approved_product_facts=blank_facts,
        existing_label=orig,
        target_jurisdiction="US",
        impact_assessment=impact,
    )

    # UDI and warnings must not have invented tokens
    assert proposed.get_field("udi_identifiers") == orig["fields"]["udi_identifiers"]
    assert proposed.get_field("warnings_precautions") == orig["fields"]["warnings_precautions"]
    assert any("missing assigned UDI-DI" in m for m in report.missing_information)
    assert any("missing verified clinical" in m for m in report.missing_information)


def test_correct_version_diff_classification() -> None:
    orig = load_cardioflex_label()
    facts = load_cardioflex_facts()
    impact = load_cardioflex_impact()

    _, report = draft_label_update(
        approved_product_facts=facts,
        existing_label=orig,
        target_jurisdiction="US",
        impact_assessment=impact,
    )

    assert report.total_fields == len(report.field_diffs)
    assert report.total_fields == (
        report.modified_fields + report.unchanged_fields + report.added_fields + report.removed_fields
    )
    assert report.modified_fields >= 1
    assert report.unchanged_fields >= 10


def test_field_level_review_decisions() -> None:
    orig = load_cardioflex_label()
    facts = load_cardioflex_facts()
    impact = load_cardioflex_impact()

    _, report = draft_label_update(
        approved_product_facts=facts,
        existing_label=orig,
        target_jurisdiction="US",
        impact_assessment=impact,
    )

    # Accept manufacturer_info
    updated = update_field_review_decision(report, "manufacturer_info", "Accepted", "Verified against lease agreement")
    mfg = next(d for d in updated.field_diffs if d.field_id == "manufacturer_info")
    assert mfg.review_status == "Accepted"
    assert mfg.reviewer_notes == "Verified against lease agreement"

    # Set needs revision
    updated2 = update_field_review_decision(updated, "instructions_for_use", "Needs revision", "Check phone format")
    ifu = next(d for d in updated2.field_diffs if d.field_id == "instructions_for_use")
    assert ifu.review_status == "Needs revision"

    # Reject
    updated3 = update_field_review_decision(updated2, "instructions_for_use", "Rejected", "Revert to Rev B")
    ifu_rej = next(d for d in updated3.field_diffs if d.field_id == "instructions_for_use")
    assert ifu_rej.review_status == "Rejected"

    # Invalid decision error
    with pytest.raises(ValueError, match="invalid"):
        update_field_review_decision(report, "manufacturer_info", "AutoApproved")

    # Invalid field error
    with pytest.raises(ValueError, match="not found"):
        update_field_review_decision(report, "non_existent_field", "Accepted")


def test_json_serialization_and_provenance() -> None:
    orig = load_cardioflex_label()
    facts = load_cardioflex_facts()
    impact = load_cardioflex_impact()

    proposed, report = draft_label_update(
        approved_product_facts=facts,
        existing_label=orig,
        target_jurisdiction="US",
        impact_assessment=impact,
    )

    doc_dict = proposed.to_dict()
    rep_dict = report.to_dict()

    # Test roundtrip JSON
    doc_json = json.dumps(doc_dict)
    rep_json = json.dumps(rep_dict)

    recon_doc = LabelDocument.from_dict(json.loads(doc_json))
    recon_rep = VersionComparisonReport.from_dict(json.loads(rep_json))

    assert recon_doc.label_id == proposed.label_id
    assert recon_rep.report_id == report.report_id
    assert recon_rep.modified_fields == report.modified_fields
    assert "authoring_timestamp" in recon_rep.metadata

    # Test markdown report generation
    md = export_diff_to_markdown(report)
    assert "# LabelAI Version Comparison Report" in md
    assert "manufacturer_info" in md


def test_operation_without_optional_api_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    orig = load_cardioflex_label()
    facts = load_cardioflex_facts()

    proposed, report = draft_label_update(
        approved_product_facts=facts,
        existing_label=orig,
        target_jurisdiction="US",
    )

    assert proposed.version == "Rev C"
    assert report.total_fields > 0


def test_udi_scenario_draft_generation() -> None:
    udi_label = json.loads(Path("data/label_authoring/sample_existing_label_udi.json").read_text(encoding="utf-8"))
    udi_facts = json.loads(Path("data/label_authoring/sample_approved_facts_udi.json").read_text(encoding="utf-8"))
    udi_impact = json.loads(Path("data/change_impact/change_request_udi_impact_assessment.json").read_text(encoding="utf-8"))

    proposed, report = draft_label_update(
        approved_product_facts=udi_facts,
        existing_label=udi_label,
        target_jurisdiction="US",
        impact_assessment=udi_impact,
    )

    assert proposed.version == "Rev D"
    assert "00812345678901" in proposed.get_field("udi_identifiers")
    assert "2D DataMatrix" in proposed.get_field("udi_identifiers")
    # Verify manufacturer info was preserved unchanged
    assert proposed.get_field("manufacturer_info") == udi_label["fields"]["manufacturer_info"]

    diff_map = {d.field_id: d for d in report.field_diffs}
    assert diff_map["udi_identifiers"].change_type == "modified"
    assert diff_map["manufacturer_info"].change_type == "unchanged"
