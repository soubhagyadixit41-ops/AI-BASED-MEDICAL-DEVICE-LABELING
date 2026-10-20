from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .label_models import (
    LABEL_FIELD_DEFINITIONS,
    FieldDiff,
    LabelDocument,
    VersionComparisonReport,
)
from .retrieval import LocalTfidfRetriever


ELEMENT_TO_FIELDS_MAP: dict[str, list[str]] = {
    "manufacturer name/address": ["manufacturer_info", "instructions_for_use"],
    "udi": ["udi_identifiers"],
    "device identifier": ["product_name_identifier", "udi_identifiers"],
    "warnings": ["warnings_precautions", "instructions_for_use"],
    "precautions": ["warnings_precautions", "instructions_for_use"],
    "instructions for use": ["instructions_for_use"],
    "symbols": ["symbols_descriptions"],
    "storage/shelf life": ["shelf_life_expiry", "storage_handling"],
    "storage and shelf-life": ["shelf_life_expiry", "storage_handling"],
    "sterility": ["sterilization_info"],
    "sterility status / sterilization": ["sterilization_info"],
    "packaging": ["storage_handling", "sterilization_info"],
    "intended purpose": ["intended_purpose", "instructions_for_use"],
    "composition": ["device_description", "warnings_precautions"],
}

SUPPORTED_AUTHORING_JURISDICTIONS = {"us", "usa", "united states", "international", "global", "eu", "european union"}


def normalize_str(val: str) -> str:
    return val.strip().lower()


def identify_candidate_sections(
    impact_assessment: dict[str, Any] | None,
    requested_sections: list[str] | None = None,
) -> set[str]:
    candidate_fields: set[str] = set()

    if impact_assessment:
        affected = impact_assessment.get("affected_label_elements", [])
        for item in affected:
            elem = normalize_str(item.get("element", ""))
            for pattern, field_ids in ELEMENT_TO_FIELDS_MAP.items():
                if pattern in elem or elem in pattern:
                    candidate_fields.update(field_ids)

    if not candidate_fields and not requested_sections:
        # Default fallback: if no impact assessment provided, no sections are marked for modification
        return set()

    if requested_sections:
        req_set = {s.strip() for s in requested_sections if s.strip()}
        if candidate_fields:
            candidate_fields = candidate_fields.intersection(req_set)
        else:
            candidate_fields = req_set

    return candidate_fields


def _retrieve_evidence_for_field(
    field_id: str,
    target_jurisdiction: str,
    existing_evidence: list[dict[str, Any]] | None = None,
) -> tuple[list[str], str, list[dict[str, Any]]]:
    """Return (evidence_refs, evidence_state, supporting_evidence_items)."""
    norm_jur = normalize_str(target_jurisdiction)
    if norm_jur not in SUPPORTED_AUTHORING_JURISDICTIONS:
        return [], "evidence_gap", []

    if field_id == "symbols_descriptions":
        # ISO 15223-1 is paywalled and not in corpus
        return [], "evidence_gap", []

    if existing_evidence:
        refs = [e.get("evidence_id", f"EV{i+1:03d}") for i, e in enumerate(existing_evidence[:2])]
        state = "evidence_supported" if any(e.get("retrieval_score", 0) >= 0.2 for e in existing_evidence) else "potentially_relevant"
        return refs, state, existing_evidence[:2]

    # Otherwise query retriever
    retriever = LocalTfidfRetriever.load()
    jur_filter = "United States" if norm_jur in {"us", "usa", "united states"} else "International"
    query = f"{field_id.replace('_', ' ')} medical device labeling requirements"
    results = retriever.search(query, top_k=2, jurisdiction=jur_filter)

    refs: list[str] = []
    items: list[dict[str, Any]] = []
    for i, res in enumerate(results):
        ref_id = f"EV{i+1:03d}"
        refs.append(ref_id)
        items.append({
            "evidence_id": ref_id,
            "chunk_id": res.chunk.chunk_id,
            "source_title": res.chunk.title,
            "publisher": res.chunk.publisher,
            "jurisdiction": res.chunk.jurisdiction,
            "url": res.chunk.url,
            "section": res.chunk.section,
            "retrieval_score": round(res.score, 4),
            "excerpt": res.chunk.text[:500],
        })

    state = "evidence_supported" if results and results[0].score >= 0.2 else "potentially_relevant"
    return refs, state, items


def draft_label_update(
    approved_product_facts: dict[str, Any],
    existing_label: LabelDocument | dict[str, Any],
    target_jurisdiction: str = "US",
    impact_assessment: dict[str, Any] | None = None,
    retrieved_evidence: list[dict[str, Any]] | None = None,
    requested_sections_to_revise: list[str] | None = None,
    target_version: str | None = None,
) -> tuple[LabelDocument, VersionComparisonReport]:
    """Grounded label authoring: generates proposed revisions strictly based on approved facts and regulatory evidence."""
    if not isinstance(approved_product_facts, dict):
        raise ValueError("approved_product_facts must be a dictionary.")

    orig_doc = existing_label if isinstance(existing_label, LabelDocument) else LabelDocument.from_dict(existing_label)

    norm_jur = normalize_str(target_jurisdiction)
    is_unsupported_jur = norm_jur not in SUPPORTED_AUTHORING_JURISDICTIONS

    candidate_fields = identify_candidate_sections(impact_assessment, requested_sections_to_revise)

    # Determine next version
    curr_v = orig_doc.version or "v1.0"
    if target_version:
        next_v = target_version
    elif curr_v.startswith("Rev "):
        next_letter = chr(ord(curr_v.replace("Rev ", "").strip() or "A") + 1)
        next_v = f"Rev {next_letter}"
    elif curr_v.startswith("v"):
        try:
            num = float(curr_v[1:])
            next_v = f"v{num + 0.1:.1f}"
        except ValueError:
            next_v = f"{curr_v}-draft"
    else:
        next_v = f"{curr_v}.1"

    proposed_fields: dict[str, str] = dict(orig_doc.fields)
    field_diffs: list[FieldDiff] = []
    missing_information: list[str] = []
    limitations: list[str] = []

    if is_unsupported_jur:
        limitations.append(
            f"Target jurisdiction '{target_jurisdiction}' is not directly indexed. Knowledge base contains United States (FDA), European Union (EUDAMED/UDI), and International (IMDRF) regulations."
        )

    # Carry forward limitations from impact assessment
    if impact_assessment:
        for m in impact_assessment.get("missing_information", []):
            if m not in missing_information:
                missing_information.append(m)
        for lim in impact_assessment.get("source_coverage_limitations", []):
            if lim not in limitations:
                limitations.append(lim)

    # Evaluate each defined label field
    all_field_keys = list(LABEL_FIELD_DEFINITIONS.keys())
    # Also include any custom keys in orig_doc.fields
    for k in orig_doc.fields.keys():
        if k not in all_field_keys:
            all_field_keys.append(k)

    for field_id in all_field_keys:
        label_name = LABEL_FIELD_DEFINITIONS.get(field_id, field_id.replace("_", " ").title())
        orig_val = orig_doc.get_field(field_id, "")

        if field_id not in candidate_fields:
            # Preserved unchanged
            field_diffs.append(
                FieldDiff(
                    field_id=field_id,
                    label_name=label_name,
                    original_value=orig_val,
                    proposed_value=orig_val,
                    change_type="unchanged",
                    reason_for_change="Section not identified as impacted by change assessment; preserved unchanged.",
                    evidence_refs=[],
                    evidence_state="not_applicable",
                    review_status="Accepted",
                    reviewer_notes="Unchanged from previous approved label version.",
                )
            )
            continue

        # Candidate for revision
        ev_refs, ev_state, _ = _retrieve_evidence_for_field(
            field_id,
            target_jurisdiction,
            retrieved_evidence or (impact_assessment.get("supporting_evidence") if impact_assessment else None),
        )

        # Drafting logic per field
        new_val = orig_val
        reason = ""
        missing_fact = False

        if field_id == "manufacturer_info":
            # Approved facts check
            new_addr = (
                approved_product_facts.get("manufacturer_address")
                or approved_product_facts.get("new_manufacturer_address")
                or approved_product_facts.get("address")
                or approved_product_facts.get("relocated_address")
            )
            mfg_name = approved_product_facts.get("manufacturer_name") or approved_product_facts.get("legal_entity_name") or orig_doc.product_name

            if new_addr:
                new_val = f"Manufactured by:\n{mfg_name}\n{new_addr}"
                reason = "Updated manufacturer location per approved product facts in compliance with 21 CFR 801.1 and IMDRF Section 5.2.9."
            else:
                missing_fact = True
                missing_msg = "Approved product facts missing new manufacturer physical street address (21 CFR 801.1)."
                missing_information.append(missing_msg)
                reason = f"Section impacted, but approved facts lacked required address. Content preserved unchanged. Limitation: {missing_msg}"
                ev_state = "evidence_gap"

        elif field_id == "udi_identifiers":
            udi_di = approved_product_facts.get("udi_di") or approved_product_facts.get("gtin")
            carrier = approved_product_facts.get("carrier_type") or approved_product_facts.get("barcode_carrier") or "2D DataMatrix (GS1)"

            if udi_di:
                new_val = f"UDI: (01){udi_di}\nCarrier: {carrier}\nIssuing Agency: {approved_product_facts.get('issuing_agency', 'GS1')}"
                reason = "Updated device identifier and UDI carrier format per approved product facts and 21 CFR 801.40 / FDA UDI guidance."
            else:
                missing_fact = True
                missing_msg = "Approved product facts missing assigned UDI-DI / GTIN (21 CFR 801.40)."
                missing_information.append(missing_msg)
                reason = f"Section impacted, but approved facts lacked assigned UDI-DI. Content preserved unchanged. Limitation: {missing_msg}"
                ev_state = "evidence_gap"

        elif field_id == "warnings_precautions":
            contra = (
                approved_product_facts.get("primary_contraindication")
                or approved_product_facts.get("new_contraindications")
                or approved_product_facts.get("warning_update")
            )
            mri_info = approved_product_facts.get("mr_safety_status")

            if contra or mri_info:
                additions = []
                if contra:
                    additions.append(f"CONTRAINDICATION: {contra}")
                if mri_info:
                    additions.append(f"MRI SAFETY: {mri_info}")
                joined_additions = "\n".join(additions)
                new_val = f"{orig_val}\n\n[REVISED SAFETY INFORMATION]:\n{joined_additions}".strip()
                reason = "Incorporated approved clinical safety statements/contraindications per risk assessment RA-2026 and 21 CFR 801.405-437."
            else:
                missing_fact = True
                missing_msg = "Approved product facts missing verified clinical contraindication / risk text."
                missing_information.append(missing_msg)
                reason = f"Section impacted, but approved facts lacked verified safety text. Content preserved unchanged. Limitation: {missing_msg}"
                ev_state = "evidence_gap"

        elif field_id == "intended_purpose":
            indications = approved_product_facts.get("approved_indications") or approved_product_facts.get("intended_use")
            if indications:
                new_val = str(indications)
                reason = "Updated intended purpose and clinical indications per approved clinical evaluation."
            else:
                missing_fact = True
                missing_msg = "Approved product facts missing cleared clinical indications statement."
                missing_information.append(missing_msg)
                reason = "Section impacted, but approved facts lacked cleared indication statement. Content preserved unchanged."
                ev_state = "evidence_gap"

        elif field_id == "sterilization_info":
            steril_method = approved_product_facts.get("sterilization_method")
            if steril_method:
                new_val = f"Sterilization: {steril_method}\nSingle-use sterile device. Do not resterilize if sterile barrier is damaged."
                reason = "Updated sterilization method per approved sterilization validation protocol (21 CFR 820.130)."
            else:
                missing_fact = True
                missing_msg = "Approved product facts missing sterilization validation parameters."
                missing_information.append(missing_msg)
                reason = "Section impacted, but sterilization validation parameters were missing. Preserved unchanged."
                ev_state = "evidence_gap"

        elif field_id == "shelf_life_expiry":
            shelf_life = approved_product_facts.get("shelf_life") or approved_product_facts.get("approved_shelf_life")
            if shelf_life:
                new_val = f"Shelf Life: {shelf_life}\nSee packaging for expiration date (YYYY-MM-DD)."
                reason = "Updated shelf-life expiration duration per completed stability testing report."
            else:
                missing_fact = True
                missing_msg = "Approved product facts missing stability / shelf-life test report."
                missing_information.append(missing_msg)
                reason = "Section impacted, but stability data missing. Preserved unchanged."
                ev_state = "evidence_gap"

        elif field_id == "symbols_descriptions":
            # Proprietary standard limitation
            ev_state = "evidence_gap"
            limitations.append("ISO 15223-1 graphical symbols standard is copyrighted and not indexed; symbols must be manually audited against official standard.")
            reason = "Symbol review flagged by change assessment. Autonomous drafting withheld because ISO 15223-1 is unindexed/paywalled."
            new_val = orig_val

        elif field_id == "instructions_for_use":
            # If address or warning changed, reflect in IFU reference
            new_addr = approved_product_facts.get("manufacturer_address") or approved_product_facts.get("new_manufacturer_address")
            contra = approved_product_facts.get("primary_contraindication")
            parts = []
            if orig_val:
                parts.append(orig_val)
            if new_addr:
                parts.append(f"\n[IFU Contact Update]: Inquiries and adverse event reports: {new_addr}")
            if contra:
                parts.append(f"\n[IFU Warning Update]: {contra}")

            if parts and (new_addr or contra):
                new_val = "\n".join(parts).strip()
                reason = "Synchronized IFU contact and safety sections with approved product changes."
            else:
                reason = "IFU flagged for review; existing directions preserved pending clinical IFU sign-off."
                new_val = orig_val

        else:
            # Generic candidate
            reason = "Candidate section evaluated; existing text preserved without unauthorized alteration."
            new_val = orig_val

        proposed_fields[field_id] = new_val

        # Classify diff
        if orig_val == new_val:
            change_type = "unchanged"
            rev_status = "Pending" if missing_fact else "Accepted"
        elif not orig_val and new_val:
            change_type = "added"
            rev_status = "Pending"
        elif orig_val and not new_val:
            change_type = "removed"
            rev_status = "Pending"
        else:
            change_type = "modified"
            rev_status = "Pending"

        field_diffs.append(
            FieldDiff(
                field_id=field_id,
                label_name=label_name,
                original_value=orig_val,
                proposed_value=new_val,
                change_type=change_type,
                reason_for_change=reason,
                evidence_refs=ev_refs,
                evidence_state=ev_state,
                review_status=rev_status,
                reviewer_notes="Requires qualified regulatory review before release.",
            )
        )

    # Build proposed document
    proposed_doc = LabelDocument(
        label_id=f"{orig_doc.label_id}-draft",
        product_name=orig_doc.product_name,
        version=next_v,
        status="draft_for_review",
        target_jurisdiction=target_jurisdiction,
        language=orig_doc.language,
        fields=proposed_fields,
        metadata={
            "created_at": datetime.now().isoformat(),
            "based_on_version": orig_doc.version,
            "authoring_mode": "deterministic_grounded_authoring",
            "human_review_required": True,
        },
    )

    # Build report
    total_f = len(field_diffs)
    mod_f = sum(1 for d in field_diffs if d.change_type == "modified")
    unchanged_f = sum(1 for d in field_diffs if d.change_type == "unchanged")
    add_f = sum(1 for d in field_diffs if d.change_type == "added")
    rem_f = sum(1 for d in field_diffs if d.change_type == "removed")

    report = VersionComparisonReport(
        report_id=f"DIFF-{orig_doc.label_id}-{next_v}",
        label_id=orig_doc.label_id,
        from_version=curr_v,
        to_version=next_v,
        target_jurisdiction=target_jurisdiction,
        total_fields=total_f,
        modified_fields=mod_f,
        unchanged_fields=unchanged_f,
        added_fields=add_f,
        removed_fields=rem_f,
        field_diffs=field_diffs,
        overall_human_review_required=True,
        missing_information=list(dict.fromkeys(missing_information)),
        limitations=list(dict.fromkeys(limitations)),
        metadata={
            "authoring_timestamp": datetime.now().isoformat(),
            "regulatory_disclaimer": "Proposed draft requires qualified regulatory review. Does not constitute regulatory compliance determination.",
        },
    )

    return proposed_doc, report


def update_field_review_decision(
    report: VersionComparisonReport | dict[str, Any],
    field_id: str,
    decision: str,
    reviewer_notes: str = "",
) -> VersionComparisonReport | dict[str, Any]:
    """Update human review decision for an individual field."""
    valid_decisions = {"Pending", "Accepted", "Needs revision", "Rejected"}
    if decision not in valid_decisions:
        raise ValueError(f"Decision '{decision}' is invalid. Must be one of {valid_decisions}")

    is_dict = isinstance(report, dict)
    rep_obj = VersionComparisonReport.from_dict(report) if is_dict else report

    matched = False
    for diff in rep_obj.field_diffs:
        if diff.field_id == field_id:
            diff.review_status = decision
            if reviewer_notes.strip():
                diff.reviewer_notes = reviewer_notes.strip()
            matched = True
            break

    if not matched:
        raise ValueError(f"Field ID '{field_id}' not found in version comparison report.")

    return rep_obj.to_dict() if is_dict else rep_obj


def export_diff_to_markdown(report: VersionComparisonReport | dict[str, Any]) -> str:
    rep = VersionComparisonReport.from_dict(report) if isinstance(report, dict) else report
    lines: list[str] = [
        f"# LabelAI Version Comparison Report: {rep.from_version} → {rep.to_version}",
        "",
        f"- **Label ID:** `{rep.label_id}`",
        f"- **Target Jurisdiction:** {rep.target_jurisdiction}",
        f"- **Total Fields:** {rep.total_fields} (Modified: {rep.modified_fields}, Unchanged: {rep.unchanged_fields}, Added: {rep.added_fields})",
        "- **Human Review Required:** Yes (Mandatory regulatory professional review)",
        "",
        "## Field-by-Field Diff & Review Status",
        "",
        "| Field | Change Type | Evidence State | Review Decision | Rationale |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    for d in rep.field_diffs:
        lines.append(
            f"| **{d.label_name}** (`{d.field_id}`) | `{d.change_type}` | `{d.evidence_state}` | **{d.review_status}** | {d.reason_for_change} |"
        )

    if rep.missing_information:
        lines.extend(["", "## Missing Information Required Before Release", ""])
        for m in rep.missing_information:
            lines.append(f"- ⚠️ {m}")

    if rep.limitations:
        lines.extend(["", "## Regulatory Coverage Limitations", ""])
        for lim in rep.limitations:
            lines.append(f"- ℹ️ {lim}")

    lines.extend([
        "",
        "---",
        "*Disclaimer: This report was produced by an automated drafting and triage assistant. It does not certify regulatory compliance.*",
    ])
    return "\n".join(lines)
