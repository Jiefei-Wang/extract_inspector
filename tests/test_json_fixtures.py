from pathlib import Path

import pandas as pd

from extract_inspector.inspect import Inspector
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
        [
            Inspector(
                "entities",
                entities,
                entity_title="Entity: {extraction_id}",
                shown_cols=["value", "entity_type", "confidence"],
                highlight_cols=["evidence", "alternate_evidence"],
                highlight_span_start_cols=["span_start"],
                highlight_span_end_cols=["span_end"],
                highlight_relations={
                    "evidence": "value",
                    "alternate_evidence": "value",
                    "span_start:span_end": "value",
                },
                filter_cols=["entity_type", "confidence"],
            ),
            Inspector(
                "actions",
                actions,
                entity_title="Action: {extraction_id}",
                shown_cols=["action", "owner", "confidence"],
                highlight_cols=["evidence"],
                highlight_relations={"evidence": "action"},
                filter_cols=["owner", "confidence"],
            ),
        ],
    )


def test_json_fixtures_load_into_normalized_dataset():
    dataset = load_fixture_dataset()

    assert list(dataset.groups) == ["all", "entities", "actions"]
    assert [item.tag for item in dataset.groups["all"].texts["text-001"].items] == [
        "entities",
        "entities",
        "entities",
        "actions",
        "actions",
    ]
    first_entity = dataset.groups["entities"].texts["text-001"].items[0]
    assert first_entity.title == "Entity: entity-001"
    assert [(highlight.source, highlight.text, highlight.related_fields) for highlight in first_entity.highlights] == [
        ("evidence", "chest pain after exercise", ["value"]),
        ("alternate_evidence", "Symptom severity was moderate", ["value"]),
    ]
    assert [(span.start, span.end, span.text, span.related_fields) for span in dataset.groups["entities"].texts["text-001"].items[2].spans] == [
        (19, 36, "customer reported", ["value"])
    ]


def test_json_fixtures_render_through_flask_api():
    app = create_app(load_fixture_dataset())
    client = app.test_client()

    groups = client.get("/api/groups").json
    assert [group["key"] for group in groups["groups"]] == ["all", "entities", "actions"]
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
        {"column": "owner", "label": "Owner", "values": ["data team", "subject", "support"]},
    ]

    response = client.get("/api/texts?group=all")
    assert response.status_code == 200
    first_text = response.json["texts"][0]
    assert first_text["text_id"] == "text-001"
    assert first_text["title"] == "Text: text-001"
    assert first_text["highlighted_html"].count('class="text-highlight"') >= 5
    assert 'data-related-fields="entity-001::value"' in first_text["highlighted_html"]
    assert first_text["items"][0]["title"] == "Entity: entity-001"
    assert first_text["items"][0]["fields"][0] == {"key": "value", "label": "Value", "value": "chest pain"}
    assert first_text["items"][0]["highlights"][0] == {
        "source": "evidence",
        "text": "chest pain after exercise",
        "related_fields": ["value"],
    }

    unmatched_text = client.get("/api/texts?group=entities&text_ids=text-003").json["texts"][0]
    unmatched_item = [item for item in unmatched_text["items"] if item["item_id"] == "entity-008"][0]
    assert unmatched_item["has_match"] is False


def test_highlight_columns_display_only_when_in_shown_cols():
    texts = pd.read_json(FIXTURES / "texts.json")
    entities = pd.read_json(FIXTURES / "entities.json")
    dataset = normalize_dataset(
        texts,
        [
            Inspector(
                "entities",
                entities,
                shown_cols=["value", "evidence"],
                highlight_cols=["evidence"],
                highlight_relations={"evidence": "value"},
            )
        ],
    )
    client = create_app(dataset).test_client()

    first_item = client.get("/api/texts?group=entities").json["texts"][0]["items"][0]

    assert [field["key"] for field in first_item["fields"]] == ["value", "evidence"]
    assert first_item["highlights"] == [
        {
            "source": "evidence",
            "text": "chest pain after exercise",
            "related_fields": ["value"],
        }
    ]


def test_json_fixture_filters_apply_to_all_and_specific_tabs():
    app = create_app(load_fixture_dataset())
    client = app.test_client()

    response = client.get('/api/texts?group=entities&filters={"confidence":"medium"}')
    assert response.status_code == 200
    items = [item for text in response.json["texts"] for item in text["items"]]
    assert {item["filter_values"]["confidence"] for item in items} == {"medium"}
    assert {item["item_id"] for item in items} == {"entity-003", "entity-004"}

    all_response = client.get('/api/texts?group=all&filters={"owner":"support"}')
    assert all_response.status_code == 200
    all_items = [item for text in all_response.json["texts"] for item in text["items"]]
    assert [item["item_id"] for item in all_items] == ["action-003"]


def test_ui_contains_relation_hover_hooks():
    assert "hoveredFieldKeys" in INDEX_HTML
    assert "dataset.relatedFields" in INDEX_HTML
    assert "related-active" in INDEX_HTML
    assert "highlight-lines" not in INDEX_HTML
    assert '<div class="field-label">Highlight</div>' not in INDEX_HTML
