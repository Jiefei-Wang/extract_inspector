from extract_inspector.inspect.matching import build_highlights


def test_build_highlights_matches_multiple_highlight_values_for_one_item():
    html, matched = build_highlights(
        "Alpha beta gamma beta.",
        [
            {
                "item_id": "item-1",
                "highlights": [
                    {"source": "evidence", "text": "Alpha", "related_fields": ["value"]},
                    {"source": "evidence", "text": "gamma", "related_fields": ["value"]},
                ],
            }
        ],
    )

    assert matched == {"item-1"}
    assert html.count('class="text-highlight"') == 2
    assert "Alpha" in html
    assert "gamma" in html
    assert 'data-related-fields="item-1::value"' in html


def test_build_highlights_links_shared_span_to_multiple_items():
    html, matched = build_highlights(
        "Shared evidence appears here.",
        [
            {"item_id": "item-1", "highlights": [{"source": "evidence", "text": "Shared evidence"}]},
            {"item_id": "item-2", "highlights": [{"source": "evidence", "text": "Shared evidence"}]},
        ],
    )

    assert matched == {"item-1", "item-2"}
    assert 'data-item-ids="item-1,item-2"' in html


def test_build_highlights_uses_offset_spans():
    html, matched = build_highlights(
        "Alpha beta gamma.",
        [
            {
                "item_id": "item-1",
                "highlights": [],
                "spans": [{"start": 6, "end": 10, "text": "beta", "related_fields": ["value"]}],
            }
        ],
    )

    assert matched == {"item-1"}
    assert (
        '<span class="text-highlight" data-item-ids="item-1" '
        'data-related-fields="item-1::value">beta</span>'
    ) in html


def test_build_highlights_uses_spans_and_highlights_together():
    html, matched = build_highlights(
        "Alpha beta gamma.",
        [
            {
                "item_id": "item-1",
                "highlights": [{"source": "evidence", "text": "gamma"}],
                "spans": [{"start": 0, "end": 5}],
            }
        ],
    )

    assert matched == {"item-1"}
    assert html.count('class="text-highlight"') == 2


def test_build_highlights_drops_unmatched_string_highlights():
    html, matched = build_highlights(
        "Alpha beta gamma.",
        [{"item_id": "item-1", "highlights": [{"source": "evidence", "text": "missing"}]}],
    )

    assert matched == set()
    assert 'class="text-highlight"' not in html
