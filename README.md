# extract_inspector

General-purpose web inspector for source texts and extracted structured data.

The inspector is domain-neutral. It works with any extraction output that can be represented as pandas DataFrames linked to source texts by a shared ID.

## Install

From this repository:

```powershell
pip install -e .
```

For test dependencies:

```powershell
pip install -e ".[test]"
```

## Basic Usage

```python
import pandas as pd

from extract_inspector.inspect import inspect_extractions


texts = pd.DataFrame(
    [
        {
            "text_id": "text-001",
            "subject_id": "subject-a",
            "text": "The user cannot log in after password reset.",
        }
    ]
)

extractions = pd.DataFrame(
    [
        {
            "text_id": "text-001",
            "evidence": "cannot log in",
            "confidence": "high",
            "problem": "login failure",
        }
    ]
)

inspect_extractions(texts, extractions)
```

This starts a local Flask app with a three-pane inspector:

- extraction groups and filters
- highlighted source text
- extracted item details

## Multiple Extraction Groups

Pass a dictionary of DataFrames to inspect multiple extraction types:

```python
inspect_extractions(
    texts,
    {
        "entities": entities_df,
        "actions": actions_df,
    },
)
```

Each dictionary key becomes an extraction group in the UI.

## Evidence Columns

`evidence_col` can be a single column name:

```python
inspect_extractions(texts, extractions, evidence_col="evidence")
```

or multiple column names:

```python
inspect_extractions(
    texts,
    extractions,
    evidence_col=["evidence", "alternate_evidence", "quote"],
)
```

Each evidence cell may be either a string:

```python
"cannot log in"
```

or a list of strings:

```python
["cannot log in", "account temporarily locked"]
```

All valid evidence strings are highlighted in the source text.

## Categorical Filters

By default, the left filter panel only shows Text ID and Subject ID filters.

To add dropdown filters for extraction columns, pass `filter_categorical_cols`:

```python
inspect_extractions(
    texts,
    extractions,
    filter_categorical_cols=["entity_type", "confidence"],
)
```

Each configured column appears as a dropdown with `All` selected by default. Selecting a value filters extracted items, and a text remains visible if it has at least one matching item.

Filter columns still appear in extracted item cards as normal fields unless you hide them with `exclude_fields`.

## API

```python
inspect_extractions(
    texts,
    extractions,
    *,
    text_id="text_id",
    text_col="text",
    subject_id="subject_id",
    extraction_id=None,
    extraction_group=None,
    evidence_col="evidence",
    span_start_col=None,
    span_end_col=None,
    filter_categorical_cols=None,
    exclude_fields=None,
    field_labels=None,
    host="127.0.0.1",
    port=5001,
    debug=False,
    open_browser=True,
)
```

## Offset Spans

If your extraction output has character offsets, pass the start and end columns:

```python
inspect_extractions(
    texts,
    extractions,
    span_start_col="span_start",
    span_end_col="span_end",
)
```

Offsets use Python's half-open convention: `[start, end)`.

Span cells may be scalar values:

```python
{"span_start": 4, "span_end": 14}
```

or matched lists:

```python
{"span_start": [4, 28], "span_end": [14, 35]}
```

When both offset spans and evidence text are provided, the inspector highlights both. Invalid spans are skipped and reported as Python warnings.

## Demo

The repository includes JSON fixture data under `tests/fixtures`.

Run the demo inspector:

```powershell
python examples\inspect_json_fixture.py
```

Then open:

```text
http://127.0.0.1:5001
```

The demo shows:

- multiple extraction groups
- multiple evidence columns
- string and list-valued evidence cells
- matched and unmatched evidence

## Tests

```powershell
python -m pytest
```
