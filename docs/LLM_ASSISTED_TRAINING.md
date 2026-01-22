# LLM-Assisted Training (Optional Helper)

This workflow is completely optional. It layers on top of the existing
Human-in-the-Loop (HITL) review so you can call an external LLM to critique
predictions, suggest improvements, and generate synthetic data before you
decide what to keep.

The tools **never change files automatically**. You (the reviewer) remain in
control and approve every change before it reaches the training datasets.

> Plain language overview: think of the LLM as a brainstorming buddy. It reads
> the prediction spreadsheet, proposes cleaner values, and gives a short
> justification. You choose which ideas to accept. Accepted suggestions are
> merged back into the review CSV and then the normal `feedback_cli` commands
> take over.

## 1. Generate LLM critiques (optional)

```
   poetry run python tools/llm_critique.py \
  --pred-csv reports/advanced_coupa_fields_extraction_*.csv \
  --review-csv reports/feedback/review.csv \
  --out-dir reports/llm_critique/ \
  --provider deepseek \
  --max-rows 40
```

What happens:

- Each row is sent to the selected provider (DeepSeek by default).
- Output files are written to `reports/llm_critique/`:
  - `llm_critique_<timestamp>.jsonl`: raw JSON suggestions per row.
  - `llm_critique_merged_<timestamp>.csv`: your review spreadsheet plus helper
    columns named `<Field>_llm_suggested`, `<Field>_llm_rationale`, and
    `<Field>_llm_confidence`.
  - `llm_critique_summary_<timestamp>.json`: small summary (rows processed,
    cost estimate, provider/model used).
- Use `--dry-run` to preview the flow without touching external APIs.

Cost guardrails:

- DeepSeek keys: set `DEEPSEEK_API_KEY`.
- OpenAI fallback: set `OPENAI_API_KEY` and pass `--provider openai`.
- Flags such as `--max-rows`, `--rate-limit`, and `--temperature` help you keep
  cost predictable.

## 2. Optional self augmentation

```
   poetry run python tools/self_augment.py \
  --input datasets/supervised.jsonl \
  --out datasets/st_pairs_aug.jsonl \
  --fields contract_type,managed_by \
  --provider deepseek \
  --per-value 3
```

What happens:

- The script gathers unique values from the chosen fields and asks the LLM to
  produce paraphrases.
- New positive Sentence-Transformer pairs are written to
  `datasets/st_pairs_aug.jsonl` (one JSON object per line) plus a metadata file
  with basic statistics.
- Use `--dry-run` for synthetic suggestions without any API call.

## 3. Review suggestions inside the gamified CLI

```
poetry run python tools/feedback_cli.py train-st \
  --enable-llm-helpers \
  --llm-jsonl reports/llm_critique/llm_critique_20240921-120000.jsonl \
  --review-csv reports/feedback/review.csv \
  --output embeddinggemma_feasibility/models/st_llm_v1 \
  --datasets-out datasets/llm_session
```

What happens:

1. A Rich-powered “quest” screen appears for each suggestion. Press `Y` to
   accept, `N` to reject, `D` for more details, or `Q` to stop.
2. Accepted suggestions are written to a copy of the review CSV
   (`*_llm_applied.csv` by default).
3. The script re-runs `ingest` on that updated review, producing fresh
   datasets in `datasets/llm_session/`.
4. Training continues on the regenerated `st_pairs.jsonl` using the familiar
   Sentence Transformers pipeline.

All decisions are logged (JSON) so you can audit what was accepted or reverted.

### Flags explained (plain language)

- `--enable-llm-helpers`: turn on the interactive screen.
- `--llm-jsonl`: the JSONL created in step 1.
- `--review-csv`: the human review file that will receive approved values.
- `--llm-review-out`: optional custom path for the updated review CSV. If
  omitted, the tool writes `<original>_llm_applied.csv`.
- `--llm-session-log`: where to store the accept/reject log (defaults inside
  `reports/llm_critique/`).
- `--datasets-out`: directory where new datasets will be generated before
  training. Your original datasets are left untouched.

## 4. Keep the main workflow unchanged

The standard steps (`prepare`, `ingest`, `eval`, `train-st`, `export-labelstudio`)
still work without the helpers. If you skip every LLM flag the CLI behaves as
before. This ensures production defaults stay stable.

## Troubleshooting

- **Missing API key** – Set the correct environment variable or pass
  `--api-key`. Remember to keep keys in your shell and out of version control.
- **Large token usage** – Use `--max-rows`, reduce the field list, or lower the
  temperature. Always inspect the summary JSON for cost estimates.
- **JSON parsing errors** – Some providers may return extra text. The scripts
  capture the raw content in the JSONL so you can inspect and retry.
- **Rich import error** – Install project dependencies (the repository already
  lists `rich` and `textual`).

## Quick checklist before shipping results

1. Run `llm_critique.py` (optional) and inspect the merged CSV.
2. Accept or reject suggestions in the gamified `train-st` session.
3. Evaluate metrics with `feedback_cli.py eval` using the updated review CSV.
4. Store the regenerated datasets and model artefacts in version control or a
   model registry as appropriate.

Stay mindful of privacy: redact anything sensitive before sending to external
providers, and never commit API keys.
