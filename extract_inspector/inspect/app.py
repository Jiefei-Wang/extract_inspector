from __future__ import annotations

import json
import webbrowser
from threading import Timer
from typing import Any

from flask import Flask, Response, jsonify, request

from extract_inspector.inspect.matching import build_highlights
from extract_inspector.inspect.models import Corpus, ExtractionItem, Field, Highlight, Inspector, InspectorDataset, Span, TextDocument
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
    return {"key": field.key, "label": field.label, "value": clean_json_value(field.value)}


def highlight_to_dict(highlight: Highlight) -> dict:
    return {
        "source": highlight.source,
        "text": highlight.text,
        "related_fields": list(highlight.related_fields),
    }


def span_to_dict(span: Span) -> dict:
    return {
        "start": span.start,
        "end": span.end,
        "text": span.text,
        "source": span.source,
        "related_fields": list(span.related_fields),
    }


def item_to_dict(item: ExtractionItem) -> dict:
    return {
        "item_id": item.item_id,
        "tag": item.tag,
        "title": item.title,
        "highlights": [highlight_to_dict(highlight) for highlight in item.highlights],
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
        "title": document.title,
        "text": document.text,
        "highlighted_html": highlighted_html,
        "items": item_dicts,
    }


def parse_filters(filters_json: str | None) -> dict[str, dict[str, str]]:
    if not filters_json:
        return {}
    try:
        parsed = json.loads(filters_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    filters = {}
    for scope, values in parsed.items():
        if not isinstance(scope, str) or not isinstance(values, dict):
            continue
        scope_filters = {}
        for column, value in values.items():
            if isinstance(column, str) and isinstance(value, str) and value and value != "all":
                scope_filters[column] = value
        if scope_filters:
            filters[scope] = scope_filters
    return filters


def split_multitext(value: str) -> set[str]:
    return {entry.strip() for entry in value.split(",") if entry.strip()}


def matches_filter(value: str | None, query: str, method: str) -> bool:
    if value is None:
        return False
    if method == "textbox":
        return query.casefold() in value.casefold()
    if method == "multitext":
        return value in split_multitext(query)
    return value == query


def active_filter_specs(group_data, scope: str) -> dict[str, str]:
    for block in group_data.filter_blocks:
        if block["scope"] != scope:
            continue
        return {filter_spec["column"]: filter_spec["method"] for filter_spec in block["filters"]}
    return {}


def matches_filter_scope(values: dict[str, str], filters: dict[str, str], methods: dict[str, str]) -> bool:
    return all(matches_filter(values.get(column), query, methods.get(column, "dropdown")) for column, query in filters.items())


def filter_document_items(group_data, document: TextDocument, filters_by_scope: dict[str, dict[str, str]]) -> list[ExtractionItem]:
    common_filters = filters_by_scope.get("common", {})
    if common_filters and not matches_filter_scope(
        document.filter_values,
        common_filters,
        active_filter_specs(group_data, "common"),
    ):
        return []

    if not filters_by_scope:
        return list(document.items)
    filtered_items = []
    for item in document.items:
        item_filters = filters_by_scope.get(item.tag, {})
        if item_filters and not matches_filter_scope(
            item.filter_values,
            item_filters,
            active_filter_specs(group_data, item.tag),
        ):
            continue
        filtered_items.append(item)
    return filtered_items


def filter_texts_page(
    dataset: InspectorDataset,
    group_key: str,
    filters_by_scope: dict[str, dict[str, str]],
    offset: int,
    limit: int,
) -> tuple[list[dict], int]:
    group_data = dataset.groups[group_key]
    page = []
    total = 0

    for current_text_id in group_data.text_ids:
        document = group_data.texts[current_text_id]

        items = filter_document_items(group_data, document, filters_by_scope)
        if not items:
            continue

        if total >= offset and len(page) < limit:
            serialized = document_to_dict(document, items)
            if serialized is not None:
                page.append(serialized)
        total += 1

    return page, total


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
                "filter_blocks": group_data.filter_blocks,
            }
            for group_key, group_data in dataset.groups.items()
        ]
        return jsonify({"groups": groups})

    @app.get("/api/texts")
    def api_texts():
        group_key = request.args.get("group")
        if group_key not in dataset.groups:
            return jsonify({"error": "Unknown inspector tab."}), 400

        offset = parse_int(request.args.get("offset"), 0, 0)
        limit = parse_int(request.args.get("limit"), DEFAULT_PAGE_LIMIT, 1, MAX_PAGE_LIMIT)
        filters_by_scope = parse_filters(request.args.get("filters"))

        page, total = filter_texts_page(
            dataset,
            group_key,
            filters_by_scope,
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


def inspector_web(
    corpus: Corpus,
    *inspectors: Inspector,
    filter_cols=None,
    host: str = "127.0.0.1",
    port: int = 5001,
    debug: bool = False,
    open_browser: bool = True,
):
    dataset = normalize_dataset(
        corpus,
        inspectors,
        filter_cols=filter_cols,
    )
    app = create_app(dataset)
    url = f"http://{host}:{port}"
    if open_browser:
        Timer(0.75, lambda: webbrowser.open(url)).start()
    return app.run(host=host, port=port, debug=debug)
