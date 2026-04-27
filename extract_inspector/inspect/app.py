from __future__ import annotations

import json
import webbrowser
from threading import Timer
from typing import Any

import pandas as pd
from flask import Flask, Response, jsonify, request

from extract_inspector.inspect.matching import build_highlights
from extract_inspector.inspect.models import ExtractionItem, Field, InspectorDataset, Span, TextDocument
from extract_inspector.inspect.normalize import normalize_dataset
from extract_inspector.inspect.ui import INDEX_HTML

DEFAULT_PAGE_LIMIT = 1000
MAX_PAGE_LIMIT = 1000


def clean_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): clean_json_value(entry) for key, entry in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_json_value(entry) for entry in value]
    return str(value)


def parse_ids(ids: str | None) -> set[str] | None:
    if not ids:
        return None
    parsed = {entry.strip() for entry in ids.split(",") if entry.strip()}
    return parsed or None


def parse_int(value: str | None, default: int, minimum: int, maximum: int | None = None) -> int:
    try:
        parsed = int(value) if value is not None else default
    except ValueError:
        parsed = default
    parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def field_to_dict(field: Field) -> dict:
    return {"label": field.label, "value": clean_json_value(field.value)}


def span_to_dict(span: Span) -> dict:
    return {"start": span.start, "end": span.end, "text": span.text}


def item_to_dict(item: ExtractionItem) -> dict:
    return {
        "item_id": item.item_id,
        "summary": item.summary,
        "group": item.group,
        "highlights": item.highlights,
        "highlights_by_column": item.highlights_by_column,
        "spans": [span_to_dict(span) for span in item.spans],
        "filter_values": item.filter_values,
        "fields": [field_to_dict(field) for field in item.fields],
        "has_match": item.has_match,
    }


def document_to_dict(document: TextDocument, items: list[ExtractionItem]) -> dict | None:
    if not items:
        return None

    item_dicts = [item_to_dict(item) for item in items]
    highlighted_html, matched_item_ids = build_highlights(document.text, item_dicts)
    for item_dict in item_dicts:
        item_dict["has_match"] = item_dict["item_id"] in matched_item_ids

    return {
        "text_id": document.text_id,
        "subject_id": document.subject_id,
        "text": document.text,
        "highlighted_html": highlighted_html,
        "items": item_dicts,
    }


def parse_categorical_filters(filters_json: str | None) -> dict[str, str]:
    if not filters_json:
        return {}
    try:
        parsed = json.loads(filters_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    filters = {}
    for key, value in parsed.items():
        if isinstance(key, str) and isinstance(value, str) and value and value != "all":
            filters[key] = value
    return filters


def filter_document_items(document: TextDocument, categorical_filters: dict[str, str]) -> list[ExtractionItem]:
    if not categorical_filters:
        return list(document.items)
    return [
        item
        for item in document.items
        if all(item.filter_values.get(column) == value for column, value in categorical_filters.items())
    ]


def filter_texts_page(
    dataset: InspectorDataset,
    group_key: str,
    categorical_filters: dict[str, str],
    text_ids: set[str] | None,
    subject_ids: set[str] | None,
    offset: int,
    limit: int,
) -> tuple[list[dict], int]:
    group_data = dataset.groups[group_key]
    page = []
    total = 0

    for current_text_id in group_data.text_ids:
        if text_ids is not None and current_text_id not in text_ids:
            continue

        document = group_data.texts[current_text_id]
        if subject_ids is not None and document.subject_id not in subject_ids:
            continue

        items = filter_document_items(document, categorical_filters)
        if not items:
            continue

        if total >= offset and len(page) < limit:
            serialized = document_to_dict(document, items)
            if serialized is not None:
                page.append(serialized)
        total += 1

    return page, total


def group_filter_definitions(dataset: InspectorDataset, group_key: str) -> list[dict]:
    values_by_column = {column: set() for column in dataset.filter_categorical_cols}
    group = dataset.groups[group_key]
    for document in group.texts.values():
        for item in document.items:
            for column in dataset.filter_categorical_cols:
                value = item.filter_values.get(column)
                if value not in (None, ""):
                    values_by_column[column].add(value)

    return [
        {
            "column": column,
            "label": column.replace("_", " ").title(),
            "values": sorted(values),
        }
        for column, values in values_by_column.items()
        if values
    ]


def create_app(dataset: InspectorDataset) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index() -> Response:
        return Response(INDEX_HTML, mimetype="text/html")

    @app.get("/api/groups")
    def api_groups():
        groups = [
            {
                "key": group_key,
                "label": group_data.label,
                "total": len(group_data.text_ids),
                "filters": group_filter_definitions(dataset, group_key),
            }
            for group_key, group_data in dataset.groups.items()
        ]
        return jsonify(
            {
                "groups": groups,
                "has_subject_id": dataset.has_subject_id,
            }
        )

    @app.get("/api/texts")
    def api_texts():
        group_key = request.args.get("group")
        if group_key not in dataset.groups:
            return jsonify({"error": "Unknown extraction group."}), 400

        offset = parse_int(request.args.get("offset"), 0, 0)
        limit = parse_int(request.args.get("limit"), DEFAULT_PAGE_LIMIT, 1, MAX_PAGE_LIMIT)
        text_ids = parse_ids(request.args.get("text_ids"))
        subject_ids = parse_ids(request.args.get("subject_ids"))
        categorical_filters = parse_categorical_filters(request.args.get("filters"))

        page, total = filter_texts_page(
            dataset,
            group_key,
            categorical_filters,
            text_ids,
            subject_ids,
            offset,
            limit,
        )

        return jsonify(
            {
                "texts": page,
                "total": total,
                "offset": offset,
                "limit": limit,
                "has_more": offset + len(page) < total,
            }
        )

    return app


def inspect_extractions(
    texts: pd.DataFrame,
    extractions: pd.DataFrame | dict[str, pd.DataFrame],
    *,
    text_id: str = "text_id",
    text_col: str = "text",
    subject_id: str | None = "subject_id",
    extraction_id: str | None = None,
    extraction_group: str | None = None,
    highlight_col: str | list[str] | None = "evidence",
    span_start_col: str | None = None,
    span_end_col: str | None = None,
    filter_categorical_cols: str | list[str] | None = None,
    exclude_fields: list[str] | None = None,
    field_labels: dict[str, str] | None = None,
    host: str = "127.0.0.1",
    port: int = 5001,
    debug: bool = False,
    open_browser: bool = True,
):
    dataset = normalize_dataset(
        texts,
        extractions,
        text_id=text_id,
        text_col=text_col,
        subject_id=subject_id,
        extraction_id=extraction_id,
        extraction_group=extraction_group,
        highlight_col=highlight_col,
        span_start_col=span_start_col,
        span_end_col=span_end_col,
        filter_categorical_cols=filter_categorical_cols,
        exclude_fields=exclude_fields,
        field_labels=field_labels,
    )
    app = create_app(dataset)
    url = f"http://{host}:{port}"
    if open_browser:
        Timer(0.75, lambda: webbrowser.open(url)).start()
    return app.run(host=host, port=port, debug=debug)
