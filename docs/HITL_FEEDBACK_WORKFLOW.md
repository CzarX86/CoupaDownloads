# Human-in-the-Loop (HITL) Feedback Workflow

This guide shows how to review predictions, ingest corrections, generate training datasets, evaluate metrics, and optionally fine‑tune a Sentence Transformers model — without changing the main pipeline defaults.

## 1) Prepare a review CSV

Use the latest pipeline CSV as input (produced by the advanced extractor):

```
python tools/feedback_cli.py prepare \
  --pred-csv reports/advanced_coupa_fields_extraction_*.csv \
  --out reports/feedback/review.csv \
  --fields contract_name,contract_type,sow_value_eur,pwo_number,managed_by \
  --sample 30
```

This creates triplets per field: `<Field>_pred`, `<Field>_gold`, `<Field>_status` and preserves metadata (`Source File`, `Extraction Confidence`, `Extraction Method`).

Recommended statuses: `OK | CORRECTED | NEW | MISSING | REJECTED`.

## 2) Annotate

Open `reports/feedback/review.csv` in your editor/spreadsheet. Fill the `_gold` and `_status` columns for rows you reviewed.

## 3) Ingest and build datasets

```
python tools/feedback_cli.py ingest \
  --review-csv reports/feedback/review.csv \
  --out-dir datasets/
```

Outputs:
- `datasets/supervised.jsonl`: one object per document with `{source_file, labels:{...}}`
- `datasets/st_pairs.jsonl`: positive/negative pairs derived from categorical fields
- `datasets/training_analysis.json`: patterns/statistics from `ContractDataTrainer`

## 4) Evaluate

```
python tools/feedback_cli.py eval \
  --review-csv reports/feedback/review.csv \
  --report-dir reports/feedback/
```

Outputs `metrics.json` and `metrics.md` with per‑field accuracy and coverage.

## 5) Optional: fine‑tune Sentence Transformers

```
python tools/feedback_cli.py train-st \
  --dataset datasets/st_pairs.jsonl \
  --output embeddinggemma_feasibility/models/st_custom_v1
```

This uses a lightweight default model (`all-MiniLM-L6-v2`). No pipeline defaults are changed; to use the custom model, point the extractor config to the new path when you are ready.

## 6) Optional: export tasks for Label Studio

```
python tools/feedback_cli.py export-labelstudio \
  --review-csv reports/feedback/review.csv \
  --out reports/feedback/tasks.json
```

This produces a basic JSON that can be adapted for a Label Studio project configuration.

## Switching the active ST model (after validation)

After evaluating metrics, you can point the extractor to a fine‑tuned model without changing defaults:

```python
from embeddinggemma_feasibility.config import update_config
update_config(embed_model_custom_path="embeddinggemma_feasibility/models/st_custom_v1")
```

To revert to the default model, set `None`. Alternatively, use the Model Manager:

```bash
python tools/model_select.py list
python tools/model_select.py set-active --path embeddinggemma_feasibility/models/st_custom_v1
python tools/model_select.py show-active
```
