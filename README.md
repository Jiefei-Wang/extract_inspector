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

from extract_inspector.inspect import Inspector, inspector_web


texts = pd.DataFrame(
    [
        {
            "text_id": "text-001",
            "subject_id": "subject-a",
            "text": "The user cannot log in after password reset.",
        }
    ]
)

entities = pd.DataFrame(
    [
        {
            "text_id": "text-001",
            "extraction_id": "entity-001",
            "evidence": "cannot log in",
            "confidence": "high",
            "problem": "login failure",
        }
    ]
)

inspector_web(
    texts,
    Inspector(
        "entities",
        entities,
        entity_title="Entity: {extraction_id}",
        shown_cols=["problem", "confidence"],
        highlight_cols=["evidence"],
        highlight_relations={"evidence": "problem"},
        filter_cols=["confidence"],
    ),
)
```

This starts a local Flask app with a three-pane inspector:

- inspector tabs and filters
- highlighted source text
- extracted item details

## Multiple Inspectors

Pass one `Inspector` per extraction table:

```python
inspector_web(
    texts,
    Inspector("entities", entities_df, shown_cols=["value"], highlight_cols=["evidence"]),
    Inspector("actions", actions_df, shown_cols=["action"], highlight_cols=["evidence"]),
)
```

The UI includes an `All` tab plus one tab per inspector. `All` combines matching items from every inspector for each source text.

## Highlights And Relations

`highlight_cols` may contain columns whose cells are strings or lists of strings:

```python
Inspector(
    "entities",
    entities_df,
    shown_cols=["value"],
    highlight_cols=["evidence", "alternate_evidence"],
    highlight_relations={
        "evidence": "value",
        "alternate_evidence": "value",
    },
)
```

Matched highlight text is linked to the item card. `highlight_relations` also links a highlight source to one or more displayed fields so hovering a field deep-highlights its evidence, and hovering evidence deep-highlights the related field.

## Offset Spans

If your extraction output has character offsets, configure paired start/end columns:

```python
Inspector(
    "entities",
    entities_df,
    shown_cols=["value"],
    highlight_span_start_cols=["span_start"],
    highlight_span_end_cols=["span_end"],
    highlight_relations={"span_start:span_end": "value"},
)
```

Offsets use Python's half-open convention: `[start, end)`. Offset cells may be scalar values or matched lists of values. Invalid spans are skipped and reported as Python warnings.

## API

```python
Inspector(
    tag_name,
    entities,
    text_id_col="text_id",
    entity_title="",
    shown_cols=None,
    highlight_cols=None,
    highlight_span_start_cols=None,
    highlight_span_end_cols=None,
    highlight_relations=None,
    filter_cols=None,
)

inspector_web(
    texts,
    *inspectors,
    text_id_col="text_id",
    text_col="text",
    subject_id_col="subject_id",
    text_title="Text: {text_id}",
    host="127.0.0.1",
    port=5001,
    debug=False,
    open_browser=True,
)
```

## Demo

The repository includes JSON fixture data under `tests/fixtures`.

Run the demo inspector:

```powershell
python examples/inspect_json_fixture.py
```

Then open:

```text
http://127.0.0.1:5001
```

## Tests

```powershell
python -m pytest
```
