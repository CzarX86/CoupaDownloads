# PR Plan 41 — Training Pipeline Consuming Database Annotations

## Objective
Rebuild the training pipeline so it reads reviewed annotations from the database, generates datasets, trains models, and logs metrics back to the DB, replacing the CSV-based workflow.

**Resumo em pt-BR:** Vamos adaptar o pipeline de treinamento para buscar dados anotados diretamente no banco, gerar datasets intermediários, treinar o modelo e registrar métricas/versionamento sem usar CSV.

## Scope
- Implement dataset builders that query annotations/annotation_events and produce in-memory DataFrames/JSONL for training and evaluation.
- Update training orchestration (currently in `cmd_ingest`, `cmd_eval`, `cmd_train_st`) to operate through services, writing results (datasets summary, metrics) to DB tables and blob storage paths.
- Create evaluation reporting that stores accuracy/coverage metrics in the `metrics` table, linked to `training_runs` and `model_versions`.
- Provide download/export endpoints for datasets/models when needed (for auditing or external use).

Out of scope:
- SPA UI for history (already in Plan 40, uses data produced here).
- Data migration and CLI deprecation (Plan 42).

## Affected Files
- `tools/feedback_utils.py`, `tools/pdf_annotation.py` — refactor to route through service layer (DB), keeping thin wrappers for CLI legacy mode.
- `src/server/pdf_training_app/services.py` — add training orchestration functions.
- `src/server/db/repository.py` — queries for annotations, training runs, metrics.
- `src/server/pdf_training_app/api.py` — ensure training endpoints surface DB results (metrics, artefacts).
- `docs/USER_GUIDE.md`, `docs/refactor/pr32-refactor-spa-blueprint.md` — describe the DB-driven training pipeline.

## Approach
1. **Dataset extraction** — Query annotations with latest accepted values, join metadata, and produce dataset structures (Python objects). Persist snapshots if needed (Parquet/JSONL) under blob storage with references.
2. **Training orchestration** — Convert `cmd_ingest`/`cmd_eval`/`cmd_train_st` to service functions that accept DB session + training_run_id. CLI commands become thin wrappers calling those services.
3. **Metrics logging** — After training, compute metrics and store them in `metrics` table with JSON payload (accuracy, coverage, confusion). Link artefact paths to `model_versions`.
4. **Exports & downloads** — Provide API endpoints to download latest dataset/model for auditing (optional but handy for QA).
5. **Tests & docs** — Unit/integration tests for dataset builder, training services, metrics logging. Update docs explaining the new pipeline (no CSV).

```mermaid
digraph Training {
  Annotations[DB: annotations]
  Annotations -> DatasetBuilder
  DatasetBuilder -> TrainingJob
  TrainingJob -> ModelArtifacts[Blob: models/]
  TrainingJob -> MetricsTable[DB: metrics]
  MetricsTable -> TrainingRuns
}
```

### Plain-language explainer
Training will now read the corrected labels straight from the database, build the dataset on the fly, train the model, and write back the results. No more exporting/importing CSV just to kick off a job.

## Pseudodiff (representative)
```diff
--- tools/feedback_cli.py
+++ tools/feedback_cli.py
@@
-    result = ingest_pdf_annotation_export(export_json, review_csv)
+    result = annotation_service.ingest_export(export_json)
@@
-    cmd_ingest(args)
+    training_service.run_ingest(args.training_run_id)

+++ src/server/pdf_training_app/services.py
+async def run_training(training_run_id: UUID) -> None:
+    dataset = await datasets.build_from_db(training_run_id)
+    metrics, model_path = await trainer.train(dataset)
+    await metrics_repo.save(training_run_id, metrics, model_path)
```

## Acceptance Criteria
- Dataset builder pulls annotations from DB (latest accepted values) and produces training/eval datasets without writing CSV.
- Training job service persists artefact paths, metrics, and status to DB tables.
- CLI commands delegate to DB-aware services (legacy CSV path optional, behind flag).
- Tests cover dataset query logic and training service (with mocked trainer for speed).
- Documentation explains the DB-driven training pipeline and how to download artefacts if needed.

## Manual Tests
- `poetry run pytest tools/tests/test_training_service.py`
- Manual run: trigger training from SPA → verify DB tables (`training_runs`, `metrics`, `model_versions`) and artefact paths.
- Optional CLI check: `poetry run python tools/feedback_cli.py train-st --use-db --training-run <id>`.

## Suggested commit message and branch
- Branch: `impl/41-training-db-pipeline`
- Commit: `feat(training): generate datasets and train models directly from DB annotations`

## Checklist
- [ ] Objective and Scope are clear and limited.
- [ ] Affected files listed.
- [ ] Pseudodiff (small, readable, representative of the approach).
- [ ] Acceptance criteria and minimal manual tests.
- [ ] Suggested commit message and branch name.
