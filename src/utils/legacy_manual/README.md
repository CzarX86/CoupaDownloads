# Legacy manual utilities

This folder houses the old "test" scripts that previously lived under
`src/utils/` and `src/utils/GeminiTests/`. They interacted with the browser or
depended on the deprecated `MainApp` class, which made the automated pytest
suite fail. The files were kept for troubleshooting purposes only and were
updated to reference the modern `src.core` modules where applicable.

None of the scripts in this directory are executed automatically. Run them
manually from the repository root, for example:

```bash
python -m src.utils.legacy_manual.manual_single_po --po PO123456
python -m src.utils.legacy_manual.manual_po16518898 --po PO16518898 --download-dir /tmp/po-test
```

The legacy Gemini robustness scenarios (`gemini_main_app_robustness.py`) now
document the behaviours that were originally covered. Should a new top-level
orchestrator emerge, port those scenarios to the fresh architecture instead of
reviving the old `MainApp` API.
