from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Field:
    label: str
    value: Any


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    text: str


@dataclass
class ExtractionItem:
    item_id: str
    text_id: str
    group: str
    summary: str
    evidence: list[str]
    evidence_by_column: dict[str, list[str]] = field(default_factory=dict)
    spans: list[Span] = field(default_factory=list)
    confidence: Any = None
    fields: list[Field] = field(default_factory=list)
    has_match: bool = False


@dataclass
class TextDocument:
    text_id: str
    text: str
    subject_id: str | None = None
    items: list[ExtractionItem] = field(default_factory=list)


@dataclass
class GroupData:
    key: str
    label: str
    text_ids: list[str]
    texts: dict[str, TextDocument]


@dataclass
class InspectorDataset:
    groups: dict[str, GroupData]
    has_subject_id: bool
    has_confidence: bool
