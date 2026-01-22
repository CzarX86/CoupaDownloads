# PR Plan 38 — Database Foundations for AI Builder Workflow

## Objective
Introduce a persistent database layer that stores documents, extraction snapshots, annotations, and training metadata to replace the current session folders and `review.csv` dependency.

**Resumo em pt-BR:** Vamos criar o banco de dados que guardará PDFs, resultados de extração, anotações e histórico de treinamento, eliminando a necessidade de arquivos CSV para coordenar o fluxo.

## Scope
- Select the database technology (SQLite locally, Postgres-ready) and define connection/config loading under Poetry.
- Design SQLAlchemy models (or equivalent) for `documents`, `document_versions`, `extractions`, `annotations`, `annotation_events`, `training_runs`, `model_versions`, `metrics`.
- Set up Alembic (or custom migration tooling) with initial migration scripts and developer commands.
- Implement storage helpers for blob paths (PDFs, exports, model artefacts) aligned with DB records.

Out of scope:
- API endpoints or SPA integration (handled in later plans).
- Running extractions or training jobs—the focus here is schema and storage scaffolding.
- Migrating legacy CSV data (covered in a downstream plan).

## Affected Files
- `pyproject.toml` — add DB/ORM dependencies (`sqlalchemy`, `alembic`, `psycopg` optional, `aiosqlite` for async SQLite).
- `src/server/db/__init__.py`, `models.py`, `session.py`, `migrations/` — new modules for ORM and migrations.
- `docs/refactor/pr32-refactor-spa-blueprint.md` — reference the new storage stack.
- `docs/USER_GUIDE.md` — note DB bootstrap steps.
- `docs/diagrams/ai_builder_db_schema.mmd` — Mermaid ER diagram of the tables.

## Approach
1. **Choose stack & configuration** — Use SQLAlchemy 2.0 (async) with SQLite by default; environment variable `PDF_TRAINING_DB_URL` for overrides. Configure Alembic with Poetry scripts (`poetry run alembic upgrade head`).
2. **Model the schema** — Document models with UUID primary keys, relationships, timestamps, and JSONB fields for flexible metadata. Capture storage paths for blobs (PDF, labelled export, model artefacts).
3. **Set up migrations** — Initial migration creates all tables; provide helper commands to stamp baseline and to generate future revisions.
4. **Blob storage helpers** — Introduce `storage_root` under `storage/pdf_training/blobs/` with deterministic path builders for documents and models, referencing them in DB rows.
5. **Documentation & DX** — Update blueprint + user guide with setup instructions and dev checklist (create DB, run migration, verify tables).

```mermaid
digraph DBSchema {
  Documents -> DocumentVersions
  DocumentVersions -> Extractions
  Documents -> Annotations
  Annotations -> AnnotationEvents
  Annotations -> TrainingRuns
  TrainingRuns -> ModelVersions
  TrainingRuns -> Metrics
}
```

### Plain-language explainer
We’ll give the system a real database. Every PDF and prediction will have a row in tables instead of living only in folders. That way the next steps (API/UI) can look up documents, save edits, and record training history without juggling CSVs.

## Pseudodiff (representative)
```diff
+++ pyproject.toml
+[tool.poetry.dependencies]
+sqlalchemy = "^2.0"
+alembic = "^1.13"
+aiosqlite = "^0.19"
+
+++ src/server/db/models.py
+class Document(Base):
+    __tablename__ = "documents"
+    id = mapped_column(UUID, primary_key=True)
+    filename = mapped_column(String, nullable=False)
+    storage_path = mapped_column(String, nullable=False)
+    uploaded_at = mapped_column(DateTime(timezone=True))
+
+++ docs/diagrams/ai_builder_db_schema.mmd
+erDiagram
+  DOCUMENTS ||--o{ DOCUMENT_VERSIONS : has
+  DOCUMENT_VERSIONS ||--o{ EXTRACTIONS : produces
+  DOCUMENTS ||--o{ ANNOTATIONS : collects
+  ANNOTATIONS ||--o{ ANNOTATION_EVENTS : records
+  ANNOTATIONS ||--o{ TRAINING_RUNS : feeds
+  TRAINING_RUNS ||--o{ MODEL_VERSIONS : generates
+  TRAINING_RUNS ||--o{ METRICS : reports
```

## Acceptance Criteria
- ORM models and migration scripts exist for all core tables with constraints and indexes.
- Poetry command(s) can create/migrate the DB (`poetry run alembic upgrade head`).
- Storage helper produces deterministic blob paths stored alongside DB records.
- Documentation explains how to initialise the database locally.
- No API/SPA code altered yet; tests (where applicable) confirm schema integrity.

## Manual Tests
- `poetry run alembic upgrade head`
- `poetry run python -m server.db.show_tables` (small util to list tables) — confirm schema.
- Create a sample document via shell helper to ensure blobs + DB row created (temporary script).

## Suggested commit message and branch
- Branch: `impl/38-db-foundations`
- Commit: `feat(db): add database schema and migrations for AI Builder workflow`

## Checklist
- [ ] Objective and Scope are clear and limited.
- [ ] Affected files listed.
- [ ] Pseudodiff (small, readable, representative of the approach).
- [ ] Acceptance criteria and minimal manual tests.
- [ ] Suggested commit message and branch name.
