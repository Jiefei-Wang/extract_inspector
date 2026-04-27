from pathlib import Path

import pandas as pd

from extract_inspector.inspect.app import create_app
from extract_inspector.inspect.normalize import normalize_dataset
from extract_inspector.inspect.ui import INDEX_HTML


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_fixture_dataset():
    texts = pd.read_json(FIXTURES / "texts.json")
    entities = pd.read_json(FIXTURES / "entities.json")
    actions = pd.read_json(FIXTURES / "actions.json")
    return normalize_dataset(
        texts,
        {"entities": entities, "actions": actions},
        highlight_col=["evidence", "alternate_evidence"],
        span_start_col="span_start",
        span_end_col="span_end",
        filter_categorical_cols=["entity_type", "confidence"],
        extraction_id="extraction_id",
    )


def test_json_fixtures_load_into_normalized_dataset():
    dataset = load_fixture_dataset()

    assert list(dataset.groups) == ["entities", "actions"]
    assert dataset.groups["entities"].texts["text-001"].items[0].highlights == [
        "chest pain after exercise",
        "Symptom severity was moderate",
    ]
    assert dataset.groups["entities"].texts["text-001"].items[0].highlights_by_column == {
        "evidence": ["chest pain after exercise"],
        "alternate_evidence": ["Symptom severity was moderate"],
    }
    assert [(span.start, span.end, span.text) for span in dataset.groups["entities"].texts["text-001"].items[2].spans] == [
        (19, 36, "customer reported")
    ]
    assert [(span.start, span.end, span.text) for span in dataset.groups["entities"].texts["text-002"].items[1].spans] == [
        (128, 146, "waiting 15 minutes")
    ]
    assert dataset.groups["entities"].texts["text-003"].items[-1].highlights == ["database outage"]


def test_json_fixtures_render_through_flask_api():
    app = create_app(load_fixture_dataset())
    client = app.test_client()

    groups = client.get("/api/groups").json
    assert groups["groups"][0]["key"] == "entities"
    assert groups["groups"][0]["filters"] == [
        {
            "column": "entity_type",
            "label": "Entity Type",
            "values": [
                "context",
                "failure_reason",
                "measurement",
                "problem",
                "remediation",
                "resolution",
                "symptom",
                "unmatched",
            ],
        },
        {"column": "confidence", "label": "Confidence", "values": ["high", "low", "medium"]},
    ]

    response = client.get("/api/texts?group=entities")
    assert response.status_code == 200
    first_text = response.json["texts"][0]
    assert first_text["text_id"] == "text-001"
    assert first_text["highlighted_html"].count('class="text-highlight"') >= 3
    assert first_text["items"][0]["highlights_by_column"] == {
        "evidence": ["chest pain after exercise"],
        "alternate_evidence": ["Symptom severity was moderate"],
    }
    assert "evidence" not in first_text["items"][0]
    assert "evidence_by_column" not in first_text["items"][0]
    assert first_text["items"][2]["spans"] == [
        {"start": 19, "end": 36, "text": "customer reported"}
    ]

    unmatched_text = client.get("/api/texts?group=entities&text_ids=text-003").json["texts"][0]
    unmatched_item = [item for item in unmatched_text["items"] if item["item_id"] == "entity-008"][0]
    assert unmatched_item["has_match"] is False


def test_json_fixture_categorical_filtering():
    app = create_app(load_fixture_dataset())
    client = app.test_client()

    response = client.get('/api/texts?group=entities&filters={"confidence":"medium"}')
    assert response.status_code == 200
    items = [item for text in response.json["texts"] for item in text["items"]]
    assert {item["filter_values"]["confidence"] for item in items} == {"medium"}
    assert {item["item_id"] for item in items} == {"entity-003", "entity-004"}


def test_json_fixture_categorical_filters_use_and_semantics():
    app = create_app(load_fixture_dataset())
    client = app.test_client()

    response = client.get('/api/texts?group=entities&filters={"confidence":"high","entity_type":"resolution"}')
    assert response.status_code == 200
    items = [item for text in response.json["texts"] for item in text["items"]]
    assert [item["item_id"] for item in items] == ["entity-007"]


def test_ui_renders_single_highlight_field_row_with_stacked_lines():
    assert '<div class="field-label">Highlight</div>' in INDEX_HTML
    assert "highlightLines.map" in INDEX_HTML
    assert "Evidence (" not in INDEX_HTML
    assert '<div class="field-label">Span</div>' not in INDEX_HTML
