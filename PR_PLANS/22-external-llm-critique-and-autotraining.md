# PR 22 — External LLM Critique + Auto‑training (optional, gated)

## Objective
Leverage an external LLM (e.g., OpenAI API) during the training phase to:
- Produce structured critiques of field predictions and suggest corrections.
- Generate synthetic supervision (few‑shot augmentation) and self‑consistency checks.
- Keep this fully optional, behind a flag and environment variables; no change to runtime defaults.

## Scope
- Add `tools/llm_critique.py`:
  - Inputs: a predictions CSV and/or a reviewed CSV.
  - For each row/field, ask the LLM to critique and propose a corrected value with rationale, returning JSON.
  - Output artifacts: `reports/llm_critique/*.jsonl` and a merged CSV with columns `<Field>_llm_suggested`.
- Add `tools/self_augment.py`:
  - Use LLM to create paraphrases and near‑duplicates for categorical terms (contract types, platforms, currencies) to enrich ST pairs.
- Config and safety:
  - Read `OPENAI_API_KEY` (or provider‑agnostic via pluggable interface) from env; never commit keys.
  - Rate limiting, cost guardrails (max tokens/files per run), redact PII if configured.
- Docs: `docs/LLM_ASSISTED_TRAINING.md` (risks, costs, privacy, usage examples).

Out of scope:
- Invoking LLMs in the main extraction path.
- Changing default prompts in `advanced_coupa_field_extractor.py`.

## Affected files
- Add: `tools/llm_critique.py`
- Add: `tools/self_augment.py`
- Add: `docs/LLM_ASSISTED_TRAINING.md`
- Update: `docs/HITL_FEEDBACK_WORKFLOW.md` (link optional LLM‑assisted augmentation)

## Pseudodiff (representative)
```diff
+ tools/llm_critique.py
+ -------------------------------------------------
+ def critique_csv(pred_csv: str, out_dir: str, model: str = "gpt-4o-mini"): 
+   # stream rows; for each field build a compact JSON‑only prompt; write results to JSONL
+
+ tools/self_augment.py
+ -------------------------------------------------
+ def augment_terms(input_jsonl: str, out_pairs: str, model: str = "gpt-4o-mini"): 
+   # generate paraphrases/synonyms for categorical fields → pairs for ST
+
+ docs/LLM_ASSISTED_TRAINING.md
+ -------------------------------------------------
+ # LLM‑Assisted Training
+ - Set `OPENAI_API_KEY`.
+ - Run critique on a predictions CSV, produce suggestions.
+ - Merge suggestions cautiously; human remains in the loop.
+ - Cost & privacy caveats.
```

## Acceptance Criteria
- `tools/llm_critique.py` runs with an API key set and produces JSONL suggestions without modifying source files.
- `tools/self_augment.py` generates additional pairs compatible with `feedback_cli.py train-st`.
- Docs clearly mark the feature as optional/experimental, with cost/privacy warnings.

## Minimal Manual Tests
1) Set `OPENAI_API_KEY`.
2) Run `python tools/llm_critique.py --pred-csv reports/advanced_*.csv --out reports/llm_critique/` and verify JSONL outputs.
3) Run `python tools/self_augment.py --input datasets/supervised.jsonl --out datasets/st_pairs_aug.jsonl` and verify file.

## Suggested Commit Message and Branch
- Branch (plan): `plan/22-external-llm-critique-autotraining`
- Commit (plan): `docs(pr-plan): PR 22 — external LLM critique + auto‑training (optional)`
- Branch (impl): `feat/22-external-llm-critique-autotraining`

## Checklist
- [x] Objective and Scope are clear and limited.
- [x] Affected files listed.
- [x] Pseudodiff (small/representative) included.
- [x] Acceptance criteria and minimal manual tests.
- [x] Suggested commit message and branch name.
