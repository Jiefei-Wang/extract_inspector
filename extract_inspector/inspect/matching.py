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


def build_highlights(text: str, items: list[dict]) -> tuple[str, set[str]]:
    interval_map: OrderedDict[tuple[int, int], set[str]] = OrderedDict()

    for item in items:
        for span in item.get("spans", []):
            start = span.get("start")
            end = span.get("end")
            if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text):
                interval_map.setdefault((start, end), set()).add(item["item_id"])
        for highlight in item.get("highlights", []):
            for interval in find_matches(text, highlight):
                interval_map.setdefault(interval, set()).add(item["item_id"])

    intervals = [
        {"start": start, "end": end, "item_ids": sorted(item_ids)}
        for (start, end), item_ids in interval_map.items()
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
        rendered_parts.append(
            "<span class=\"text-highlight\" "
            f"data-item-ids=\"{html.escape(item_ids_attr)}\">{matched_text}</span>"
        )
        matched_item_ids.update(interval["item_ids"])
        cursor = end

    rendered_parts.append(html.escape(text[cursor:]))
    return "".join(rendered_parts), matched_item_ids
