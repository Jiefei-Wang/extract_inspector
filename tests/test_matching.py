from extract_inspector.inspect.matching import build_highlights


def test_build_highlights_matches_multiple_evidence_values_for_one_item():
    html, matched = build_highlights(
        "Alpha beta gamma beta.",
        [{"item_id": "item-1", "evidence": ["Alpha", "gamma"]}],
    )

    assert matched == {"item-1"}
    assert html.count('class="text-highlight"') == 2
    assert "Alpha" in html
    assert "gamma" in html


def test_build_highlights_links_shared_span_to_multiple_items():
    html, matched = build_highlights(
        "Shared evidence appears here.",
        [
            {"item_id": "item-1", "evidence": ["Shared evidence"]},
            {"item_id": "item-2", "evidence": ["Shared evidence"]},
        ],
    )

    assert matched == {"item-1", "item-2"}
    assert 'data-item-ids="item-1,item-2"' in html


def test_build_highlights_uses_offset_spans():
    html, matched = build_highlights(
        "Alpha beta gamma.",
        [{"item_id": "item-1", "evidence": [], "spans": [{"start": 6, "end": 10, "text": "beta"}]}],
    )

    assert matched == {"item-1"}
    assert '<span class="text-highlight" data-item-ids="item-1">beta</span>' in html


def test_build_highlights_uses_spans_and_evidence_together():
    html, matched = build_highlights(
        "Alpha beta gamma.",
        [{"item_id": "item-1", "evidence": ["gamma"], "spans": [{"start": 0, "end": 5}]}],
    )

    assert matched == {"item-1"}
    assert html.count('class="text-highlight"') == 2


def test_build_highlights_links_shared_offset_span_to_multiple_items():
    html, matched = build_highlights(
        "Alpha beta gamma.",
        [
            {"item_id": "item-1", "evidence": [], "spans": [{"start": 6, "end": 10}]},
            {"item_id": "item-2", "evidence": [], "spans": [{"start": 6, "end": 10}]},
        ],
    )

    assert matched == {"item-1", "item-2"}
    assert 'data-item-ids="item-1,item-2"' in html
