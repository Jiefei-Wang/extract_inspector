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


def normalize_highlight_columns(highlight_col: str | Iterable[str] | None) -> list[str]:
    if highlight_col is None:
        return []
    if isinstance(highlight_col, str):
        return [highlight_col]
    columns = list(highlight_col)
    if not all(isinstance(column, str) for column in columns):
        raise TypeError("highlight_col must be a string, a list of strings, or None.")
    return columns


def normalize_highlight_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, float) and pd.isna(value):
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, (list, tuple, set)):
        highlights = []
        for entry in value:
            if isinstance(entry, str):
                stripped = entry.strip()
                if stripped:
                    highlights.append(stripped)
        return highlights
    return []


def collect_highlights(row: Mapping[str, Any], highlight_columns: list[str]) -> list[str]:
    highlights = []
    for column in highlight_columns:
        if column in row:
            highlights.extend(normalize_highlight_value(row[column]))
    return highlights


def collect_highlights_by_column(row: Mapping[str, Any], highlight_columns: list[str]) -> dict[str, list[str]]:
    highlights_by_column = OrderedDict()
    for column in highlight_columns:
        if column not in row:
            continue
        highlights = normalize_highlight_value(row[column])
        if highlights:
            highlights_by_column[column] = highlights
    return dict(highlights_by_column)


def is_null(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, set, dict)):
        return False
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    if isinstance(missing, bool):
        return missing
    if getattr(missing, "shape", None) == ():
        return bool(missing)
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


def normalize_categorical_filter_columns(filter_categorical_cols: str | Iterable[str] | None) -> list[str]:
    if filter_categorical_cols is None:
        return []
    if isinstance(filter_categorical_cols, str):
        return [filter_categorical_cols]
    columns = list(filter_categorical_cols)
    if not all(isinstance(column, str) for column in columns):
        raise TypeError("filter_categorical_cols must be a string, a list of strings, or None.")
    return columns


def normalize_filter_value(value: Any) -> str | None:
    if is_null(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, Number):
        return normalize_id(value)
    return None


def collect_filter_values(row: Mapping[str, Any], filter_columns: list[str]) -> dict[str, str]:
    values = OrderedDict()
    for column in filter_columns:
        if column not in row:
            continue
        value = normalize_filter_value(row[column])
        if value is not None:
            values[column] = value
    return dict(values)


def normalize_frame(df: pd.DataFrame, name: str) -> list[dict]:
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame.")
    clean_df = df.astype(object).where(pd.notna(df), None)
    return clean_df.to_dict(orient="records")


def is_missing_required_value(value: Any) -> bool:
    if is_null(value):
        return True
    return isinstance(value, str) and not value.strip()


def warn_missing_required_row(*, column: str, row_index: int, table_name: str) -> None:
    warnings.warn(
        f"Skipping {table_name} row {row_index}: missing required value {column!r}.",
        stacklevel=2,
    )


def normalize_extractions_input(
    extractions: pd.DataFrame | Mapping[str, pd.DataFrame],
    extraction_group: str | None,
) -> OrderedDict[str, pd.DataFrame]:
    if isinstance(extractions, pd.DataFrame):
        group_key = extraction_group if extraction_group and extraction_group in extractions.columns else "extractions"
        return OrderedDict([(group_key, extractions)])
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
        if key in excluded or is_empty_field_value(value):
            continue
        label = field_labels.get(key, labelize(key)) if field_labels else labelize(key)
        fields.append(Field(label=label, value=value))
    return fields


def is_empty_field_value(value: Any) -> bool:
    if is_null(value):
        return True
    if isinstance(value, str):
        return value == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    if hasattr(value, "size"):
        return value.size == 0
    return False


def normalize_dataset(
    texts: pd.DataFrame,
    extractions: pd.DataFrame | Mapping[str, pd.DataFrame],
    *,
    text_id: str = "text_id",
    text_col: str = "text",
    subject_id: str | None = "subject_id",
    extraction_id: str | None = None,
    extraction_group: str | None = None,
    highlight_col: str | Iterable[str] | None = "evidence",
    span_start_col: str | None = None,
    span_end_col: str | None = None,
    filter_categorical_cols: str | Iterable[str] | None = None,
    exclude_fields: Iterable[str] | None = None,
    field_labels: Mapping[str, str] | None = None,
) -> InspectorDataset:
    text_rows = normalize_frame(texts, "texts")
    if text_id not in texts.columns:
        raise ValueError(f"texts is missing required column {text_id!r}.")
    if text_col not in texts.columns:
        raise ValueError(f"texts is missing required column {text_col!r}.")

    has_subject_id = bool(subject_id and subject_id in texts.columns)
    text_lookup: OrderedDict[str, TextDocument] = OrderedDict()
    for row_index, row in enumerate(text_rows):
        current_text_id_value = row.get(text_id)
        if is_missing_required_value(current_text_id_value):
            warn_missing_required_row(column=text_id, row_index=row_index, table_name="texts")
            continue
        current_text = row.get(text_col)
        if is_missing_required_value(current_text):
            warn_missing_required_row(column=text_col, row_index=row_index, table_name="texts")
            continue
        current_text_id = normalize_id(current_text_id_value)
        subject_value = row.get(subject_id) if has_subject_id else None
        text_lookup[current_text_id] = TextDocument(
            text_id=current_text_id,
            subject_id=normalize_id(subject_value) if subject_value is not None else None,
            text=str(current_text),
        )

    highlight_columns = normalize_highlight_columns(highlight_col)
    filter_columns = normalize_categorical_filter_columns(filter_categorical_cols)
    extraction_tables = normalize_extractions_input(extractions, extraction_group)
    groups: OrderedDict[str, GroupData] = OrderedDict()

    structural_fields = {text_id}
    for optional in [extraction_id, extraction_group, span_start_col, span_end_col, *highlight_columns]:
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
        for row_index, row in enumerate(rows):
            current_text_id_value = row.get(text_id)
            if is_missing_required_value(current_text_id_value):
                warn_missing_required_row(
                    column=text_id,
                    row_index=row_index,
                    table_name=f"extractions group {table_group_key!r}",
                )
                continue
            current_text_id = normalize_id(current_text_id_value)
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

            row_group_label = labelize(row_group_key)
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
                highlights=collect_highlights(row, highlight_columns),
                highlights_by_column=collect_highlights_by_column(row, highlight_columns),
                spans=collect_spans(
                    row,
                    source_document.text,
                    span_start_col,
                    span_end_col,
                    item_id,
                ),
                filter_values=collect_filter_values(row, filter_columns),
                fields=build_item_fields(row, structural_fields, field_labels),
            )
            group_documents[current_text_id].items.append(item)

    for group_key, group_documents in group_documents_by_key.items():
        group_label = labelize(group_key)
        groups[group_key] = GroupData(
            key=group_key,
            label=group_label,
            text_ids=list(group_documents.keys()),
            texts=dict(group_documents),
        )

    return InspectorDataset(
        groups=dict(groups),
        has_subject_id=has_subject_id,
        filter_categorical_cols=filter_columns,
    )
