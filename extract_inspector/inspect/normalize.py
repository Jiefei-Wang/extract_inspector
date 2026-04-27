from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable, Mapping
from numbers import Number
from typing import Any
import warnings

import pandas as pd

from extract_inspector.inspect.models import ExtractionItem, Field, GroupData, InspectorDataset, Span, TextDocument


def normalize_id(value: Any) -> str:
    if isinstance(value, Number) and not isinstance(value, bool) and float(value).is_integer():
        return str(int(value))
    return str(value)


def labelize(value: str) -> str:
    return value.replace("_", " ").title()


def normalize_evidence_columns(evidence_col: str | Iterable[str] | None) -> list[str]:
    if evidence_col is None:
        return []
    if isinstance(evidence_col, str):
        return [evidence_col]
    columns = list(evidence_col)
    if not all(isinstance(column, str) for column in columns):
        raise TypeError("evidence_col must be a string, a list of strings, or None.")
    return columns


def normalize_evidence_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, float) and pd.isna(value):
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, (list, tuple, set)):
        evidence = []
        for entry in value:
            if isinstance(entry, str):
                stripped = entry.strip()
                if stripped:
                    evidence.append(stripped)
        return evidence
    return []


def collect_evidence(row: Mapping[str, Any], evidence_columns: list[str]) -> list[str]:
    evidence = []
    for column in evidence_columns:
        if column in row:
            evidence.extend(normalize_evidence_value(row[column]))
    return evidence


def collect_evidence_by_column(row: Mapping[str, Any], evidence_columns: list[str]) -> dict[str, list[str]]:
    evidence_by_column = OrderedDict()
    for column in evidence_columns:
        if column not in row:
            continue
        evidence = normalize_evidence_value(row[column])
        if evidence:
            evidence_by_column[column] = evidence
    return dict(evidence_by_column)


def is_null(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    return False


def normalize_span_cell(value: Any) -> list[Any]:
    if is_null(value):
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            parsed = float(stripped)
        except ValueError:
            return None
        if parsed.is_integer():
            return int(parsed)
    return None


def warn_span(message: str, item_id: str | None = None) -> None:
    prefix = f"Skipping span for item {item_id}: " if item_id else "Skipping span: "
    warnings.warn(prefix + message, stacklevel=2)


def collect_spans(
    row: Mapping[str, Any],
    text: str,
    span_start_col: str | None,
    span_end_col: str | None,
    item_id: str,
) -> list[Span]:
    if not span_start_col and not span_end_col:
        return []
    if not span_start_col or not span_end_col:
        warn_span("both span_start_col and span_end_col must be configured.", item_id)
        return []
    has_start = span_start_col in row
    has_end = span_end_col in row
    if not has_start and not has_end:
        return []
    if not has_start or not has_end:
        warn_span(f"missing {span_start_col!r} or {span_end_col!r} column value.", item_id)
        return []

    starts = normalize_span_cell(row[span_start_col])
    ends = normalize_span_cell(row[span_end_col])
    if not starts and not ends:
        return []
    if len(starts) != len(ends):
        warn_span(
            f"{span_start_col!r} and {span_end_col!r} have different lengths "
            f"({len(starts)} != {len(ends)}).",
            item_id,
        )
        return []

    spans = []
    for start_value, end_value in zip(starts, ends):
        start = coerce_int(start_value)
        end = coerce_int(end_value)
        if start is None or end is None:
            warn_span(f"non-integer offsets {start_value!r}, {end_value!r}.", item_id)
            continue
        if not (0 <= start < end <= len(text)):
            warn_span(f"invalid offset range [{start}, {end}) for text length {len(text)}.", item_id)
            continue
        spans.append(Span(start=start, end=end, text=text[start:end]))
    return spans


def normalize_frame(df: pd.DataFrame, name: str) -> list[dict]:
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame.")
    clean_df = df.astype(object).where(pd.notna(df), None)
    return clean_df.to_dict(orient="records")


def normalize_extractions_input(
    extractions: pd.DataFrame | Mapping[str, pd.DataFrame],
    extraction_group: str | None,
) -> OrderedDict[str, pd.DataFrame]:
    if isinstance(extractions, pd.DataFrame):
        return OrderedDict([(extraction_group or "extractions", extractions)])
    if isinstance(extractions, Mapping):
        normalized = OrderedDict()
        for key, value in extractions.items():
            if not isinstance(key, str):
                raise TypeError("Extraction group names must be strings.")
            if not isinstance(value, pd.DataFrame):
                raise TypeError(f"Extraction group {key!r} must be a pandas DataFrame.")
            normalized[key] = value
        return normalized
    raise TypeError("extractions must be a pandas DataFrame or a dict of DataFrames.")


def build_item_fields(
    row: Mapping[str, Any],
    excluded: set[str],
    field_labels: Mapping[str, str] | None,
) -> list[Field]:
    fields = []
    for key, value in row.items():
        if key in excluded or value in (None, "", []):
            continue
        label = field_labels.get(key, labelize(key)) if field_labels else labelize(key)
        fields.append(Field(label=label, value=value))
    return fields


def normalize_dataset(
    texts: pd.DataFrame,
    extractions: pd.DataFrame | Mapping[str, pd.DataFrame],
    *,
    text_id: str = "text_id",
    text_col: str = "text",
    subject_id: str | None = "subject_id",
    extraction_id: str | None = None,
    extraction_group: str | None = None,
    evidence_col: str | Iterable[str] | None = "evidence",
    confidence_col: str | None = "confidence",
    span_start_col: str | None = None,
    span_end_col: str | None = None,
    exclude_fields: Iterable[str] | None = None,
    field_labels: Mapping[str, str] | None = None,
    group_labels: Mapping[str, str] | None = None,
) -> InspectorDataset:
    text_rows = normalize_frame(texts, "texts")
    if text_id not in texts.columns:
        raise ValueError(f"texts is missing required column {text_id!r}.")
    if text_col not in texts.columns:
        raise ValueError(f"texts is missing required column {text_col!r}.")

    has_subject_id = bool(subject_id and subject_id in texts.columns)
    text_lookup: OrderedDict[str, TextDocument] = OrderedDict()
    for row in text_rows:
        current_text_id = normalize_id(row[text_id])
        current_text = row.get(text_col)
        if current_text is None:
            current_text = ""
        subject_value = row.get(subject_id) if has_subject_id else None
        text_lookup[current_text_id] = TextDocument(
            text_id=current_text_id,
            subject_id=normalize_id(subject_value) if subject_value is not None else None,
            text=str(current_text),
        )

    evidence_columns = normalize_evidence_columns(evidence_col)
    extraction_tables = normalize_extractions_input(extractions, extraction_group)
    groups: OrderedDict[str, GroupData] = OrderedDict()
    has_confidence = bool(confidence_col)

    structural_fields = {text_id}
    for optional in [extraction_id, extraction_group, confidence_col, span_start_col, span_end_col, *evidence_columns]:
        if optional:
            structural_fields.add(optional)
    if subject_id:
        structural_fields.add(subject_id)
    if text_col:
        structural_fields.add(text_col)
    if exclude_fields:
        structural_fields.update(exclude_fields)

    group_documents_by_key: OrderedDict[str, OrderedDict[str, TextDocument]] = OrderedDict()

    for table_group_key, frame in extraction_tables.items():
        if text_id not in frame.columns:
            raise ValueError(f"extractions group {table_group_key!r} is missing required column {text_id!r}.")

        rows = normalize_frame(frame, f"extractions[{table_group_key!r}]")
        if confidence_col and confidence_col not in frame.columns:
            has_confidence = False

        for row_index, row in enumerate(rows):
            current_text_id = normalize_id(row[text_id])
            source_document = text_lookup.get(current_text_id)
            if source_document is None:
                continue

            row_group_key = (
                normalize_id(row[extraction_group])
                if extraction_group and row.get(extraction_group)
                else table_group_key
            )
            group_documents = group_documents_by_key.setdefault(row_group_key, OrderedDict())
            if current_text_id not in group_documents:
                group_documents[current_text_id] = TextDocument(
                    text_id=source_document.text_id,
                    subject_id=source_document.subject_id,
                    text=source_document.text,
                )

            row_group_label = (
                group_labels.get(row_group_key, labelize(row_group_key))
                if group_labels
                else labelize(row_group_key)
            )
            item_id = (
                normalize_id(row[extraction_id])
                if extraction_id and row.get(extraction_id) not in (None, "")
                else f"{row_group_key}:{current_text_id}:{row_index}"
            )
            item = ExtractionItem(
                item_id=item_id,
                text_id=current_text_id,
                group=row_group_key,
                summary=row_group_label,
                evidence=collect_evidence(row, evidence_columns),
                evidence_by_column=collect_evidence_by_column(row, evidence_columns),
                spans=collect_spans(
                    row,
                    source_document.text,
                    span_start_col,
                    span_end_col,
                    item_id,
                ),
                confidence=row.get(confidence_col) if confidence_col else None,
                fields=build_item_fields(row, structural_fields, field_labels),
            )
            group_documents[current_text_id].items.append(item)

    for group_key, group_documents in group_documents_by_key.items():
        group_label = group_labels.get(group_key, labelize(group_key)) if group_labels else labelize(group_key)
        groups[group_key] = GroupData(
            key=group_key,
            label=group_label,
            text_ids=list(group_documents.keys()),
            texts=dict(group_documents),
        )

    return InspectorDataset(groups=dict(groups), has_subject_id=has_subject_id, has_confidence=has_confidence)
