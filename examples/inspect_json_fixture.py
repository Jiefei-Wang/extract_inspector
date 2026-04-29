from pathlib import Path

import pandas as pd

from extract_inspector.inspect import Inspector, inspector_web


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


texts = pd.read_json(FIXTURES / "texts.json")
entities = pd.read_json(FIXTURES / "entities.json")
actions = pd.read_json(FIXTURES / "actions.json")


inspector_web(
    texts,
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
)
