from pathlib import Path

import pandas as pd

from extract_inspector.inspect import Corpus, Inspector, inspector_web


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


texts = pd.read_json(FIXTURES / "clinical_texts.json")
patient_demo = pd.read_json(FIXTURES / "patient_demo.json")
lab_values = pd.read_json(FIXTURES / "lab_values.json")
diagnoses = pd.read_json(FIXTURES / "diagnoses.json")


inspector_web(
    Corpus(texts),
    Inspector(
        "patient_demo",
        patient_demo,
        entity_title="Patient: {extraction_id}",
        shown_cols=["field", "value", "confidence"],
        highlight_cols=["evidence"],
        highlight_relations={"evidence": "value"},
        filter_cols=[{"field": "dropdown"}, {"confidence": "button"}],
    ),
    Inspector(
        "lab_values",
        lab_values,
        entity_title="Lab: {test_name}",
        shown_cols=["test_name", "value", "unit", "flag"],
        highlight_cols=["evidence"],
        highlight_relations={"evidence": ["test_name", "value"]},
        filter_cols=[{"test_name": "dropdown"}, {"flag": "button"}],
    ),
    Inspector(
        "diagnoses",
        diagnoses,
        entity_title="Diagnosis: {diagnosis}",
        shown_cols=["diagnosis", "status", "confidence"],
        highlight_cols=["evidence"],
        highlight_relations={"evidence": "diagnosis"},
        filter_cols=[{"status": "dropdown"}, {"confidence": "button"}],
    ),
    filter_cols=[{"text_id": "multitext"}, {"patient_id": "multitext"}],
)
