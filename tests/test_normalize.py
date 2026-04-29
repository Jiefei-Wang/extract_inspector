import numpy as np
import pandas as pd
import pytest

from extract_inspector.inspect import Inspector
from extract_inspector.inspect.normalize import normalize_dataset


def texts_df():
    return pd.DataFrame(
        [
            {"text_id": "t1", "subject_id": "s1", "text": "Alpha beta gamma delta."},
            {"text_id": "t2", "subject_id": "s2", "text": "No evidence here."},
        ]
    )


def test_inspector_requires_valid_dataframe_and_text_id_column():
    with pytest.raises(TypeError, match="entities must be a pandas DataFrame"):
        Inspector("entities", entities=[])

    with pytest.raises(ValueError, match="missing text id column"):
        Inspector("entities", pd.DataFrame([{"id": "t1"}]), text_id_col="text_id")


def test_inspector_normalizes_column_options_and_relations():
    inspector = Inspector(
        "entities",
        pd.DataFrame([{"text_id": "t1"}]),
        shown_cols="value",
        highlight_cols="evidence",
        highlight_span_start_cols="start",
        highlight_span_end_cols="end",
        highlight_relations={"evidence": "value", "start:end": ["value"]},
        filter_cols="confidence",
    )

    assert inspector.shown_cols == ["value"]
    assert inspector.highlight_cols == ["evidence"]
    assert inspector.highlight_span_start_cols == ["start"]
    assert inspector.highlight_span_end_cols == ["end"]
    assert inspector.highlight_relations == {"evidence": ["value"], "start:end": ["value"]}
    assert inspector.filter_cols == ["confidence"]


def test_inspector_rejects_mismatched_span_column_pairs():
    with pytest.raises(ValueError, match="same length"):
        Inspector(
            "entities",
            pd.DataFrame([{"text_id": "t1"}]),
            highlight_span_start_cols=["start"],
            highlight_span_end_cols=["end", "end2"],
        )


def test_dataset_creates_all_tab_and_inspector_tabs():
    entities = pd.DataFrame([{"extraction_id": "e1", "text_id": "t1", "value": "Alpha", "evidence": "Alpha"}])
    actions = pd.DataFrame([{"extraction_id": "a1", "text_id": "t1", "action": "review", "evidence": "beta"}])

    dataset = normalize_dataset(
        texts_df(),
        [
            Inspector("entities", entities, shown_cols=["value"], highlight_cols=["evidence"]),
            Inspector("actions", actions, shown_cols=["action"], highlight_cols=["evidence"]),
        ],
    )

    assert list(dataset.groups) == ["all", "entities", "actions"]
    assert [item.item_id for item in dataset.groups["all"].texts["t1"].items] == ["e1", "a1"]
    assert [item.item_id for item in dataset.groups["entities"].texts["t1"].items] == ["e1"]
    assert [item.item_id for item in dataset.groups["actions"].texts["t1"].items] == ["a1"]


def test_shown_cols_entity_title_and_highlight_metadata_are_normalized():
    extractions = pd.DataFrame(
        [
            {
                "extraction_id": "entity-001",
                "text_id": "t1",
                "value": "Alpha beta",
                "evidence": ["Alpha", "gamma"],
                "hidden": "not shown",
                "confidence": "high",
            }
        ]
    )

    dataset = normalize_dataset(
        texts_df(),
        [
            Inspector(
                "entities",
                extractions,
                entity_title="Entity: {extraction_id}",
                shown_cols=["value"],
                highlight_cols=["evidence"],
                highlight_relations={"evidence": "value"},
                filter_cols=["confidence"],
            )
        ],
    )

    item = dataset.groups["entities"].texts["t1"].items[0]
    assert item.title == "Entity: entity-001"
    assert [(field.key, field.value) for field in item.fields] == [("value", "Alpha beta")]
    assert [(highlight.source, highlight.text, highlight.related_fields) for highlight in item.highlights] == [
        ("evidence", "Alpha", ["value"]),
        ("evidence", "gamma", ["value"]),
    ]
    assert item.filter_values == {"confidence": "high"}


def test_span_pairs_produce_related_highlight_spans():
    extractions = pd.DataFrame([{"text_id": "t1", "value": "beta", "span_start": 6, "span_end": 10}])

    dataset = normalize_dataset(
        texts_df(),
        [
            Inspector(
                "entities",
                extractions,
                shown_cols=["value"],
                highlight_span_start_cols=["span_start"],
                highlight_span_end_cols=["span_end"],
                highlight_relations={"span_start:span_end": "value"},
            )
        ],
    )

    item = dataset.groups["entities"].texts["t1"].items[0]
    assert [(span.start, span.end, span.text, span.source, span.related_fields) for span in item.spans] == [
        (6, 10, "beta", "span_start:span_end", ["value"])
    ]


@pytest.mark.parametrize(
    "row",
    [
        {"text_id": "t1", "span_start": "bad", "span_end": 5},
        {"text_id": "t1", "span_start": 10, "span_end": 6},
        {"text_id": "t1", "span_start": -1, "span_end": 5},
        {"text_id": "t1", "span_start": 0, "span_end": 999},
        {"text_id": "t1", "span_start": [0, 6], "span_end": [5]},
        {"text_id": "t1", "span_start": 0},
    ],
)
def test_invalid_span_offsets_are_ignored_with_warnings(row):
    inspector = Inspector(
        "entities",
        pd.DataFrame([row]),
        highlight_span_start_cols=["span_start"],
        highlight_span_end_cols=["span_end"],
    )

    with pytest.warns(UserWarning):
        dataset = normalize_dataset(texts_df(), [inspector])

    assert dataset.groups["entities"].texts["t1"].items[0].spans == []


def test_array_field_values_do_not_break_field_filtering():
    extractions = pd.DataFrame(
        [
            {"text_id": "t1", "values": np.array(["a", "b"])},
            {"text_id": "t1", "values": np.array([])},
        ]
    )

    dataset = normalize_dataset(texts_df(), [Inspector("entities", extractions, shown_cols=["values"])])

    fields_by_item = [
        {field.label: field.value for field in item.fields}
        for item in dataset.groups["entities"].texts["t1"].items
    ]
    assert fields_by_item[0]["Values"].tolist() == ["a", "b"]
    assert "Values" not in fields_by_item[1]


def test_missing_required_rows_warn_and_skip():
    texts = pd.DataFrame([{"text_id": None, "text": "Alpha."}, {"text_id": "t1", "text": "Beta."}])
    extractions = pd.DataFrame([{"text_id": "", "value": "x"}, {"text_id": "t1", "value": "y"}])

    with pytest.warns(UserWarning, match="missing required value"):
        dataset = normalize_dataset(texts, [Inspector("entities", extractions, shown_cols=["value"])])

    assert list(dataset.groups["entities"].texts) == ["t1"]
