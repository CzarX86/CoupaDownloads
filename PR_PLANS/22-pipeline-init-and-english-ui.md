# PR 22 — Cache RAG embedding model and English UI strings

## Objective
- Avoid model reinitialization and re-downloads per document by caching the RAG embedding model used in candidate retrieval.
- Align all user-visible CLI/menu strings and high-level log/info messages to English, per Language Policy, without changing runtime defaults or behavior.

## Scope
- Add a module-level singleton (or lazy cache) for the HuggingFace embedding model used by RAG-assisted retrieval to prevent repeated initialization across files.
- Keep pipeline/model initialization for BERT NER and SentenceTransformer in the extractor constructor (already once-per-run), no functional changes — only verify it does not reinit inside loops.
- Update user-facing strings to English in the interactive CLI and the extractor’s top-level prints and INFO/warning/error messages. Internal code and comments may remain in pt-BR.
- Do not change algorithms, defaults, or feature flags. Only cache model objects and adjust strings.

Out of scope:
- No architecture changes, no new dependencies, no change to default models.
- No behavioral changes to extraction logic, scoring, or RAG indexing strategy.

## Affected Files
- `embeddinggemma_feasibility/rag_assisted_extraction.py` (embedder singleton / lazy init)
- `embeddinggemma_feasibility/advanced_coupa_field_extractor.py` (user-visible messages to English; confirm init only once)
- `embeddinggemma_feasibility/interactive_cli.py` (menu/options/prompts in English)
- Optional docs text-only updates referencing the menu label:
  - `embeddinggemma_feasibility/docs/RAG_MINIMAL.md`
  - `embeddinggemma_feasibility/COUPA_FIELDS_GUIDE.md`

## Pseudodiff (representative)

### `embeddinggemma_feasibility/rag_assisted_extraction.py`
```diff
@@
 from llama_index.embeddings.huggingface import HuggingFaceEmbedding  # type: ignore

+# Module-level cache to avoid reloading per call
+_EMBED_SINGLETON: HuggingFaceEmbedding | None = None

@@ def retrieve_candidates_for_fields(text: str, field_keys: List[str], top_k: int = 3) -> Dict[str, List[str]]:
-    embed_model = HuggingFaceEmbedding(model_name="intfloat/multilingual-e5-small")
+    global _EMBED_SINGLETON
+    if _EMBED_SINGLETON is None:
+        _EMBED_SINGLETON = HuggingFaceEmbedding(model_name="intfloat/multilingual-e5-small")
+    embed_model = _EMBED_SINGLETON
@@
-    prev_embed = getattr(Settings, "embed_model", None)
 +    prev_embed = getattr(Settings, "embed_model", None)
     setattr(Settings, "embed_model", embed_model)
```

Notes:
- Keeps ephemeral in-memory index per call (text-dependent), but reuses the embedding model across all documents.
- No change to retrieval behavior; only model instantiation caching.

### `embeddinggemma_feasibility/interactive_cli.py`
```diff
@@ def main_menu(...):
-    print("\n=== Menu RAG — embeddinggemma_feasibility ===")
-    print("1) Build index")
-    print("2) Query index")
-    print("3) Mostrar configurações")
-    print("4) Executar Extrator Avançado (PDF → CSV)")
-    print("5) Ferramentas de Revisão (HITL)")
-    print("6) Model Manager (listar/selecionar/comparar)")
-    print("0) Sair")
+    print("\n=== RAG Menu — embeddinggemma_feasibility ===")
+    print("1) Build index")
+    print("2) Query index")
+    print("3) Show settings")
+    print("4) Advanced Extractor (PDF → CSV)")
+    print("5) Review Tools (HITL)")
+    print("6) Model Manager (list/select/compare)")
+    print("0) Exit")
```

### `embeddinggemma_feasibility/advanced_coupa_field_extractor.py`
```diff
@@ class AdvancedCoupaPDFFieldExtractor:
-        self.logger.info("🔧 Inicializando bibliotecas NLP...")
+        self.logger.info("🔧 Initializing NLP libraries...")
@@
-                self.logger.info("✅ BERT NER pipeline carregado")
+                self.logger.info("✅ BERT NER pipeline loaded")
@@
-                    self.logger.info(f"✅ SentenceTransformer carregado: {model_name}")
+                    self.logger.info(f"✅ SentenceTransformer loaded: {model_name}")
@@
-                self.logger.info(f"✅ Ollama disponível com {len(models['models'])} modelos")
+                self.logger.info(f"✅ Ollama available with {len(models['models'])} models")
@@
-        self.logger.info(f"📚 Bibliotecas NLP disponíveis: {', '.join(self.available_libraries)}")
+        self.logger.info(f"📚 Available NLP libraries: {', '.join(self.available_libraries)}")
@@ def main():
-    print("📄 Extrator Avançado de Campos do Coupa com NLP")
+    print("📄 Advanced Coupa Field Extractor with NLP")
```

Notes:
- Only user-facing messages are translated to English. No change to logic, data, or defaults.
- Ensure there is no per-file pipeline init (already one-time in constructor). No new side effects.

## Acceptance Criteria
- Running `poetry run rag-cli` shows the menu entirely in English; option 4 reads “Advanced Extractor (PDF → CSV)”.
- When enabling RAG in the extractor, Hugging Face models download/initialize only on the first document; subsequent documents reuse the cached embedding model (no repeated model downloads/initializations per file).
- The extractor’s high-level prints and INFO logs appear in English while behavior and defaults remain unchanged.
- Full run across multiple files completes with equal or improved throughput compared to before, with no functional regressions.

## Minimal Manual Tests
1) CLI/UI
   - Run `poetry run rag-cli`.
   - Verify the main menu labels are in English, including option 4.

2) RAG embedder caching
   - From the menu, choose “Advanced Extractor (PDF → CSV)”.
   - Answer prompts with RAG enabled and extra validations enabled.
   - Observe that model downloads/initializations occur once at the start; subsequent files do not trigger additional downloads.
   - Re-run in the same session to confirm reuse; optionally verify that HF cache path is used.

3) Regression sanity
   - Run a small batch (2–3 PDFs) and confirm a CSV is produced and the run completes without exceptions.

## Suggested Commit Message and Branch
- Plan branch: `plan/22-pipeline-init-and-english-ui`
- Implementation branch: `feat/22-pipeline-init-and-english-ui`
- Plan commit: `docs(pr-plan): PR 22 — cache RAG embedder and English UI`
- Impl commit: `feat(extractor): PR 22 — cache RAG embedder and English UI`

## Notes
- If future performance needs arise, we can extend caching to optionally persist a lightweight index across documents in a batch, but that is not part of this plan.

