from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from datetime import date, datetime
from numbers import Number
from typing import Any
import warnings

import pandas as pd

from extract_inspector.inspect.models import (
    Corpus,
    ExtractionItem,
    Field,
    FilterInput,
    FilterSpec,
    GroupData,
    Highlight,
    Inspector,
    InspectorDataset,
    Span,
    TextDocument,
)

SUPPORTED_SCALARS = "string, number, bool, date, datetime, pandas timestamp, or null"
SUPPORTED_COLLECTIONS = f"{SUPPORTED_SCALARS}; collections may be lists, tuples, sets, or numpy-like arrays"


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


def type_name(value: Any) -> str:
    return type(value).__name__


def column_type_message(
    *,
    table_name: str,
    column: str,
    row_index: int,
    value: Any,
    expected: str,
) -> str:
    return (
        f"Unsupported value type for {table_name} row {row_index}, column {column!r}: "
        f"{type_name(value)}. Expected {expected}."
    )


def raise_unsupported_column_value(
    *,
    table_name: str,
    column: str,
    row_index: int,
    value: Any,
    expected: str,
) -> None:
    raise TypeError(
        column_type_message(
            table_name=table_name,
            column=column,
            row_index=row_index,
            value=value,
            expected=expected,
        )
    )


def warn_unsupported_column_value(
    *,
    table_name: str,
    column: str,
    row_index: int,
    value: Any,
    expected: str,
) -> None:
    warnings.warn(
        "Skipping value. "
        + column_type_message(
            table_name=table_name,
            column=column,
            row_index=row_index,
            value=value,
            expected=expected,
        ),
        stacklevel=3,
    )


def to_python_value(value: Any) -> Any:
    if is_null(value) or isinstance(value, (str, bytes, bytearray, Mapping)):
        return value
    if isinstance(value, (list, tuple, set)):
        return list(value)
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        try:
            converted = tolist()
        except (TypeError, ValueError):
            return value
        return converted
    return value


def normalize_display_value(
    value: Any,
    *,
    table_name: str,
    column: str,
    row_index: int,
) -> Any:
    value = to_python_value(value)
    if is_null(value):
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, Number):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (list, tuple, set)):
        values = []
        for entry in value:
            try:
                values.append(
                    normalize_scalar_value(
                        entry,
                        table_name=table_name,
                        column=column,
                        row_index=row_index,
                    )
                )
            except TypeError:
                warn_unsupported_column_value(
                    table_name=table_name,
                    column=column,
                    row_index=row_index,
                    value=entry,
                    expected=SUPPORTED_SCALARS,
                )
        return values
    raise_unsupported_column_value(
        table_name=table_name,
        column=column,
        row_index=row_index,
        value=value,
        expected=SUPPORTED_COLLECTIONS,
    )


def normalize_scalar_value(
    value: Any,
    *,
    table_name: str,
    column: str,
    row_index: int,
) -> Any:
    value = to_python_value(value)
    if is_null(value):
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, Number):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise_unsupported_column_value(
        table_name=table_name,
        column=column,
        row_index=row_index,
        value=value,
        expected=SUPPORTED_SCALARS,
    )


def normalize_required_scalar(
    value: Any,
    *,
    table_name: str,
    column: str,
    row_index: int,
) -> Any:
    normalized = normalize_scalar_value(
        value,
        table_name=table_name,
        column=column,
        row_index=row_index,
    )
    if is_missing_required_value(normalized):
        warn_missing_required_row(column=column, row_index=row_index, table_name=table_name)
        return None
    return normalized


def normalize_optional_id(
    row: Mapping[str, Any],
    *,
    table_name: str,
    row_index: int,
    fallback: str,
) -> str:
    column = "extraction_id"
    if column not in row or is_null(row[column]):
        return fallback
    value = row[column]
    if isinstance(value, str) and not value.strip():
        warn_unsupported_column_value(
            table_name=table_name,
            column=column,
            row_index=row_index,
            value=value,
            expected="a non-empty scalar value",
        )
        return fallback
    try:
        normalized = normalize_scalar_value(
            value,
            table_name=table_name,
            column=column,
            row_index=row_index,
        )
    except TypeError:
        warn_unsupported_column_value(
            table_name=table_name,
            column=column,
            row_index=row_index,
            value=value,
            expected=SUPPORTED_SCALARS,
        )
        return fallback
    if isinstance(normalized, Number) and not isinstance(normalized, bool):
        return normalize_id(normalized)
    return str(normalized)


def normalize_frame(df: pd.DataFrame, name: str) -> list[dict]:
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame.")
    records = df.astype(object).to_dict(orient="records")
    return [
        {column: None if is_null(value) else value for column, value in row.items()}
        for row in records
    ]


def normalize_highlight_value(
    value: Any,
    *,
    table_name: str,
    column: str,
    row_index: int,
) -> list[str]:
    if is_null(value):
        return []
    value = to_python_value(value)
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, (list, tuple, set)):
        highlights = []
        for entry in value:
            try:
                normalized = normalize_scalar_value(
                    entry,
                    table_name=table_name,
                    column=column,
                    row_index=row_index,
                )
            except TypeError:
                warn_unsupported_column_value(
                    table_name=table_name,
                    column=column,
                    row_index=row_index,
                    value=entry,
                    expected=SUPPORTED_SCALARS,
                )
                continue
            if normalized is None:
                continue
            stripped = str(normalized).strip()
            if stripped:
                highlights.append(stripped)
        return highlights
    try:
        normalized = normalize_scalar_value(
            value,
            table_name=table_name,
            column=column,
            row_index=row_index,
        )
    except TypeError:
        warn_unsupported_column_value(
            table_name=table_name,
            column=column,
            row_index=row_index,
            value=value,
            expected=SUPPORTED_COLLECTIONS,
        )
        return []
    stripped = str(normalized).strip()
    return [stripped] if stripped else []


def normalize_span_cell(
    value: Any,
    *,
    table_name: str,
    column: str,
    row_index: int,
) -> list[Any]:
    if is_null(value):
        return []
    value = to_python_value(value)
    if isinstance(value, (list, tuple, set)):
        return list(value)
    if isinstance(value, Mapping):
        warn_unsupported_column_value(
            table_name=table_name,
            column=column,
            row_index=row_index,
            value=value,
            expected="integer-like scalar or collection of integer-like scalars",
        )
        return []
    return [value]


def warn_span(message: str, item_id: str | None = None) -> None:
    prefix = f"Skipping span for item {item_id}: " if item_id else "Skipping span: "
    warnings.warn(prefix + message, stacklevel=2)


def normalize_filter_value(
    value: Any,
    *,
    table_name: str | None = None,
    column: str | None = None,
    row_index: int | None = None,
) -> str | None:
    if is_null(value):
        return None
    original = value
    value = to_python_value(value)
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, Number):
        return normalize_id(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if table_name is not None and column is not None and row_index is not None:
        warn_unsupported_column_value(
            table_name=table_name,
            column=column,
            row_index=row_index,
            value=original,
            expected=SUPPORTED_SCALARS,
        )
    return None


def collect_filter_values(
    row: Mapping[str, Any],
    filter_specs: list[FilterSpec],
    *,
    table_name: str,
    row_index: int,
) -> dict[str, str]:
    values = OrderedDict()
    for spec in filter_specs:
        column = spec.column
        if column not in row:
            continue
        value = normalize_filter_value(
            row[column],
            table_name=table_name,
            column=column,
            row_index=row_index,
        )
        if value is not None:
            values[column] = value
    return dict(values)


def normalize_template_values(
    row: Mapping[str, Any],
    *,
    table_name: str,
    row_index: int,
) -> dict[str, Any]:
    values = {}
    for column, value in row.items():
        if is_null(value):
            values[column] = ""
            continue
        try:
            values[column] = normalize_display_value(
                value,
                table_name=table_name,
                column=column,
                row_index=row_index,
            )
        except TypeError:
            warn_unsupported_column_value(
                table_name=table_name,
                column=column,
                row_index=row_index,
                value=value,
                expected=SUPPORTED_COLLECTIONS,
            )
            values[column] = ""
    return values


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


def normalize_filter_spec_inputs(
    filter_cols: FilterInput | list[FilterInput] | tuple[FilterInput, ...] | None,
) -> list[tuple[str, str | None]]:
    if isinstance(filter_cols, (str, dict)):
        filter_cols = [filter_cols]
    specs = []
    for entry in filter_cols or []:
        if isinstance(entry, str):
            specs.append((entry, None))
            continue
        if not isinstance(entry, dict) or len(entry) != 1:
            raise TypeError("filter_cols entries must be strings or one-key dictionaries.")
        column, method = next(iter(entry.items()))
        if not isinstance(column, str) or not isinstance(method, str):
            raise TypeError("filter_cols dictionary entries must map a string column to a string method.")
        specs.append((column, method))
    return specs


def infer_filter_method(frame: pd.DataFrame, column: str) -> str:
    if column not in frame.columns:
        return "multitext"
    series = frame[column].dropna()
    if series.empty:
        return "dropdown"
    if series.map(lambda value: isinstance(value, bool)).all():
        return "button"
    normalized = [normalize_filter_value(value) for value in series.tolist()]
    values = [value for value in normalized if value is not None]
    if not values:
        return "dropdown"
    unique_count = len(set(values))
    id_like = column == "id" or column.endswith("_id") or column.endswith("id")
    if not id_like and unique_count <= 12:
        return "dropdown"
    return "multitext"


def normalize_filter_specs(
    filter_cols: list[FilterInput] | tuple[FilterInput, ...] | None,
    frame: pd.DataFrame,
) -> list[FilterSpec]:
    specs = []
    seen = set()
    for column, configured_method in normalize_filter_spec_inputs(filter_cols):
        if column in seen:
            continue
        method = configured_method or infer_filter_method(frame, column)
        specs.append(FilterSpec(column=column, method=method, label=labelize(column)))
        seen.add(column)
    return specs


def filter_spec_to_dict(spec: FilterSpec, values: list[str] | None = None) -> dict:
    return {
        "column": spec.column,
        "label": spec.label,
        "method": spec.method,
        "values": values or [],
    }


def format_template(
    template: str,
    row: Mapping[str, Any],
    fallback: str,
    *,
    table_name: str,
    row_index: int,
) -> str:
    if not template:
        return fallback
    values = normalize_template_values(row, table_name=table_name, row_index=row_index)
    try:
        rendered = template.format(**values)
    except (KeyError, ValueError, IndexError):
        return fallback
    return rendered.strip() or fallback


def related_fields_for(inspector: Inspector, source: str) -> list[str]:
    shown = set(inspector.shown_cols or [])
    return [field for field in inspector.highlight_relations.get(source, []) if field in shown]


def build_fields(
    row: Mapping[str, Any],
    shown_cols: list[str],
    *,
    table_name: str,
    row_index: int,
) -> list[Field]:
    fields = []
    for column in shown_cols:
        if column not in row:
            continue
        try:
            value = normalize_display_value(
                row[column],
                table_name=table_name,
                column=column,
                row_index=row_index,
            )
        except TypeError:
            warn_unsupported_column_value(
                table_name=table_name,
                column=column,
                row_index=row_index,
                value=row[column],
                expected=SUPPORTED_COLLECTIONS,
            )
            continue
        if is_empty_field_value(value):
            continue
        fields.append(Field(key=column, label=labelize(column), value=value))
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


def collect_highlights(
    row: Mapping[str, Any],
    inspector: Inspector,
    *,
    table_name: str,
    row_index: int,
) -> list[Highlight]:
    highlights = []
    for column in inspector.highlight_cols or []:
        if column not in row:
            continue
        for value in normalize_highlight_value(
            row[column],
            table_name=table_name,
            column=column,
            row_index=row_index,
        ):
            highlights.append(
                Highlight(
                    source=column,
                    text=value,
                    related_fields=related_fields_for(inspector, column),
                )
            )
    return highlights


def collect_spans(
    row: Mapping[str, Any],
    text: str,
    inspector: Inspector,
    item_id: str,
    *,
    table_name: str,
    row_index: int,
) -> list[Span]:
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

        start_values = normalize_span_cell(
            row[start_col],
            table_name=table_name,
            column=start_col,
            row_index=row_index,
        )
        end_values = normalize_span_cell(
            row[end_col],
            table_name=table_name,
            column=end_col,
            row_index=row_index,
        )
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
        text=document.text,
        title=document.title,
        filter_values=dict(document.filter_values),
    )


def append_item(group_documents: OrderedDict[str, TextDocument], source_document: TextDocument, item: ExtractionItem) -> None:
    if source_document.text_id not in group_documents:
        group_documents[source_document.text_id] = clone_document(source_document)
    group_documents[source_document.text_id].items.append(item)


def normalize_dataset(
    corpus: Corpus,
    inspectors: list[Inspector] | tuple[Inspector, ...],
    *,
    filter_cols: FilterInput | list[FilterInput] | tuple[FilterInput, ...] | None = None,
) -> InspectorDataset:
    if not isinstance(corpus, Corpus):
        raise TypeError("corpus must be a Corpus instance.")
    if not inspectors:
        raise ValueError("At least one Inspector is required.")
    if not all(isinstance(inspector, Inspector) for inspector in inspectors):
        raise TypeError("inspectors must contain only Inspector instances.")

    texts = corpus.texts
    text_id_col = corpus.text_id_col
    text_col = corpus.text_col
    text_title = corpus.text_title
    common_filter_specs = normalize_filter_specs(filter_cols, texts)
    inspector_filter_specs = {
        inspector.tag_name: normalize_filter_specs(inspector.filter_cols or [], inspector.entities)
        for inspector in inspectors
    }

    text_rows = normalize_frame(texts, "texts")

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

        normalized_text_id = normalize_required_scalar(
            text_id_value,
            table_name="texts",
            column=text_id_col,
            row_index=row_index,
        )
        normalized_text = normalize_required_scalar(
            current_text,
            table_name="texts",
            column=text_col,
            row_index=row_index,
        )
        if normalized_text_id is None or normalized_text is None:
            continue

        current_text_id = normalize_id(normalized_text_id)
        title_context = dict(row)
        title_context["text_id"] = current_text_id
        text_lookup[current_text_id] = TextDocument(
            text_id=current_text_id,
            text=str(normalized_text),
            title=format_template(
                text_title,
                title_context,
                f"Text: {current_text_id}",
                table_name="texts",
                row_index=row_index,
            ),
            filter_values=collect_filter_values(
                row,
                common_filter_specs,
                table_name="texts",
                row_index=row_index,
            ),
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
            table_name = f"inspector {inspector.tag_name!r}"
            normalized_text_id = normalize_required_scalar(
                text_id_value,
                table_name=table_name,
                column=inspector.text_id_col,
                row_index=row_index,
            )
            if normalized_text_id is None:
                continue
            current_text_id = normalize_id(normalized_text_id)
            source_document = text_lookup.get(current_text_id)
            if source_document is None:
                continue

            fallback_title = f"{labelize(inspector.tag_name)} {row_index + 1}"
            fallback_item_id = f"{inspector.tag_name}:{current_text_id}:{row_index}"
            item_id = normalize_optional_id(
                row,
                table_name=table_name,
                row_index=row_index,
                fallback=fallback_item_id,
            )
            item = ExtractionItem(
                item_id=item_id,
                text_id=current_text_id,
                tag=inspector.tag_name,
                title=format_template(
                    inspector.entity_title,
                    row,
                    fallback_title,
                    table_name=table_name,
                    row_index=row_index,
                ),
                fields=build_fields(
                    row,
                    inspector.shown_cols or [],
                    table_name=table_name,
                    row_index=row_index,
                ),
                highlights=collect_highlights(
                    row,
                    inspector,
                    table_name=table_name,
                    row_index=row_index,
                ),
                spans=collect_spans(
                    row,
                    source_document.text,
                    inspector,
                    item_id,
                    table_name=table_name,
                    row_index=row_index,
                ),
                filter_values=collect_filter_values(
                    row,
                    inspector_filter_specs[inspector.tag_name],
                    table_name=table_name,
                    row_index=row_index,
                ),
            )
            append_item(all_documents, source_document, item)
            append_item(documents_by_tag[inspector.tag_name], source_document, item)

    groups: OrderedDict[str, GroupData] = OrderedDict()
    common_filter_columns = {spec.column for spec in common_filter_specs}

    def block_for(scope: str, label: str, specs: list[FilterSpec], documents: Mapping[str, TextDocument]) -> dict | None:
        values_by_column = {spec.column: set() for spec in specs if spec.method in {"dropdown", "button"}}
        for document in documents.values():
            if scope == "common":
                source_values = document.filter_values
                for spec in specs:
                    value = source_values.get(spec.column)
                    if spec.column in values_by_column and value not in (None, ""):
                        values_by_column[spec.column].add(value)
                continue
            for item in document.items:
                if item.tag != scope:
                    continue
                for spec in specs:
                    value = item.filter_values.get(spec.column)
                    if spec.column in values_by_column and value not in (None, ""):
                        values_by_column[spec.column].add(value)
        filters = [
            filter_spec_to_dict(spec, sorted(values_by_column.get(spec.column, set())))
            for spec in specs
        ]
        if not filters:
            return None
        return {"scope": scope, "label": label, "filters": filters}

    def blocks_for(group_key: str, documents: Mapping[str, TextDocument]) -> list[dict]:
        blocks = []
        common_block = block_for("common", "Common", common_filter_specs, documents)
        if common_block:
            blocks.append(common_block)
        active_inspectors = inspectors if group_key == "all" else [inspector for inspector in inspectors if inspector.tag_name == group_key]
        for inspector in active_inspectors:
            specs = [
                spec
                for spec in inspector_filter_specs[inspector.tag_name]
                if spec.column not in common_filter_columns
            ]
            inspector_block = block_for(inspector.tag_name, labelize(inspector.tag_name), specs, documents)
            if inspector_block:
                blocks.append(inspector_block)
        return blocks

    groups["all"] = GroupData(
        key="all",
        label="All",
        text_ids=list(all_documents.keys()),
        texts=dict(all_documents),
        filter_blocks=blocks_for("all", all_documents),
    )
    for inspector in inspectors:
        documents = documents_by_tag[inspector.tag_name]
        groups[inspector.tag_name] = GroupData(
            key=inspector.tag_name,
            label=labelize(inspector.tag_name),
            text_ids=list(documents.keys()),
            texts=dict(documents),
            filter_blocks=blocks_for(inspector.tag_name, documents),
        )

    return InspectorDataset(groups=dict(groups))
