from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    official_title: str
    publisher: str
    jurisdiction: str
    url: str
    document_date: str | None = None
    access_status: str = "unknown"
    source_type: str = "html"
    local_path: str | None = None
    notes: str = ""
    discovered_at: str | None = None


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_id: str
    title: str
    publisher: str
    jurisdiction: str
    url: str
    text: str
    section: str | None = None
    page: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    chunk: Chunk
    score: float
    rank: int


@dataclass(frozen=True)
class EvaluationRecord:
    question_id: str
    question: str
    expected_answer: str
    expected_key_facts: list[str]
    expected_source_ids: list[str]
    expected_page_or_section: list[str]
    jurisdiction: str
    answerable_from_corpus: bool
    rationale: str
