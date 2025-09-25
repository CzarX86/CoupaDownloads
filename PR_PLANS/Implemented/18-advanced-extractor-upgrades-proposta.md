# PR 18 — Advanced Extractor Upgrades: ST fine-tune, reranker, multi-doc aggregation, and HITL training loop
- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: TBD
- Observações: 


## Objective
Deliver a robust upgrade of the advanced extractor to become the primary, most capable module by:
- Prioritizing a fine-tuned Sentence Transformers model for semantic retrieval and RAG.
- Adding an in-extractor reranker (CrossEncoder) to improve snippet selection.
- Aggregating evidence across multiple documents per PO (any supported file type) and from filenames.
- Minimizing regex to normalization/validation only; rely on semantic methods for extraction.
- Adding caching for embeddings/RAG.
- Providing a human-in-the-loop (HITL) review → retrain → evaluate workflow with CLI helpers.

## Scope
In scope (implementation confined to `embeddinggemma_feasibility`):
- Config: model selection and feature flags (ST custom path, use_reranker, cache_dir, enable_filename_clues, aggregation).
- Advanced extractor: integrate ST custom model, reranker, multi-doc PO aggregation (PDF, DOCX, TXT/MD, HTML, MSG/EML, images via OCR), filename signal parsing, and caching of embeddings/snippets.
- RAG: reuse persisted HNSW index when available; optional diskcache for transient query caches.
- Review/Training CLI: generate review bundles, ingest corrected CSVs, curate a training dataset, fire fine-tuning, and run evaluation.

Out of scope:
- Changes to downloader automation or Coupa website logic.
- Heavy refactors to unrelated modules.

## Affected Files
- Update: `embeddinggemma_feasibility/config.py` (new options)
- Update: `embeddinggemma_feasibility/advanced_coupa_field_extractor.py`
- Update: `embeddinggemma_feasibility/rag_assisted_extraction.py` (reuse reranker when enabled)
- Add: `embeddinggemma_feasibility/cache_utils.py` (diskcache helpers)
- Add: `embeddinggemma_feasibility/content_loader.py` (multi-format text extraction dispatcher)
- Add: `embeddinggemma_feasibility/po_aggregator.py` (aggregate per-PO across docs + filenames)
- Add: `embeddinggemma_feasibility/filename_signals.py` (parse PWO, project, dates from filenames)
- Add: `embeddinggemma_feasibility/review_cli.py` (HITL tooling: generate/ingest/eval)
- Update: `embeddinggemma_feasibility/interactive_cli.py` (menu entries for review/eval)
- Docs: `embeddinggemma_feasibility/README.md` (usage), `docs/HITL_WORKFLOW.md`

## Pseudodiff
```diff
--- a/embeddinggemma_feasibility/config.py
+++ b/embeddinggemma_feasibility/config.py
 class Config(BaseModel):
-    embed_model: str = "all-MiniLM-L6-v2"
+    embed_model: str = "all-MiniLM-L6-v2"
+    embed_model_custom_path: str | None = None  # prefer if set
+    use_reranker: bool = True
+    enable_diskcache: bool = True
+    cache_dir: str = "~/.cache/coupa_rag"
+    enable_filename_clues: bool = True
+    aggregate_by_po: bool = True

--- a/embeddinggemma_feasibility/advanced_coupa_field_extractor.py
+++ b/embeddinggemma_feasibility/advanced_coupa_field_extractor.py
@@ class AdvancedCoupaPDFFieldExtractor:
-    # Sentence Transformers load
-    self.nlp_models['sentence_transformer'] = SentenceTransformer("all-MiniLM-L6-v2")
+    # Prefer custom ST if provided (fine-tuned)
+    model_name = self.config.embed_model_custom_path or self.config.embed_model
+    self.nlp_models['sentence_transformer'] = SentenceTransformer(model_name)
@@ def extract_coupa_fields(...):
-    # RAG assisted (no reranker)
+    # RAG assisted with optional reranker for snippet selection
+    # if cfg.use_reranker: apply CrossEncoder reranking before merging
@@ end of processing
-    return extraction
+    return extraction
@@
@@ def process_all_documents(...):
    # iterate over supported file types; produce list of CoupaFieldExtraction
    # per-document loop; if cfg.aggregate_by_po: post-aggregate per PWO
    if self.config.aggregate_by_po:
        from .po_aggregator import aggregate_extractions_by_po
        extractions = aggregate_extractions_by_po(extractions, use_filename_clues=self.config.enable_filename_clues)
    return extractions

--- a/embeddinggemma_feasibility/rag_assisted_extraction.py
+++ b/embeddinggemma_feasibility/rag_assisted_extraction.py
@@ retrieve_candidates_for_fields(...)
- nodes = engine.retrieve(query)
+ nodes = engine.retrieve(query)
+ if cfg.use_reranker:
+    nodes = apply_reranker(query, nodes)  # CrossEncoder rerank

+ def apply_reranker(query, nodes):
+     # Convert nodes → Candidate list and call rag.rerank.rerank_candidates
+     ...

+--- a/embeddinggemma_feasibility/po_aggregator.py (new)
+def aggregate_extractions_by_po(extractions, use_filename_clues=True):
+    # group by PWO, merge best evidence across documents; optional filename signals
+    # return new list of CoupaFieldExtraction (one per PWO)
+    ...
+
+--- a/embeddinggemma_feasibility/filename_signals.py (new)
+def parse_filename_metadata(filename: str) -> dict:
+    # extract PWO numbers, project names, dates, currencies hints, vendor
+    ...
+
+--- a/embeddinggemma_feasibility/cache_utils.py (new)
+def cached_embed(text):
+    # use diskcache keyed by model+hash(text)
+    ...
+
+--- a/embeddinggemma_feasibility/review_cli.py (new)
+Commands:
+  review generate  --source reports/*.csv --size 20  # sample POs for review
+  review ingest    --corrected path/to/reviewed.csv  # add to training set
+  review train     --output models/st_custom_vX      # fine-tune ST
+  review eval      --gt path/to/groundtruth.csv      # report metrics
+
--- a/embeddinggemma_feasibility/interactive_cli.py
+++ b/embeddinggemma_feasibility/interactive_cli.py
+ 5) Ferramentas de Revisão (HITL)
```

## Acceptance Criteria
- Config supports `embed_model_custom_path`, `use_reranker`, `enable_diskcache`, `enable_filename_clues`, `aggregate_by_po`.
- Advanced extractor loads a custom ST model path when provided and runs; otherwise defaults to existing model.
- Reranker improves snippet ordering without errors; no ServiceContext warnings.
- Aggregation produces one row per PO when enabled, combining evidence from multiple documents (PDF/DOCX/TXT/HTML/MSG/EML/IMG) and filenames.
- Disk cache reduces repeat runtime on identical inputs.
- Review CLI can:
  - generate a review bundle (sample of 10–20 POs) with predictions and top snippets per field;
  - ingest a corrected CSV and append to a training dataset;
  - fine-tune ST to an output directory;
  - evaluate predictions vs. a ground truth CSV and print per-field precision/recall.
- Documentation updated with workflow and examples.

## Minimal Manual Tests
1) Custom model preference
   - Put a fine-tuned ST at `models/st_custom_v1/`.
   - Set `embed_model_custom_path` in config; run option 4; confirm it loads and runs.
2) Reranker
   - Toggle `use_reranker=True`; verify logs show reranking active and retrieved snippets change order.
3) Aggregation by PO
   - Enable `aggregate_by_po`; process a folder with mixed file types per PO; confirm CSV has one row per PWO and fields reflect best evidence.
4) Filename clues
   - Use files named like `PO16799866_PWO12345_ProjectX_v2.pdf`; confirm PWO/Project populate when missing in text.
5) Review/HITL
   - `review_cli.py` generate → annotate a few rows → ingest → train → eval; confirm model artifact and metrics.

## Suggested Commit Message and Branch
- Branch (plan): `plan/18-advanced-extractor-upgrades`
- Implementation: `feat/18-advanced-extractor-upgrades`
- Commit (plan): `docs(pr-plan): PR 18 — advanced extractor upgrades (ST custom, reranker, aggregation, HITL)`

## Checklist
- [x] Objective and Scope are clear and limited.
- [x] Affected files listed.
- [x] Pseudodiff (small/representative) included.
- [x] Acceptance criteria and minimal manual tests.
- [x] Suggested commit message and branch name.
