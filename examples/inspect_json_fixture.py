from pathlib import Path

import pandas as pd

from extract_inspector.inspect import inspect_extractions


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


texts = pd.read_json(FIXTURES / "texts.json")
entities = pd.read_json(FIXTURES / "entities.json")
actions = pd.read_json(FIXTURES / "actions.json")


inspect_extractions(
    texts,
    {"entities": entities, "actions": actions},
    evidence_col=["evidence", "alternate_evidence"],
    span_start_col="span_start",
    span_end_col="span_end",
    filter_categorical_cols=["entity_type", "confidence"],
    extraction_id="extraction_id",
)
