from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from numbers import Number
from typing import Any
import warnings

import pandas as pd

from extract_inspector.inspect.models import (
    ExtractionItem,
    Field,
    GroupData,
    Highlight,
    Inspector,
    InspectorDataset,
    Span,
    TextDocument,
)


def normalize_id(value: Any) -> str:
    if isinstance(value, Number) and not isinstance(value, bool) and float(value).is_integer():
        return str(int(value))
    return str(value)


def labelize(value: str) -> str:
    return value.replace("_", " ").title()


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


def is_missing_required_value(value: Any) -> bool:
    if is_null(value):
        return True
    return isinstance(value, str) and not value.strip()


def warn_missing_required_row(*, column: str, row_index: int, table_name: str) -> None:
    warnings.warn(
        f"Skipping {table_name} row {row_index}: missing required value {column!r}.",
        stacklevel=2,
    )


def normalize_frame(df: pd.DataFrame, name: str) -> list[dict]:
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame.")
    clean_df = df.astype(object).where(pd.notna(df), None)
    return clean_df.to_dict(orient="records")


def normalize_highlight_value(value: Any) -> list[str]:
    if is_null(value):
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


def format_template(template: str, row: Mapping[str, Any], fallback: str) -> str:
    if not template:
        return fallback
    values = {key: "" if is_null(value) else value for key, value in row.items()}
    try:
        rendered = template.format(**values)
    except (KeyError, ValueError, IndexError):
        return fallback
    return rendered.strip() or fallback


def related_fields_for(inspector: Inspector, source: str) -> list[str]:
    shown = set(inspector.shown_cols or [])
    return [field for field in inspector.highlight_relations.get(source, []) if field in shown]


def build_fields(row: Mapping[str, Any], shown_cols: list[str]) -> list[Field]:
    fields = []
    for column in shown_cols:
        if column not in row or is_empty_field_value(row[column]):
            continue
        fields.append(Field(key=column, label=labelize(column), value=row[column]))
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


def collect_highlights(row: Mapping[str, Any], inspector: Inspector) -> list[Highlight]:
    highlights = []
    for column in inspector.highlight_cols or []:
        if column not in row:
            continue
        for value in normalize_highlight_value(row[column]):
            highlights.append(
                Highlight(
                    source=column,
                    text=value,
                    related_fields=related_fields_for(inspector, column),
                )
            )
    return highlights


def collect_spans(row: Mapping[str, Any], text: str, inspector: Inspector, item_id: str) -> list[Span]:
    spans = []
    starts = inspector.highlight_span_start_cols or []
    ends = inspector.highlight_span_end_cols or []
    for start_col, end_col in zip(starts, ends):
        source = f"{start_col}:{end_col}"
        has_start = start_col in row
        has_end = end_col in row
        if not has_start and not has_end:
            continue
        if not has_start or not has_end:
            warn_span(f"missing {start_col!r} or {end_col!r} column value.", item_id)
            continue

        start_values = normalize_span_cell(row[start_col])
        end_values = normalize_span_cell(row[end_col])
        if not start_values and not end_values:
            continue
        if len(start_values) != len(end_values):
            warn_span(
                f"{start_col!r} and {end_col!r} have different lengths "
                f"({len(start_values)} != {len(end_values)}).",
                item_id,
            )
            continue

        related_fields = related_fields_for(inspector, source)
        for start_value, end_value in zip(start_values, end_values):
            start = coerce_int(start_value)
            end = coerce_int(end_value)
            if start is None or end is None:
                warn_span(f"non-integer offsets {start_value!r}, {end_value!r}.", item_id)
                continue
            if not (0 <= start < end <= len(text)):
                warn_span(f"invalid offset range [{start}, {end}) for text length {len(text)}.", item_id)
                continue
            spans.append(
                Span(
                    start=start,
                    end=end,
                    text=text[start:end],
                    source=source,
                    related_fields=related_fields,
                )
            )
    return spans


def clone_document(document: TextDocument) -> TextDocument:
    return TextDocument(
        text_id=document.text_id,
        subject_id=document.subject_id,
        text=document.text,
        title=document.title,
    )


def append_item(group_documents: OrderedDict[str, TextDocument], source_document: TextDocument, item: ExtractionItem) -> None:
    if source_document.text_id not in group_documents:
        group_documents[source_document.text_id] = clone_document(source_document)
    group_documents[source_document.text_id].items.append(item)


def normalize_dataset(
    texts: pd.DataFrame,
    inspectors: list[Inspector] | tuple[Inspector, ...],
    *,
    text_id_col: str = "text_id",
    text_col: str = "text",
    subject_id_col: str | None = "subject_id",
    text_title: str = "Text: {text_id}",
) -> InspectorDataset:
    if not inspectors:
        raise ValueError("At least one Inspector is required.")
    if not all(isinstance(inspector, Inspector) for inspector in inspectors):
        raise TypeError("inspectors must contain only Inspector instances.")

    text_rows = normalize_frame(texts, "texts")
    if text_id_col not in texts.columns:
        raise ValueError(f"texts is missing required column {text_id_col!r}.")
    if text_col not in texts.columns:
        raise ValueError(f"texts is missing required column {text_col!r}.")

    has_subject_id = bool(subject_id_col and subject_id_col in texts.columns)
    text_lookup: OrderedDict[str, TextDocument] = OrderedDict()
    for row_index, row in enumerate(text_rows):
        text_id_value = row.get(text_id_col)
        if is_missing_required_value(text_id_value):
            warn_missing_required_row(column=text_id_col, row_index=row_index, table_name="texts")
            continue
        current_text = row.get(text_col)
        if is_missing_required_value(current_text):
            warn_missing_required_row(column=text_col, row_index=row_index, table_name="texts")
            continue

        current_text_id = normalize_id(text_id_value)
        subject_value = row.get(subject_id_col) if has_subject_id else None
        title_context = dict(row)
        title_context["text_id"] = current_text_id
        text_lookup[current_text_id] = TextDocument(
            text_id=current_text_id,
            subject_id=normalize_id(subject_value) if subject_value is not None else None,
            text=str(current_text),
            title=format_template(text_title, title_context, f"Text: {current_text_id}"),
        )

    all_documents: OrderedDict[str, TextDocument] = OrderedDict()
    documents_by_tag: OrderedDict[str, OrderedDict[str, TextDocument]] = OrderedDict(
        (inspector.tag_name, OrderedDict()) for inspector in inspectors
    )

    for inspector in inspectors:
        rows = normalize_frame(inspector.entities, f"inspector[{inspector.tag_name!r}]")
        for row_index, row in enumerate(rows):
            text_id_value = row.get(inspector.text_id_col)
            if is_missing_required_value(text_id_value):
                warn_missing_required_row(
                    column=inspector.text_id_col,
                    row_index=row_index,
                    table_name=f"inspector {inspector.tag_name!r}",
                )
                continue
            current_text_id = normalize_id(text_id_value)
            source_document = text_lookup.get(current_text_id)
            if source_document is None:
                continue

            fallback_title = f"{labelize(inspector.tag_name)} {row_index + 1}"
            item_id = normalize_id(row["extraction_id"]) if row.get("extraction_id") not in (None, "") else (
                f"{inspector.tag_name}:{current_text_id}:{row_index}"
            )
            item = ExtractionItem(
                item_id=item_id,
                text_id=current_text_id,
                tag=inspector.tag_name,
                title=format_template(inspector.entity_title, row, fallback_title),
                fields=build_fields(row, inspector.shown_cols or []),
                highlights=collect_highlights(row, inspector),
                spans=collect_spans(row, source_document.text, inspector, item_id),
                filter_values=collect_filter_values(row, inspector.filter_cols or []),
            )
            append_item(all_documents, source_document, item)
            append_item(documents_by_tag[inspector.tag_name], source_document, item)

    groups: OrderedDict[str, GroupData] = OrderedDict()
    all_filter_cols = []
    for inspector in inspectors:
        for column in inspector.filter_cols or []:
            if column not in all_filter_cols:
                all_filter_cols.append(column)

    groups["all"] = GroupData(
        key="all",
        label="All",
        text_ids=list(all_documents.keys()),
        texts=dict(all_documents),
        filter_cols=all_filter_cols,
    )
    for inspector in inspectors:
        documents = documents_by_tag[inspector.tag_name]
        groups[inspector.tag_name] = GroupData(
            key=inspector.tag_name,
            label=labelize(inspector.tag_name),
            text_ids=list(documents.keys()),
            texts=dict(documents),
            filter_cols=list(inspector.filter_cols or []),
        )

    return InspectorDataset(groups=dict(groups), has_subject_id=has_subject_id)
