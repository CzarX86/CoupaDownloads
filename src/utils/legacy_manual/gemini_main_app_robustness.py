#!/usr/bin/env python3
"""Legacy notes for the removed ``MainApp`` robustness tests.

The original tests in :mod:`src.utils.GeminiTests.test_main_app_robustness`
mocked the deprecated ``MainApp`` class that lived in ``src/main.py``. The
orchestration logic was replaced by :mod:`src.Core_main` and the helper class
was deleted, which caused import errors whenever pytest tried to load the
module.

The previous assertions are kept in git history for reference. If we ever
reintroduce a high-level orchestrator, start by modelling the scenarios listed
below and port them to the new entry point instead of reviving the old
``MainApp`` API.
"""

LEGACY_SCENARIOS = [
    "Happy-path download loop with mocked Excel data",
    "Downloader returning an error and surfacing it to the status tracker",
    "InvalidSessionIdException/NoSuchWindowException recovery flow",
]
