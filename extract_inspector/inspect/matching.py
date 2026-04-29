from __future__ import annotations

import html
from collections import OrderedDict


def find_matches(text: str, needle: str) -> list[tuple[int, int]]:
    if not text or not needle:
        return []

    matches = []
    start = 0
    while True:
        index = text.find(needle, start)
        if index == -1:
            break
        matches.append((index, index + len(needle)))
        start = index + len(needle)
    return matches


def relation_tokens(item_id: str, related_fields: list[str] | None) -> list[str]:
    return [f"{item_id}::{field}" for field in (related_fields or [])]


def add_interval(
    interval_map: OrderedDict[tuple[int, int], dict[str, set[str]]],
    start: int,
    end: int,
    item_id: str,
    related_fields: list[str] | None,
) -> None:
    entry = interval_map.setdefault((start, end), {"item_ids": set(), "related_fields": set()})
    entry["item_ids"].add(item_id)
    entry["related_fields"].update(relation_tokens(item_id, related_fields))


def build_highlights(text: str, items: list[dict]) -> tuple[str, set[str]]:
    interval_map: OrderedDict[tuple[int, int], dict[str, set[str]]] = OrderedDict()

    for item in items:
        item_id = item["item_id"]
        for span in item.get("spans", []):
            start = span.get("start")
            end = span.get("end")
            if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text):
                add_interval(interval_map, start, end, item_id, span.get("related_fields") or [])
        for highlight in item.get("highlights", []):
            highlight_text = highlight.get("text")
            if not isinstance(highlight_text, str):
                continue
            for start, end in find_matches(text, highlight_text):
                add_interval(interval_map, start, end, item_id, highlight.get("related_fields") or [])

    intervals = [
        {
            "start": start,
            "end": end,
            "item_ids": sorted(data["item_ids"]),
            "related_fields": sorted(data["related_fields"]),
        }
        for (start, end), data in interval_map.items()
    ]
    intervals.sort(key=lambda entry: (entry["start"], -(entry["end"] - entry["start"])))

    rendered_parts = []
    matched_item_ids: set[str] = set()
    cursor = 0

    for interval in intervals:
        start = interval["start"]
        end = interval["end"]
        if start < cursor:
            continue

        rendered_parts.append(html.escape(text[cursor:start]))
        matched_text = html.escape(text[start:end])
        item_ids_attr = ",".join(interval["item_ids"])
        related_fields_attr = ",".join(interval["related_fields"])
        rendered_parts.append(
            "<span class=\"text-highlight\" "
            f"data-item-ids=\"{html.escape(item_ids_attr)}\" "
            f"data-related-fields=\"{html.escape(related_fields_attr)}\">{matched_text}</span>"
        )
        matched_item_ids.update(interval["item_ids"])
        cursor = end

    rendered_parts.append(html.escape(text[cursor:]))
    return "".join(rendered_parts), matched_item_ids
