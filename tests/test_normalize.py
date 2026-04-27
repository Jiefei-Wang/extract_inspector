import pandas as pd
import pytest

from extract_inspector.inspect.normalize import normalize_dataset


def texts_df():
    return pd.DataFrame(
        [
            {"text_id": "t1", "subject_id": "s1", "text": "Alpha beta gamma delta."},
            {"text_id": "t2", "subject_id": "s2", "text": "No evidence here."},
        ]
    )


def first_item(dataset, group="extractions", text_id="t1"):
    return dataset.groups[group].texts[text_id].items[0]


def test_string_highlight_column():
    extractions = pd.DataFrame([{"text_id": "t1", "evidence": "Alpha beta", "value": "x"}])

    dataset = normalize_dataset(texts_df(), extractions)

    assert first_item(dataset).highlights == ["Alpha beta"]


def test_list_valued_highlight_cell():
    extractions = pd.DataFrame([{"text_id": "t1", "evidence": ["Alpha", "gamma"], "value": "x"}])

    dataset = normalize_dataset(texts_df(), extractions)

    assert first_item(dataset).highlights == ["Alpha", "gamma"]


def test_multiple_highlight_columns_with_string_cells():
    extractions = pd.DataFrame(
        [{"text_id": "t1", "evidence_a": "Alpha", "evidence_b": "gamma", "value": "x"}]
    )

    dataset = normalize_dataset(texts_df(), extractions, highlight_col=["evidence_a", "evidence_b"])

    assert first_item(dataset).highlights == ["Alpha", "gamma"]
    assert first_item(dataset).highlights_by_column == {
        "evidence_a": ["Alpha"],
        "evidence_b": ["gamma"],
    }


def test_multiple_highlight_columns_with_list_and_string_cells():
    extractions = pd.DataFrame(
        [{"text_id": "t1", "evidence_a": ["Alpha", "beta"], "evidence_b": "gamma", "value": "x"}]
    )

    dataset = normalize_dataset(texts_df(), extractions, highlight_col=["evidence_a", "evidence_b"])

    assert first_item(dataset).highlights == ["Alpha", "beta", "gamma"]
    assert first_item(dataset).highlights_by_column == {
        "evidence_a": ["Alpha", "beta"],
        "evidence_b": ["gamma"],
    }


def test_null_empty_and_non_string_highlight_values_are_ignored():
    extractions = pd.DataFrame(
        [
            {"text_id": "t1", "evidence": None, "value": "none"},
            {"text_id": "t1", "evidence": "", "value": "empty"},
            {"text_id": "t1", "evidence": [], "value": "list"},
            {"text_id": "t1", "evidence": 123, "value": "number"},
            {"text_id": "t1", "evidence": ["Alpha", 123, ""], "value": "mixed"},
        ]
    )

    dataset = normalize_dataset(texts_df(), extractions)

    assert [item.highlights for item in dataset.groups["extractions"].texts["t1"].items] == [
        [],
        [],
        [],
        [],
        ["Alpha"],
    ]


def test_missing_optional_subject_and_extraction_id_works():
    texts = pd.DataFrame([{"text_id": "t1", "text": "Alpha."}])
    extractions = pd.DataFrame([{"text_id": "t1", "evidence": "Alpha", "value": "x"}])

    dataset = normalize_dataset(texts, extractions)

    document = dataset.groups["extractions"].texts["t1"]
    assert document.subject_id is None
    assert dataset.has_subject_id is False
    assert dataset.filter_categorical_cols == []
    assert document.items[0].item_id == "extractions:t1:0"


def test_generated_extraction_ids_are_stable_within_run():
    extractions = pd.DataFrame(
        [
            {"text_id": "t1", "evidence": "Alpha", "value": "x"},
            {"text_id": "t1", "evidence": "gamma", "value": "y"},
        ]
    )

    dataset = normalize_dataset(texts_df(), extractions)

    assert [item.item_id for item in dataset.groups["extractions"].texts["t1"].items] == [
        "extractions:t1:0",
        "extractions:t1:1",
    ]


def test_dict_extractions_create_multiple_groups():
    dataset = normalize_dataset(
        texts_df(),
        {
            "diagnoses": pd.DataFrame([{"text_id": "t1", "evidence": "Alpha"}]),
            "medications": pd.DataFrame([{"text_id": "t1", "evidence": "gamma"}]),
        },
    )

    assert list(dataset.groups) == ["diagnoses", "medications"]
    assert first_item(dataset, "diagnoses").summary == "Diagnoses"


def test_extraction_group_column_splits_single_table_into_groups():
    extractions = pd.DataFrame(
        [
            {"text_id": "t1", "kind": "diagnosis", "evidence": "Alpha"},
            {"text_id": "t1", "kind": "medication", "evidence": "gamma"},
        ]
    )

    dataset = normalize_dataset(texts_df(), extractions, extraction_group="kind")

    assert list(dataset.groups) == ["diagnosis", "medication"]


def test_scalar_span_columns_produce_one_span_and_exclude_span_fields():
    extractions = pd.DataFrame(
        [{"text_id": "t1", "span_start": 6, "span_end": 10, "evidence": "Alpha", "value": "x"}]
    )

    dataset = normalize_dataset(
        texts_df(),
        extractions,
        span_start_col="span_start",
        span_end_col="span_end",
    )

    item = first_item(dataset)
    assert [(span.start, span.end, span.text) for span in item.spans] == [(6, 10, "beta")]
    assert [field.label for field in item.fields] == ["Value"]


def test_list_span_columns_produce_multiple_spans():
    extractions = pd.DataFrame(
        [{"text_id": "t1", "span_start": [0, 11], "span_end": [5, 16], "value": "x"}]
    )

    dataset = normalize_dataset(
        texts_df(),
        extractions,
        span_start_col="span_start",
        span_end_col="span_end",
    )

    assert [(span.start, span.end, span.text) for span in first_item(dataset).spans] == [
        (0, 5, "Alpha"),
        (11, 16, "gamma"),
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
    extractions = pd.DataFrame([row])

    with pytest.warns(UserWarning):
        dataset = normalize_dataset(
            texts_df(),
            extractions,
            span_start_col="span_start",
            span_end_col="span_end",
        )

    assert first_item(dataset).spans == []


def test_only_one_configured_span_column_warns():
    extractions = pd.DataFrame([{"text_id": "t1", "span_start": 0, "span_end": 5}])

    with pytest.warns(UserWarning):
        dataset = normalize_dataset(texts_df(), extractions, span_start_col="span_start")

    assert first_item(dataset).spans == []


def test_no_categorical_filters_by_default():
    extractions = pd.DataFrame([{"text_id": "t1", "evidence": "Alpha", "confidence": "high"}])

    dataset = normalize_dataset(texts_df(), extractions)

    item = first_item(dataset)
    assert dataset.filter_categorical_cols == []
    assert item.filter_values == {}
    assert {field.label: field.value for field in item.fields}["Confidence"] == "high"


def test_configured_filter_columns_are_collected_and_still_displayed():
    extractions = pd.DataFrame(
        [{"text_id": "t1", "evidence": "Alpha", "entity_type": "symptom", "confidence": "high"}]
    )

    dataset = normalize_dataset(
        texts_df(),
        extractions,
        filter_categorical_cols=["entity_type", "confidence"],
    )

    item = first_item(dataset)
    assert dataset.filter_categorical_cols == ["entity_type", "confidence"]
    assert item.filter_values == {"entity_type": "symptom", "confidence": "high"}
    assert {field.label: field.value for field in item.fields}["Entity Type"] == "symptom"
    assert {field.label: field.value for field in item.fields}["Confidence"] == "high"


def test_null_list_and_dict_filter_values_are_ignored():
    extractions = pd.DataFrame(
        [
            {
                "text_id": "t1",
                "entity_type": None,
                "confidence": ["high"],
                "metadata": {"source": "x"},
                "flag": True,
            }
        ]
    )

    dataset = normalize_dataset(
        texts_df(),
        extractions,
        filter_categorical_cols=["entity_type", "confidence", "metadata", "flag"],
    )

    assert first_item(dataset).filter_values == {"flag": "True"}
