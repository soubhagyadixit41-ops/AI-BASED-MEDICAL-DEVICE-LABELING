from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


LABEL_FIELD_DEFINITIONS: dict[str, str] = {
    "product_name_identifier": "Product Name & Model / Catalog Number",
    "manufacturer_info": "Manufacturer Name, Place of Business & Address",
    "intended_purpose": "Intended Purpose & Indications for Use",
    "device_description": "Device Description & Technical Specifications",
    "warnings_precautions": "Warnings, Precautions & Contraindications",
    "instructions_for_use": "Instructions for Use (IFU) & Directions",
    "storage_handling": "Storage & Handling Conditions",
    "sterilization_info": "Sterilization Method & Sterile Barrier Status",
    "shelf_life_expiry": "Shelf-Life & Expiration Dating",
    "udi_identifiers": "UDI (DI + PI) & Machine-Readable Carrier",
    "symbols_descriptions": "Graphical Symbols & Symbol Descriptions",
    "target_jurisdiction": "Target Regulatory Jurisdiction",
    "language": "Label Language(s)",
    "label_version_status": "Label Version & Status",
}


@dataclass
class LabelDocument:
    label_id: str
    product_name: str
    version: str
    status: str  # "approved", "draft", "under_review", "rejected"
    target_jurisdiction: str
    language: str
    fields: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_field(self, field_id: str, default: str = "") -> str:
        return self.fields.get(field_id, default)

    def set_field(self, field_id: str, value: str) -> None:
        self.fields[field_id] = value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LabelDocument:
        return cls(
            label_id=str(data.get("label_id", "")),
            product_name=str(data.get("product_name", "")),
            version=str(data.get("version", "v1.0")),
            status=str(data.get("status", "draft")),
            target_jurisdiction=str(data.get("target_jurisdiction", "US")),
            language=str(data.get("language", "en-US")),
            fields={str(k): str(v) for k, v in data.get("fields", {}).items()},
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class FieldDiff:
    field_id: str
    label_name: str
    original_value: str
    proposed_value: str
    change_type: str  # "added" | "removed" | "modified" | "unchanged"
    reason_for_change: str
    evidence_refs: list[str] = field(default_factory=list)
    evidence_state: str = "not_applicable"  # "evidence_supported" | "potentially_relevant" | "evidence_gap" | "not_applicable"
    review_status: str = "Pending"  # "Pending" | "Accepted" | "Needs revision" | "Rejected"
    reviewer_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FieldDiff:
        return cls(
            field_id=str(data.get("field_id", "")),
            label_name=str(data.get("label_name", "")),
            original_value=str(data.get("original_value", "")),
            proposed_value=str(data.get("proposed_value", "")),
            change_type=str(data.get("change_type", "unchanged")),
            reason_for_change=str(data.get("reason_for_change", "")),
            evidence_refs=[str(x) for x in data.get("evidence_refs", [])],
            evidence_state=str(data.get("evidence_state", "not_applicable")),
            review_status=str(data.get("review_status", "Pending")),
            reviewer_notes=str(data.get("reviewer_notes", "")),
        )


@dataclass
class VersionComparisonReport:
    report_id: str
    label_id: str
    from_version: str
    to_version: str
    target_jurisdiction: str
    total_fields: int
    modified_fields: int
    unchanged_fields: int
    added_fields: int
    removed_fields: int
    field_diffs: list[FieldDiff]
    overall_human_review_required: bool = True
    missing_information: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VersionComparisonReport:
        return cls(
            report_id=str(data.get("report_id", "")),
            label_id=str(data.get("label_id", "")),
            from_version=str(data.get("from_version", "")),
            to_version=str(data.get("to_version", "")),
            target_jurisdiction=str(data.get("target_jurisdiction", "")),
            total_fields=int(data.get("total_fields", 0)),
            modified_fields=int(data.get("modified_fields", 0)),
            unchanged_fields=int(data.get("unchanged_fields", 0)),
            added_fields=int(data.get("added_fields", 0)),
            removed_fields=int(data.get("removed_fields", 0)),
            field_diffs=[FieldDiff.from_dict(d) for d in data.get("field_diffs", [])],
            overall_human_review_required=bool(data.get("overall_human_review_required", True)),
            missing_information=[str(x) for x in data.get("missing_information", [])],
            limitations=[str(x) for x in data.get("limitations", [])],
            metadata=dict(data.get("metadata", {})),
        )
