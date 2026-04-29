from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

FILTER_METHODS = {"dropdown", "textbox", "multitext", "button"}
FilterInput = str | dict[str, str]


def _as_list(value: str | list[str] | tuple[str, ...] | None, name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    values = list(value)
    if not all(isinstance(entry, str) for entry in values):
        raise TypeError(f"{name} must contain only strings.")
    return values


def _as_filter_inputs(
    value: FilterInput | list[FilterInput] | tuple[FilterInput, ...] | None,
    name: str,
) -> list[FilterInput]:
    if value is None:
        return []
    if isinstance(value, (str, dict)):
        return [value]
    values = list(value)
    if not all(isinstance(entry, (str, dict)) for entry in values):
        raise TypeError(f"{name} must contain only strings or one-key dictionaries.")
    return values


@dataclass(frozen=True)
class FilterSpec:
    column: str
    method: str
    label: str

    def __post_init__(self) -> None:
        if not isinstance(self.column, str) or not self.column:
            raise ValueError("filter column must be a non-empty string.")
        if self.method not in FILTER_METHODS:
            raise ValueError(f"filter method must be one of {sorted(FILTER_METHODS)}.")


@dataclass(frozen=True)
class Corpus:
    texts: pd.DataFrame
    text_id_col: str = "text_id"
    text_col: str = "text"
    text_title: str = "Text: {text_id}"

    def __post_init__(self) -> None:
        if not isinstance(self.texts, pd.DataFrame):
            raise TypeError("texts must be a pandas DataFrame.")
        if not isinstance(self.text_id_col, str) or not self.text_id_col:
            raise ValueError("text_id_col must be a non-empty string.")
        if not isinstance(self.text_col, str) or not self.text_col:
            raise ValueError("text_col must be a non-empty string.")
        if self.text_id_col not in self.texts.columns:
            raise ValueError(f"texts is missing required column {self.text_id_col!r}.")
        if self.text_col not in self.texts.columns:
            raise ValueError(f"texts is missing required column {self.text_col!r}.")


@dataclass(frozen=True)
class Inspector:
    tag_name: str
    entities: pd.DataFrame
    text_id_col: str = "text_id"
    entity_title: str = ""
    shown_cols: list[str] | tuple[str, ...] | None = None
    highlight_cols: list[str] | tuple[str, ...] | None = None
    highlight_span_start_cols: list[str] | tuple[str, ...] | None = None
    highlight_span_end_cols: list[str] | tuple[str, ...] | None = None
    highlight_relations: dict[str, str | list[str] | tuple[str, ...]] | None = None
    filter_cols: FilterInput | list[FilterInput] | tuple[FilterInput, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.tag_name, str) or not self.tag_name.strip():
            raise ValueError("tag_name must be a non-empty string.")
        if not isinstance(self.entities, pd.DataFrame):
            raise TypeError("entities must be a pandas DataFrame.")
        if not isinstance(self.text_id_col, str) or not self.text_id_col:
            raise ValueError("text_id_col must be a non-empty string.")
        if self.text_id_col not in self.entities.columns:
            raise ValueError(f"Inspector {self.tag_name!r} is missing text id column {self.text_id_col!r}.")

        starts = _as_list(self.highlight_span_start_cols, "highlight_span_start_cols")
        ends = _as_list(self.highlight_span_end_cols, "highlight_span_end_cols")
        if len(starts) != len(ends):
            raise ValueError("highlight_span_start_cols and highlight_span_end_cols must have the same length.")

        object.__setattr__(self, "tag_name", self.tag_name.strip())
        object.__setattr__(self, "shown_cols", _as_list(self.shown_cols, "shown_cols"))
        object.__setattr__(self, "highlight_cols", _as_list(self.highlight_cols, "highlight_cols"))
        object.__setattr__(self, "highlight_span_start_cols", starts)
        object.__setattr__(self, "highlight_span_end_cols", ends)
        object.__setattr__(self, "filter_cols", _as_filter_inputs(self.filter_cols, "filter_cols"))
        object.__setattr__(self, "highlight_relations", normalize_relations(self.highlight_relations))


def normalize_relations(
    relations: dict[str, str | list[str] | tuple[str, ...]] | None,
) -> dict[str, list[str]]:
    if not relations:
        return {}
    normalized = {}
    for source, targets in relations.items():
        if isinstance(targets, str):
            normalized[source] = [targets]
        else:
            target_list = list(targets)
            if not all(isinstance(target, str) for target in target_list):
                raise TypeError("highlight_relations values must be strings or lists of strings.")
            normalized[source] = target_list
    return normalized


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    value: Any


@dataclass(frozen=True)
class Highlight:
    source: str
    text: str
    related_fields: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    text: str
    source: str
    related_fields: list[str] = field(default_factory=list)


@dataclass
class ExtractionItem:
    item_id: str
    text_id: str
    tag: str
    title: str
    fields: list[Field] = field(default_factory=list)
    highlights: list[Highlight] = field(default_factory=list)
    spans: list[Span] = field(default_factory=list)
    filter_values: dict[str, str] = field(default_factory=dict)
    has_match: bool = False


@dataclass
class TextDocument:
    text_id: str
    text: str
    title: str
    filter_values: dict[str, str] = field(default_factory=dict)
    items: list[ExtractionItem] = field(default_factory=list)


@dataclass
class GroupData:
    key: str
    label: str
    text_ids: list[str]
    texts: dict[str, TextDocument]
    filter_blocks: list[dict] = field(default_factory=list)


@dataclass
class InspectorDataset:
    groups: dict[str, GroupData]
