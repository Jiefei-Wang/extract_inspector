from pathlib import Path

import pandas as pd

from extract_inspector.inspect.app import create_app
from extract_inspector.inspect.normalize import normalize_dataset


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_fixture_dataset():
    texts = pd.read_json(FIXTURES / "texts.json")
    entities = pd.read_json(FIXTURES / "entities.json")
    actions = pd.read_json(FIXTURES / "actions.json")
    return normalize_dataset(
        texts,
        {"entities": entities, "actions": actions},
        evidence_col=["evidence", "alternate_evidence"],
        span_start_col="span_start",
        span_end_col="span_end",
        extraction_id="extraction_id",
    )


def test_json_fixtures_load_into_normalized_dataset():
    dataset = load_fixture_dataset()

    assert list(dataset.groups) == ["entities", "actions"]
    assert dataset.groups["entities"].texts["text-001"].items[0].evidence == [
        "chest pain after exercise",
        "Symptom severity was moderate",
    ]
    assert dataset.groups["entities"].texts["text-001"].items[0].evidence_by_column == {
        "evidence": ["chest pain after exercise"],
        "alternate_evidence": ["Symptom severity was moderate"],
    }
    assert [(span.start, span.end, span.text) for span in dataset.groups["entities"].texts["text-001"].items[2].spans] == [
        (19, 36, "customer reported")
    ]
    assert [(span.start, span.end, span.text) for span in dataset.groups["entities"].texts["text-002"].items[1].spans] == [
        (128, 146, "waiting 15 minutes")
    ]
    assert dataset.groups["entities"].texts["text-003"].items[-1].evidence == ["database outage"]


def test_json_fixtures_render_through_flask_api():
    app = create_app(load_fixture_dataset())
    client = app.test_client()

    groups = client.get("/api/groups").json
    assert groups["groups"][0]["key"] == "entities"

    response = client.get("/api/texts?group=entities")
    assert response.status_code == 200
    first_text = response.json["texts"][0]
    assert first_text["text_id"] == "text-001"
    assert first_text["highlighted_html"].count('class="text-highlight"') >= 3
    assert first_text["items"][0]["evidence_by_column"] == {
        "evidence": ["chest pain after exercise"],
        "alternate_evidence": ["Symptom severity was moderate"],
    }
    assert first_text["items"][2]["spans"] == [
        {"start": 19, "end": 36, "text": "customer reported"}
    ]

    unmatched_text = client.get("/api/texts?group=entities&text_ids=text-003").json["texts"][0]
    unmatched_item = [item for item in unmatched_text["items"] if item["item_id"] == "entity-008"][0]
    assert unmatched_item["has_match"] is False
