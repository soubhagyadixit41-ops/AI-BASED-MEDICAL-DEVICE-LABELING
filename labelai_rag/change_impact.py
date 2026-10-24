from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import RetrievalResult
from .retrieval import LocalTfidfRetriever


SUPPORTED_MARKETS = {"international", "global", "us", "usa", "united states", "eu", "european union"}
PARTIALLY_SUPPORTED_MARKETS = {"eu", "european union"}


class ChangeCategory:
    MANUFACTURER_INFO = "Manufacturer information change"
    INTENDED_PURPOSE = "Intended-purpose change"
    DEVICE_SPECIFICATIONS = "Device specifications change"
    MATERIALS_COMPOSITION = "Materials or composition change"
    WARNINGS_PRECAUTIONS = "Warning or precaution change"
    STERILIZATION_SHELF_LIFE = "Sterilization or shelf-life change"
    UDI_IDENTIFIER = "UDI or identifier change"
    PACKAGING = "Packaging change"
    TRANSLATION = "Translation change"
    OTHER = "Other or unknown change"


@dataclass(frozen=True)
class ConceptProfile:
    concept_id: str
    category_aliases: tuple[str, ...]
    semantic_patterns: tuple[str, ...]
    primary_elements: tuple[str, ...]
    secondary_elements: tuple[str, ...]
    evidence_query: str
    relationship: str
    reason: str
    review_action: str
    missing_info_keys: tuple[str, ...]


CONCEPT_PROFILES: tuple[ConceptProfile, ...] = (
    ConceptProfile(
        concept_id="manufacturer_address",
        category_aliases=(
            ChangeCategory.MANUFACTURER_INFO,
            "address update",
            "manufacturer update",
            "manufacturer change",
            "relocation",
        ),
        semantic_patterns=(
            r"\b(?:relocat|address|headquarter|manufactur|site|facility|packer|distributor|place of business)\b",
            r"\b(?:move|moved|moving|new office|new facility)\b",
        ),
        primary_elements=("manufacturer name/address",),
        secondary_elements=("instructions for use",),
        evidence_query="label shall contain name and place of business of manufacturer location 21 CFR 801.1 Section 5.2.9",
        relationship="Direct manufacturer identity and registered address update on product label and packaging",
        reason="A manufacturer address change directly affects label content identifying the manufacturer and its physical or registered location under 21 CFR 801.1 and IMDRF Section 5.2.9.",
        review_action="Review product label, packaging, IFU, and regulatory registrations showing manufacturer name or address; confirm territory-specific address requirements before release.",
        missing_info_keys=(
            "new manufacturer address",
            "effective date of address change",
            "markets where updated label will be distributed",
        ),
    ),
    ConceptProfile(
        concept_id="intended_purpose",
        category_aliases=(
            ChangeCategory.INTENDED_PURPOSE,
            "indication update",
            "indications change",
            "clinical use change",
        ),
        semantic_patterns=(
            r"\b(?:intended use|intended purpose|indication|indications|population|pediatric|adult|clinical use|off-label)\b",
            r"\b(?:treatment of|prescribed for|contraindicated in)\b",
        ),
        primary_elements=("instructions for use", "warnings"),
        secondary_elements=("intended purpose",),
        evidence_query="intended use intended purpose adequate directions for use indications contraindications 21 CFR 801.4 801.5",
        relationship="Clinical indication and intended purpose scope expansion or restriction",
        reason="Modifications to intended purpose or patient population alter user instructions, indications statements, and risk disclosures under 21 CFR 801.4/801.5 and IMDRF Section 5.3.10.",
        review_action="Perform clinical evaluation and regulatory review of revised indications, user directions, and potential contraindications with qualified clinical and RA specialists.",
        missing_info_keys=(
            "clinical evaluation report (CER) update status",
            "target patient population specifications",
            "risk assessment for the intended use change",
        ),
    ),
    ConceptProfile(
        concept_id="warnings_precautions",
        category_aliases=(
            ChangeCategory.WARNINGS_PRECAUTIONS,
            "warning update",
            "precaution update",
            "safety alert",
            "contraindication change",
        ),
        semantic_patterns=(
            r"\b(?:warning|warnings|precaution|precautions|contraindication|contraindications|black box|hazard|adverse event|safety alert)\b",
            r"\b(?:residual risk|risk mitigation|toxic|side effect)\b",
        ),
        primary_elements=("warnings", "instructions for use"),
        secondary_elements=(),
        evidence_query="instructions for use warnings precautions safety performance contraindications 21 CFR 801 Section 5.1",
        relationship="Safety warning, precaution, or contraindication risk disclosure revision",
        reason="Safety-related modifications alter precautionary statements and clinical risk communication required on the device label and in the IFU.",
        review_action="Review warnings, precautions, risk controls, and IFU sections with qualified regulatory, medical, and clinical reviewers.",
        missing_info_keys=(
            "risk assessment for the proposed change",
            "clinical root-cause analysis or post-market surveillance data",
        ),
    ),
    ConceptProfile(
        concept_id="udi_identifier",
        category_aliases=(
            ChangeCategory.UDI_IDENTIFIER,
            "udi update",
            "identifier update",
            "barcode update",
            "gtin change",
        ),
        semantic_patterns=(
            r"\b(?:udi|unique device identifier|basic udi|basic udi-di|udi-di|udi-pi|datamatrix|barcode|gtin|gs1|hibcc)\b",
            r"\b(?:device identifier|catalog number|catalogue number|model number|serial number)\b",
        ),
        primary_elements=("UDI", "device identifier"),
        secondary_elements=(),
        evidence_query="unique device identifier UDI unambiguous identification device identifier production identifier 21 CFR 801.40",
        relationship="Device identifier, catalog reference, or machine-readable UDI carrier update",
        reason="Identifier or UDI changes directly impact product traceability, machine-readable labeling compliance (21 CFR 801.40), and regulatory database registration (EUDAMED/GUDID).",
        review_action="Verify UDI-DI / Basic UDI-DI assignment, barcode print quality and verifier grade, and regulatory database submissions across all target jurisdictions.",
        missing_info_keys=(
            "UDI-DI or Basic UDI-DI affected status",
            "identifier before and after the change",
        ),
    ),
    ConceptProfile(
        concept_id="symbols",
        category_aliases=(
            "symbol update",
            "symbols change",
            "iso 15223",
            "legend update",
        ),
        semantic_patterns=(
            r"\b(?:symbol|symbols|iso 15223|iso 20417|graphical symbol|symbol legend)\b",
            r"\b(?:sterile symbol|ce mark|rx only symbol)\b",
        ),
        primary_elements=("symbols",),
        secondary_elements=("instructions for use",),
        evidence_query="internationally recognized symbols labeling meaning of the symbol not obvious explanation",
        relationship="Graphical symbol, standardized icon, or symbol definition legend modification",
        reason="Symbol changes affect user comprehension and require compliance with recognized symbol standards (ISO 15223-1 / IMDRF Section 5.1.4).",
        review_action="Review symbol graphics against applicable symbol standards (ISO 15223-1); verify symbol definition legend is provided in the IFU if meaning is not obvious.",
        missing_info_keys=(
            "specific symbol being changed",
            "applicable symbol standard text",
        ),
    ),
    ConceptProfile(
        concept_id="instructions_for_use",
        category_aliases=(
            "ifu update",
            "ifu change",
            "manual update",
            "user instructions change",
            "directions update",
        ),
        semantic_patterns=(
            r"\b(?:ifu|instructions for use|user manual|directions for use|operator manual|package insert|user guide)\b",
            r"\b(?:preparation for use|maintenance instruction|cleaning instruction)\b",
        ),
        primary_elements=("instructions for use",),
        secondary_elements=(),
        evidence_query="instructions for use intended user readily understood paper electronic format adequate directions 21 CFR 801.5",
        relationship="User directions, handling, preparation, or operating instructions modification",
        reason="A change to instructions for use alters how clinicians or lay users prepare, use, or maintain the medical device safely.",
        review_action="Review IFU wording, diagrams, readability level, electronic delivery format (eIFU), and language concordances before release.",
        missing_info_keys=(
            "specific IFU sections affected",
            "eIFU regulatory qualification status if provided electronically",
        ),
    ),
    ConceptProfile(
        concept_id="sterilization_shelf_life",
        category_aliases=(
            ChangeCategory.STERILIZATION_SHELF_LIFE,
            "sterilization update",
            "shelf life change",
            "expiry update",
            "aging change",
        ),
        semantic_patterns=(
            r"\b(?:steril|sterility|sterilization|autoclave|ethylene oxide|gamma radiation|irradiation|e-beam)\b",
            r"\b(?:shelf-life|shelf life|expiry|expiration date|expiration dating|stability|accelerated aging)\b",
        ),
        primary_elements=("storage/shelf life", "sterility", "symbols", "instructions for use"),
        secondary_elements=("sterility status / sterilization", "storage and shelf-life"),
        evidence_query="sterile device labeling sterilization shelf life expiration date 21 CFR 820.130",
        relationship="Sterility method, sterile barrier, or shelf-life stability expiration dating revision",
        reason="Changes in sterilization or aging alter sterility status labeling, sterile barrier instructions, expiration dates, and sterile symbol disclosures under 21 CFR 820 and IMDRF.",
        review_action="Review sterility symbol, expiration date format, sterile packaging seal instructions, and sterility validation protocols.",
        missing_info_keys=(
            "sterilization validation report (ISO 11135 or ISO 11137)",
            "real-time or accelerated aging stability test results",
        ),
    ),
    ConceptProfile(
        concept_id="packaging",
        category_aliases=(
            ChangeCategory.PACKAGING,
            "packaging update",
            "sterile barrier change",
            "container update",
            "package change",
        ),
        semantic_patterns=(
            r"\b(?:packag|sterile barrier|blister pack|tyvek|pouch|carton|shipper|unit of use|outer box|container closure)\b",
        ),
        primary_elements=("packaging", "symbols", "instructions for use"),
        secondary_elements=("packaging / sterile barrier", "sterility", "device identifier"),
        evidence_query="label on the device itself packaging unit packaging instructions for use sterile barrier 21 CFR 801",
        relationship="Primary packaging, sterile barrier system, or secondary container labeling modification",
        reason="Altering packaging configurations affects label placement, packaging symbols, sterile barrier integrity disclosures, and unit-of-use identification.",
        review_action="Verify label adhesion and legibility on revised packaging substrates; confirm sterile barrier opening instructions and ISO 11607 packaging validation.",
        missing_info_keys=(
            "sterile barrier validation data (ISO 11607)",
            "packaging label adhesion and durability test report",
        ),
    ),
    ConceptProfile(
        concept_id="translation_language",
        category_aliases=(
            ChangeCategory.TRANSLATION,
            "translation update",
            "multilingual update",
            "language update",
        ),
        semantic_patterns=(
            r"\b(?:translat|language|spanish|french|german|italian|multilingual|local language|dialect|linguistic)\b",
            r"\b(?:puerto rico language|territory language)\b",
        ),
        primary_elements=("instructions for use", "warnings"),
        secondary_elements=("translation / language",),
        evidence_query="all labeling shall be in English foreign language translation Puerto Rico language exceptions",
        relationship="Multilingual translation or local territory language addition",
        reason="Introducing or updating foreign language translations requires verified linguistic concordance with authorized labeling under 21 CFR 801 and local market regulations.",
        review_action="Audit certified translations against approved master English labeling; ensure local territory language requirements are satisfied.",
        missing_info_keys=(
            "certified translation and back-translation verification records",
            "target country language regulatory requirements checklist",
        ),
    ),
    ConceptProfile(
        concept_id="device_specifications",
        category_aliases=(
            ChangeCategory.DEVICE_SPECIFICATIONS,
            ChangeCategory.MATERIALS_COMPOSITION,
            "specification change",
            "dimensions update",
            "materials update",
        ),
        semantic_patterns=(
            r"\b(?:dimension|dimensions|diameter|length|tolerance|voltage|specification|technical data)\b",
            r"\b(?:material|composition|polymer|biocompatibility|latex|nickel|phthalate)\b",
        ),
        primary_elements=("device identifier", "instructions for use"),
        secondary_elements=("warnings", "symbols"),
        evidence_query="details necessary for a user to identify the device catalog number model specifications warnings",
        relationship="Physical specification, dimension, or device material composition modification",
        reason="Material or dimensional alterations affect technical specification disclosures, device identification numbers, and potential material warnings (e.g. latex/nickel).",
        review_action="Review specification tables in the IFU, material hazard warnings, and catalog/model number assignments.",
        missing_info_keys=(
            "revised specification verification report",
            "biocompatibility evaluation (ISO 10993) if materials altered",
        ),
    ),
)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def parse_change_request(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Change request must be a JSON object.")
    change_id = payload.get("change_id")
    product_context = payload.get("product_context")
    change_description = payload.get("change_description")
    current_label_elements = payload.get("current_label_elements", [])

    if not isinstance(change_id, str) or not change_id.strip():
        raise ValueError("change_id is required and must be a non-empty string.")
    if not isinstance(product_context, dict) or not product_context:
        raise ValueError("product_context is required and must be a non-empty object.")
    if not isinstance(change_description, str) or not change_description.strip():
        raise ValueError("change_description is required and must be a non-empty string.")
    if not isinstance(current_label_elements, list) or not all(isinstance(item, str) for item in current_label_elements):
        raise ValueError("current_label_elements must be a list of strings.")

    # Support optional structured fields
    change_category = payload.get("change_category") or product_context.get("change_category") or ChangeCategory.OTHER
    approved_facts = payload.get("approved_product_facts") or product_context.get("approved_product_facts") or {}
    label_version = payload.get("existing_label_version") or product_context.get("existing_label_version")
    reviewer_notes = payload.get("reviewer_notes") or product_context.get("reviewer_notes")

    return {
        "change_id": change_id.strip(),
        "product_context": product_context,
        "change_category": change_category,
        "change_description": change_description.strip(),
        "current_label_elements": current_label_elements,
        "approved_product_facts": approved_facts,
        "existing_label_version": label_version,
        "reviewer_notes": reviewer_notes,
    }


def detect_candidate_profiles(
    change_description: str,
    change_category: str | None = None,
    current_label_elements: list[str] | None = None,
) -> list[ConceptProfile]:
    text = normalize_text(change_description)
    cat_norm = normalize_text(change_category or "")
    matched: list[ConceptProfile] = []

    for profile in CONCEPT_PROFILES:
        is_matched = False

        # Category alias match
        if cat_norm and any(normalize_text(alias) in cat_norm or cat_norm in normalize_text(alias) for alias in profile.category_aliases):
            is_matched = True

        # Semantic regex/word stem match
        if not is_matched:
            for pattern in profile.semantic_patterns:
                if re.search(pattern, text, re.I):
                    is_matched = True
                    break

        if is_matched:
            matched.append(profile)

    return matched


def map_candidate_elements(
    profiles: list[ConceptProfile],
    current_label_elements: list[str],
) -> list[tuple[str, ConceptProfile]]:
    """Map detected profiles to the actual current label elements."""
    norm_current = {normalize_text(elem): elem for elem in current_label_elements}
    paired: list[tuple[str, ConceptProfile]] = []
    seen_elements: set[str] = set()

    # If current_label_elements is supplied, strictly intersect with it
    for profile in profiles:
        # Check primary elements first
        for primary in profile.primary_elements:
            norm_p = normalize_text(primary)
            if norm_p in norm_current and norm_p not in seen_elements:
                paired.append((norm_current[norm_p], profile))
                seen_elements.add(norm_p)

        # Check secondary elements if primary wasn't in current_elements
        for secondary in profile.secondary_elements:
            norm_s = normalize_text(secondary)
            if norm_s in norm_current and norm_s not in seen_elements:
                paired.append((norm_current[norm_s], profile))
                seen_elements.add(norm_s)

    return paired


def map_jurisdiction(market: str | None) -> str | None:
    if not market:
        return None
    norm = normalize_text(market)
    if norm in {"us", "usa", "united states"}:
        return "United States"
    if norm in {"eu", "european union"}:
        return "European Union"
    if norm in {"international", "global"}:
        return "International"
    return None


def market_limitations(market: str | None) -> list[str]:
    if not market:
        return ["Market was not provided; market-specific requirements cannot be assessed."]
    normalized = normalize_text(market)
    if normalized in {"international", "global"}:
        return []
    if normalized in {"us", "usa", "united states"}:
        return []
    if normalized in {"eu", "european union"}:
        return [
            "EU MDR consolidated legislative text is not fully indexed (EUR-Lex endpoint unavailable). Support is grounded in European Commission UDI/EUDAMED requirements."
        ]
    return [
        f"Market '{market}' is not covered by the indexed corpus. Available indexed sources cover United States (FDA), European Union (EUDAMED/UDI), and International (IMDRF) regulations."
    ]


def evidence_state(
    element: str,
    refs: list[str],
    retrieved_jurisdictions: list[str],
    target_market: str | None,
    limitations: list[str],
) -> str:
    if not refs:
        return "evidence_gap"

    # Symbols standard ISO 15223-1 is paywalled/metadata-only
    if normalize_text(element) == "symbols":
        return "evidence_gap"

    # Unsupported market (e.g. India)
    if limitations and any("not covered" in lim for lim in limitations):
        return "potentially_relevant" if refs else "evidence_gap"

    target_norm = normalize_text(target_market or "")
    if target_norm in {"us", "usa", "united states"}:
        has_us = any("united states" in j.lower() for j in retrieved_jurisdictions)
        return "evidence_supported" if has_us else "potentially_relevant"

    if target_norm in {"eu", "european union"}:
        has_eu = any("european union" in j.lower() for j in retrieved_jurisdictions)
        return "evidence_supported" if has_eu else "potentially_relevant"

    if target_norm in {"international", "global"}:
        return "evidence_supported"

    return "evidence_supported" if refs else "evidence_gap"


def evidence_record(evidence_id: str, result: RetrievalResult) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "chunk_id": result.chunk.chunk_id,
        "source_id": result.chunk.source_id,
        "source_title": result.chunk.title,
        "publisher": result.chunk.publisher,
        "jurisdiction": result.chunk.jurisdiction,
        "url": result.chunk.url,
        "page": result.chunk.page,
        "section": result.chunk.section,
        "retrieval_score": round(result.score, 4),
        "excerpt": result.chunk.text[:900],
    }


def assess_change_impact(payload: dict[str, Any], top_k: int = 3) -> dict[str, Any]:
    request = parse_change_request(payload)
    retriever = LocalTfidfRetriever.load()
    product_context = request["product_context"]
    market = product_context.get("market") if isinstance(product_context.get("market"), str) else None
    limitations = market_limitations(market)
    target_jurisdiction = map_jurisdiction(market)

    profiles = detect_candidate_profiles(
        request["change_description"],
        request.get("change_category"),
        request["current_label_elements"],
    )

    paired_elements = map_candidate_elements(profiles, request["current_label_elements"])

    evidence: list[dict[str, Any]] = []
    affected: list[dict[str, Any]] = []
    reasons: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    missing: list[str] = []
    evidence_counter = 1
    seen_evidence_chunks: dict[str, str] = {}

    if not paired_elements:
        missing.append("No deterministic impact rule matched the proposed change; manual triage is required.")

    for elem_name, profile in paired_elements:
        # Search jurisdiction-aware first
        raw_results = retriever.search(profile.evidence_query, top_k=top_k, jurisdiction=target_jurisdiction)
        results = [r for r in raw_results if r.score >= 0.05]

        # Fallback to general search if jurisdiction filter returned empty
        if not results:
            raw_results = retriever.search(profile.evidence_query, top_k=top_k)
            results = [r for r in raw_results if r.score >= 0.05]

        refs: list[str] = []
        retrieved_jurs: list[str] = []
        top_excerpt = ""
        for result in results[:2]:
            retrieved_jurs.append(result.chunk.jurisdiction)
            if not top_excerpt:
                top_excerpt = result.chunk.text[:400]
            if result.chunk.chunk_id in seen_evidence_chunks:
                refs.append(seen_evidence_chunks[result.chunk.chunk_id])
                continue
            ev_id = f"EV{evidence_counter:03d}"
            evidence_counter += 1
            seen_evidence_chunks[result.chunk.chunk_id] = ev_id
            refs.append(ev_id)
            evidence.append(evidence_record(ev_id, result))

        state = evidence_state(elem_name, refs, retrieved_jurs, market, limitations)
        unsupported = (state == "evidence_gap")

        # Element-level missing info
        elem_missing: list[str] = []
        for key in profile.missing_info_keys:
            if key not in missing:
                missing.append(key)
            elem_missing.append(key)

        affected.append(
            {
                "element": elem_name,
                "impact": "review_required",
                "relationship": profile.relationship,
                "evidence_state": state,
                "evidence_refs": refs,
                "jurisdiction": market or "Unspecified",
                "relevant_excerpt": top_excerpt,
                "reason": profile.reason,
                "recommended_action": profile.review_action,
                "missing_information": elem_missing,
                "unsupported_by_current_corpus": unsupported,
                "human_review_required": True,
            }
        )

        reasons.append(
            {
                "element": elem_name,
                "reason": profile.reason if refs else f"{profile.reason} No supporting passage was retrieved from the indexed corpus.",
                "evidence_state": state,
                "evidence_refs": refs,
            }
        )

        actions.append(
            {
                "element": elem_name,
                "action": profile.review_action,
                "human_review_required": True,
            }
        )

    # Symbol paywall limitation disclosure
    if any(item["element"] == "symbols" for item in affected):
        sym_lim = "Full text of ISO 15223-1 and ISO 20417 is copyrighted/paywalled and not indexed in this corpus."
        if sym_lim not in limitations:
            limitations.append(sym_lim)

    missing.extend([lim for lim in limitations if lim not in missing])

    confidence = "medium" if evidence and not limitations else "low"
    if not evidence:
        confidence = "very_low"

    return {
        "change_id": request["change_id"],
        "product_context": product_context,
        "change_description": request["change_description"],
        "affected_label_elements": affected,
        "supporting_evidence": evidence,
        "reason_for_impact": reasons,
        "recommended_review_actions": actions,
        "missing_information": missing,
        "confidence_or_uncertainty": {
            "overall": confidence,
            "basis": "Structured multi-stage change analysis with jurisdiction-aware TF-IDF retrieval from official regulatory sources. This is not a compliance determination.",
        },
        "human_review_required": True,
        "source_coverage_limitations": limitations
        + [
            "Outputs are informational and require qualified regulatory review by regulatory affairs professionals.",
            "This platform does not certify regulatory compliance.",
        ],
    }


def assess_change_impact_file(input_path: Path, output_path: Path) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    assessment = assess_change_impact(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(assessment, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return assessment
