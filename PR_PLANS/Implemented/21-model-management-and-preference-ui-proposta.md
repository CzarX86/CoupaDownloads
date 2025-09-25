# PR 21 — Model Management UI, Side‑by‑Side Preference Review, and Docs note (model switching)
- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: TBD
- Observações: 


## Objective
Provide a practical way to:
- Choose which Sentence Transformers (ST) model the extractor uses (default or custom) and view metadata (freshness, size, embedding dim, tag/version).
- Run side‑by‑side comparisons between two models on the same inputs and capture human preferences per field (cell‑level) to feed training.
- Add a docs note explaining how to switch the active model via `embed_model_custom_path` after validation.

This is additive and optional: no change to defaults or main pipeline behavior unless the user selects a custom model.

## Scope
In `embeddinggemma_feasibility` and `tools/` only:
- Model registry and selection:
  - List local ST models under `embeddinggemma_feasibility/models/` (and any extra search paths) with metadata (name/path, mtime, size, embedding dim if available, contract_config.json info).
  - Allow setting the active model by writing `embed_model_custom_path` (via a small config setter CLI) or by creating a `models/current` symlink.
- Side‑by‑side (A/B) comparison CLI:
  - Given two models (A,B), run field extraction on a sample set (from PDFs or cached text) and show per‑field predictions side‑by‑side.
  - Ask the reviewer to pick A/B/“tie” for each field (or skip), record preferences to `datasets/preferences.jsonl`.
  - Provide an export that converts preferences into ST training pairs with a “preferred” signal (for self‑supervised boosting).
- Docs:
  - Add a short note to `docs/HITL_FEEDBACK_WORKFLOW.md` on switching the model via `embed_model_custom_path`.
  - New page `docs/MODEL_MANAGEMENT.md` with instructions to list/select models and run A/B.

Out of scope (follow‑up plan):
- Integration with external LLMs (e.g., OpenAI) for auto‑critique/training — propose as PR 22 due to keys/cost/privacy.
- GUI; this PR provides terminal UI only (interactive CLI prompts).

## Affected files
- Add: `tools/model_registry.py` (scan model dirs, read metadata, sort, pretty print)
- Add: `tools/model_select.py` (CLI: list, set-active, show-active; updates `embed_model_custom_path` or creates `models/current` symlink)
- Add: `tools/ab_compare_cli.py` (run A/B extraction, capture preferences → datasets/preferences.jsonl, export to st_pairs_pref.jsonl)
- Update: `embeddinggemma_feasibility/interactive_cli.py` (new menu: “Model Manager” → list/select/compare)
- Update: `docs/HITL_FEEDBACK_WORKFLOW.md` (add note on `embed_model_custom_path` switch)
- Add: `docs/MODEL_MANAGEMENT.md` (how to manage models and run A/B)

## Pseudodiff (representative)
```diff
+ tools/model_registry.py
+ -------------------------------------------------
+ def find_models(search_dirs: list[str]) -> list[dict]:
+   # Scan for dirs with Sentence Transformers artifacts or our custom contract_config.json
+   # Return [{"name": str, "path": str, "mtime": float, "size_mb": float, "dim": int | None, "tags": {...}}]
+
+ def load_st_dim(model_dir: str) -> int | None:
+   # Try to read config.json or sentence-transformers metadata to infer embedding dimension
+
+ tools/model_select.py
+ -------------------------------------------------
+ if __name__ == "__main__":
+   # Commands: list | set-active | show-active | clear-active
+   # set-active: writes embed_model_custom_path in config via update_config(); optional symlink models/current
+
+ tools/ab_compare_cli.py
+ -------------------------------------------------
+ def main():
+   # Args: --model-a PATH --model-b PATH --pdf-dir PATH --sample 20 --out datasets/preferences.jsonl
+   # For each sampled doc: run extraction with A and B; present per-field side-by-side; prompt user (A/B/tie/skip)
+   # Persist preferences as JSONL with {source_file, field, a: valA, b: valB, choice, timestamp}
+   # Subcommand: export-pairs -> convert preferences into st_pairs_pref.jsonl (preferred positives)
+
*** a/embeddinggemma_feasibility/interactive_cli.py
--- b/embeddinggemma_feasibility/interactive_cli.py
@@
-        print("5) Ferramentas de Revisão (HITL)")
+        print("5) Ferramentas de Revisão (HITL)")
+        print("6) Model Manager (listar/selecionar/comparar)")
@@
-        elif choice == "5":
+        elif choice == "5":
             action_review_tools()
+        elif choice == "6":
+            action_model_manager()
+
+def action_model_manager() -> None:
+    print("\n=== Model Manager ===")
+    print("1) Listar modelos")
+    print("2) Selecionar modelo ativo")
+    print("3) Mostrar modelo ativo")
+    print("4) A/B compare (lado a lado)")
+    print("0) Voltar")
+    choice = input("> ").strip()
+    if choice == "1":
+        os.system("python tools/model_select.py list")
+    elif choice == "2":
+        path = _ask("Caminho do modelo (dir)")
+        os.system(f"python tools/model_select.py set-active --path '{path}'")
+    elif choice == "3":
+        os.system("python tools/model_select.py show-active")
+    elif choice == "4":
+        a = _ask("Modelo A (dir)")
+        b = _ask("Modelo B (dir)")
+        pdf = _ask("Pasta de PDFs", str(DEFAULT_SOURCE_DIR))
+        os.system(f"python tools/ab_compare_cli.py --model-a '{a}' --model-b '{b}' --pdf-dir '{pdf}' --sample 10")
+    input("\nPressione Enter para voltar ao menu...")

*** a/docs/HITL_FEEDBACK_WORKFLOW.md
--- b/docs/HITL_FEEDBACK_WORKFLOW.md
@@
@@
+## Switching the active ST model (after validation)
+
+After evaluating metrics, you can point the extractor to a fine‑tuned model without changing defaults:
+
+```python
+from embeddinggemma_feasibility.config import update_config
+update_config(embed_model_custom_path="embeddinggemma_feasibility/models/st_custom_v1")
+```
+
+Set `None` to revert to the default model. You can also use the upcoming Model Manager UI to list/select models.
+
+
+ docs/MODEL_MANAGEMENT.md
+ -------------------------------------------------
+ # Model Management
+ - List models: `python tools/model_select.py list`
+ - Select active: `python tools/model_select.py set-active --path embeddinggemma_feasibility/models/st_custom_v1`
+ - Show active: `python tools/model_select.py show-active`
+ - A/B compare: `python tools/ab_compare_cli.py --model-a ... --model-b ... --pdf-dir ... --sample 20`
+ Notes: active model preference is stored via `embed_model_custom_path` and does not alter defaults unless set.
```

## Acceptance Criteria
- Model Manager menu exists in `interactive_cli` with list/select/show/compare options.
- `tools/model_select.py list` prints models sorted by recency (mtime) and shows: name/path, size (MB), embedding dim (if available), and any tags from `contract_config.json`.
- `set-active` sets `embed_model_custom_path` or creates/updates a `models/current` symlink (documented) without breaking other flows.
- `ab_compare_cli.py` runs A/B on a sample of documents and writes `datasets/preferences.jsonl`; supports `export-pairs` to produce `st_pairs_pref.jsonl`.
- `docs/HITL_FEEDBACK_WORKFLOW.md` includes a short “switch active model” note.
- `docs/MODEL_MANAGEMENT.md` documents listing/selecting models and A/B flow.

## Minimal Manual Tests
1) Create or copy two ST model dirs under `embeddinggemma_feasibility/models/`.
2) Run `python tools/model_select.py list` and verify metadata ordering and fields.
3) Run `python tools/model_select.py set-active --path <model_dir>` then run the advanced extractor to confirm it loads the custom model.
4) Run A/B compare on 5–10 PDFs; confirm prompts show side‑by‑side values per field and `datasets/preferences.jsonl` is filled.
5) Export pairs and fine‑tune using existing `feedback_cli.py train-st` with the exported dataset; verify model artifact is saved.

## Suggested Commit Message and Branch
- Branch (plan): `plan/21-model-management-and-preference-ui`
- Commit (plan): `docs(pr-plan): PR 21 — model manager, side-by-side preference review, and docs note`
- Branch (impl): `feat/21-model-management-and-preference-ui`

## Checklist
- [x] Objective and Scope are clear and limited.
- [x] Affected files listed.
- [x] Pseudodiff (small/representative) included.
- [x] Acceptance criteria and minimal manual tests.
- [x] Suggested commit message and branch name.
