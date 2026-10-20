from __future__ import annotations

import pytest

from labelai_rag.change_impact import ChangeCategory, assess_change_impact, parse_change_request


def base_request(**overrides):
    payload = {
        "change_id": "DEMO-CHANGE-001",
        "product_context": {
            "product": "illustrative cardiac stent",
            "market": "US",
            "device_type": "illustrative medical device",
        },
        "change_description": "Manufacturer address updated from the old office to a new office.",
        "current_label_elements": [
            "manufacturer name/address",
            "device identifier",
            "UDI",
            "warnings",
            "symbols",
            "instructions for use",
        ],
    }
    payload.update(overrides)
    return payload


def test_change_with_relevant_evidence_in_corpus() -> None:
    assessment = assess_change_impact(base_request(current_label_elements=["manufacturer name/address"]))
    elements = {item["element"]: item for item in assessment["affected_label_elements"]}
    assert "manufacturer name/address" in elements
    assert elements["manufacturer name/address"]["evidence_refs"]
    assert assessment["supporting_evidence"]
    assert assessment["human_review_required"] is True


def test_change_with_incomplete_evidence_marks_missing_information() -> None:
    assessment = assess_change_impact(
        base_request(
            change_description="The sterile symbol will be updated on the package label.",
            current_label_elements=["symbols"],
        )
    )
    assert any(item["element"] == "symbols" for item in assessment["affected_label_elements"])
    assert any("applicable symbol standard text" in item for item in assessment["missing_information"])
    assert any("ISO" in item or "limited" in item for item in assessment["source_coverage_limitations"])


def test_unsupported_market_or_regulatory_question_is_limited() -> None:
    assessment = assess_change_impact(
        base_request(
            product_context={"product": "illustrative cardiac stent", "market": "India"},
            change_description="Manufacturer address updated for India market release.",
            current_label_elements=["manufacturer name/address"],
        )
    )
    assert assessment["confidence_or_uncertainty"]["overall"] == "low"
    assert any("India" in item for item in assessment["source_coverage_limitations"])


def test_address_change_does_not_trigger_unrelated_label_elements() -> None:
    assessment = assess_change_impact(base_request(current_label_elements=["manufacturer name/address"]))
    elements = {item["element"] for item in assessment["affected_label_elements"]}
    assert elements == {"manufacturer name/address"}


def test_missing_product_context_fails_safely() -> None:
    payload = base_request()
    payload.pop("product_context")
    with pytest.raises(ValueError, match="product_context"):
        parse_change_request(payload)


def test_invalid_input_fails_safely() -> None:
    with pytest.raises(ValueError):
        parse_change_request({"change_id": "", "product_context": {}, "change_description": ""})


def test_evidence_and_citation_provenance() -> None:
    assessment = assess_change_impact(base_request(current_label_elements=["manufacturer name/address"]))
    evidence = assessment["supporting_evidence"][0]
    assert evidence["evidence_id"].startswith("EV")
    assert evidence["chunk_id"]
    assert evidence["source_title"]
    assert evidence["url"].startswith("https://")
    assert evidence["page"] is not None or evidence["section"]


def test_human_review_flags_are_preserved() -> None:
    assessment = assess_change_impact(base_request(current_label_elements=["manufacturer name/address"]))
    assert assessment["human_review_required"] is True
    assert all(action["human_review_required"] is True for action in assessment["recommended_review_actions"])


def test_novel_manufacturer_address_change() -> None:
    req = base_request(
        change_id="CHG-NOVEL-ADDR",
        product_context={
            "product": "CardioFlex Coronary Stent",
            "market": "US",
            "device_type": "Class III Cardiovascular Implant",
            "change_category": ChangeCategory.MANUFACTURER_INFO,
        },
        change_description="Relocating secondary manufacturing facility to 100 Innovation Way, Suite 400, Boston, MA 02110; corporate headquarters remains unchanged.",
        current_label_elements=["manufacturer name/address", "UDI", "warnings", "instructions for use"],
    )
    assessment = assess_change_impact(req)
    affected = {item["element"]: item for item in assessment["affected_label_elements"]}
    assert "manufacturer name/address" in affected
    assert affected["manufacturer name/address"]["evidence_state"] == "evidence_supported"
    assert affected["manufacturer name/address"]["evidence_refs"]
    assert "UDI" not in affected
    assert "warnings" not in affected
    assert assessment["human_review_required"] is True


def test_novel_intended_purpose_change() -> None:
    req = base_request(
        change_id="CHG-NOVEL-PURPOSE",
        product_context={
            "product": "PulseGuide Catheter System",
            "market": "US",
            "device_type": "Class II Diagnostic Catheter",
            "change_category": ChangeCategory.INTENDED_PURPOSE,
        },
        change_description="Expanding clinical indication to include adolescent patients aged 12-17 years with refractory coarctation of aorta.",
        current_label_elements=["instructions for use", "warnings", "intended purpose", "precautions"],
    )
    assessment = assess_change_impact(req)
    affected_elements = {item["element"] for item in assessment["affected_label_elements"]}
    assert any(elem in affected_elements for elem in ("instructions for use", "intended purpose", "warnings"))
    assert assessment["human_review_required"] is True
    assert any(
        "clinical" in act["action"].lower() or "indication" in act["action"].lower() or "ifu" in act["action"].lower()
        for act in assessment["recommended_review_actions"]
    )


def test_novel_warning_precaution_change() -> None:
    req = base_request(
        change_id="CHG-NOVEL-WARN",
        product_context={
            "product": "EndoGrip Biopsy Forceps",
            "market": "US",
            "device_type": "Class II Endoscopic Accessory",
            "change_category": ChangeCategory.WARNINGS_PRECAUTIONS,
        },
        change_description="Added contraindication regarding magnetic resonance imaging (MRI) field strengths exceeding 3 Tesla due to radiofrequency heating risks.",
        current_label_elements=["warnings", "precautions", "instructions for use", "symbols", "manufacturer name/address"],
    )
    assessment = assess_change_impact(req)
    affected_elements = {item["element"] for item in assessment["affected_label_elements"]}
    assert "warnings" in affected_elements or "precautions" in affected_elements or "instructions for use" in affected_elements
    assert "manufacturer name/address" not in affected_elements
    assert assessment["human_review_required"] is True


def test_novel_udi_identifier_change() -> None:
    req = base_request(
        change_id="CHG-NOVEL-UDI",
        product_context={
            "product": "OrthoSpine Pedicle Screw",
            "market": "US",
            "device_type": "Class III Spinal Implant",
            "change_category": ChangeCategory.UDI_IDENTIFIER,
        },
        change_description="Assigned new GS1 GTIN-14 (00812345678901) and 2D DataMatrix barcode due to change in primary package unit of use.",
        current_label_elements=["UDI", "device identifier", "packaging", "manufacturer name/address"],
    )
    assessment = assess_change_impact(req)
    affected_elements = {item["element"] for item in assessment["affected_label_elements"]}
    assert "UDI" in affected_elements or "device identifier" in affected_elements
    assert "manufacturer name/address" not in affected_elements
    udi_item = next(item for item in assessment["affected_label_elements"] if item["element"] in ("UDI", "device identifier"))
    assert udi_item["evidence_refs"]
    assert assessment["human_review_required"] is True


def test_novel_sterilization_shelf_life_change() -> None:
    req = base_request(
        change_id="CHG-NOVEL-STERIL",
        product_context={
            "product": "SurgiSeal Topical Adhesive",
            "market": "US",
            "device_type": "Class I Sterile Device",
            "change_category": ChangeCategory.STERILIZATION_SHELF_LIFE,
        },
        change_description="Shelf life extended from 24 months to 36 months following completed real-time aging stability testing; ethylene oxide sterilization cycle parameters modified.",
        current_label_elements=["storage/shelf life", "sterility", "instructions for use", "symbols", "manufacturer name/address"],
    )
    assessment = assess_change_impact(req)
    affected_elements = {item["element"] for item in assessment["affected_label_elements"]}
    assert any(elem in affected_elements for elem in ("storage/shelf life", "sterility", "instructions for use"))
    assert "manufacturer name/address" not in affected_elements
    assert any(
        "stability" in m.lower() or "aging" in m.lower() or "steril" in m.lower()
        for m in assessment["missing_information"]
    )
    assert assessment["human_review_required"] is True


def test_novel_packaging_change() -> None:
    req = base_request(
        change_id="CHG-NOVEL-PKG",
        product_context={
            "product": "VascPatch Synthetic Graft",
            "market": "US",
            "device_type": "Class II Vascular Prosthesis",
            "change_category": ChangeCategory.PACKAGING,
        },
        change_description="Transitioning sterile barrier from double poly pouch to Tyvek blister tray with peelable foil lid.",
        current_label_elements=["packaging", "sterility", "instructions for use", "UDI"],
    )
    assessment = assess_change_impact(req)
    affected_elements = {item["element"] for item in assessment["affected_label_elements"]}
    assert "packaging" in affected_elements or "sterility" in affected_elements
    assert "UDI" not in affected_elements
    assert assessment["human_review_required"] is True


def test_novel_translation_change() -> None:
    req = base_request(
        change_id="CHG-NOVEL-TRANS",
        product_context={
            "product": "DermaStitch Surgical Stapler",
            "market": "US",
            "device_type": "Class II Stapler",
            "change_category": ChangeCategory.TRANSLATION,
        },
        change_description="Adding Spanish language translation to package insert and outer box label for distribution in Puerto Rico.",
        current_label_elements=["instructions for use", "warnings", "manufacturer name/address"],
    )
    assessment = assess_change_impact(req)
    affected_elements = {item["element"] for item in assessment["affected_label_elements"]}
    assert "instructions for use" in affected_elements or "warnings" in affected_elements
    assert assessment["human_review_required"] is True


def test_novel_unsupported_jurisdiction() -> None:
    req = base_request(
        change_id="CHG-NOVEL-AU",
        product_context={
            "product": "AeroNeb Ultrasonic Nebulizer",
            "market": "Australia",
            "device_type": "Class IIa Respiratory Device",
            "change_category": ChangeCategory.MANUFACTURER_INFO,
        },
        change_description="Updating manufacturer address and caution statement for commercial launch in Australia under TGA regulations.",
        current_label_elements=["manufacturer name/address", "warnings"],
    )
    assessment = assess_change_impact(req)
    assert assessment["confidence_or_uncertainty"]["overall"] == "low"
    assert any("australia" in item.lower() for item in assessment["source_coverage_limitations"])
    assert assessment["human_review_required"] is True


def test_novel_insufficient_product_context_validation() -> None:
    with pytest.raises(ValueError, match="change_description"):
        parse_change_request(base_request(change_description="   "))

    with pytest.raises(ValueError, match="product_context"):
        parse_change_request({"change_id": "TEST-01", "change_description": "Valid description"})

    with pytest.raises(ValueError, match="change_id"):
        parse_change_request(base_request(change_id=""))


def test_novel_unrelated_elements_not_triggered() -> None:
    req = base_request(
        change_id="CHG-NOVEL-ISOLATION",
        product_context={
            "product": "illustrative cardiac stent",
            "market": "US",
            "device_type": "Class III Cardiovascular Implant",
            "change_category": ChangeCategory.MANUFACTURER_INFO,
        },
        change_description="Solely modifying corporate registered office suite number from Suite 100 to Suite 200 in Dallas, TX.",
        current_label_elements=[
            "manufacturer name/address",
            "device identifier",
            "UDI",
            "warnings",
            "symbols",
            "instructions for use",
        ],
    )
    assessment = assess_change_impact(req)
    affected = {item["element"] for item in assessment["affected_label_elements"]}
    assert "manufacturer name/address" in affected
    assert "UDI" not in affected
    assert "warnings" not in affected
    assert "symbols" not in affected
    assert "device identifier" not in affected
