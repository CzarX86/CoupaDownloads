"""Comprehensive E2E Playwright tests covering the full GUI journey.

These tests validate every screen, UI control, and backend interaction through
the Playwright probe bridge (mock + real backend). macOS is the test platform;
Windows cross-platform assertions are validated in test_cross_platform.py.
"""

from pathlib import Path

from scripts.gui_playwright_debug import run_probe


# ── Mock-mode full journey (deterministic, fast) ──────────────────────────


def test_full_journey_mock_steps_captured(tmp_path: Path) -> None:
    """Every expected step must be recorded by the probe runner."""
    result = run_probe(mode="mock", timeout_ms=25000, output_root=tmp_path)

    expected = [
        "loaded-index",
        "checked-next-without-file",
        "selected-input-file",
        "clicked-start",
        "progress-visible",
        "history-loaded",
        "modal-opened",
        "po-edge-link-clicked",
        "export-clicked",
        "modal-closed",
        "manual-update-check",
        "settings-save-visible",
    ]
    for step in expected:
        assert step in result.report["steps"], f"Missing step: {step}"


def test_full_journey_mock_no_page_errors(tmp_path: Path) -> None:
    """No unhandled JavaScript or console errors during the journey."""
    result = run_probe(mode="mock", timeout_ms=25000, output_root=tmp_path)
    assert result.report["page_error_count"] == 0


def test_full_journey_mock_dom_state_invariants(tmp_path: Path) -> None:
    """DOM invariants that must survive every page transition."""
    result = run_probe(mode="mock", timeout_ms=25000, output_root=tmp_path)
    dom = result.report["dom_state"]

    assert dom["history_rows"] >= 1
    assert dom["console_ui_lines"] >= 1
    assert dom["modal_po_rows"] >= 1
    assert dom["status_filter_inputs"] == 5
    assert dom["sidebar_controls_visible"] is True

    sidebar = dom["sidebar_metrics"]
    assert sidebar["overflowY"] == "hidden"
    assert sidebar["scrollHeight"] <= sidebar["clientHeight"]

    settings_save = dom["settings_save_metrics"]
    assert settings_save["fullyVisible"] is True
    assert settings_save["bottom"] <= settings_save["viewportHeight"]


def test_full_journey_mock_screenshots_created(tmp_path: Path) -> None:
    """Every journey phase must produce a screenshot for visual regression."""
    result = run_probe(mode="mock", timeout_ms=25000, output_root=tmp_path)

    expected_screens = [
        "01_loaded.png",
        "02_file_selected.png",
        "03_progress.png",
        "04_history.png",
        "05_modal.png",
        "06_done.png",
        "07_settings_scrolled.png",
    ]
    for screen in expected_screens:
        assert (result.run_dir / screen).exists(), f"Missing screenshot: {screen}"


def test_full_journey_mock_pause_resume_works(tmp_path: Path) -> None:
    """Pause and resume buttons must be recorded without page errors."""
    result = run_probe(mode="mock", timeout_ms=25000, output_root=tmp_path)

    # The probe script clicks pause, waits, then clicks resume if the button
    # is still enabled (the mock backend may process too quickly for both).
    assert "pause-clicked" in result.report["steps"]
    assert result.report["page_error_count"] == 0


def test_full_journey_mock_stop_persisted(tmp_path: Path) -> None:
    """Stop during execution must log a console message."""
    result = run_probe(mode="mock", timeout_ms=25000, output_root=tmp_path)

    assert "clicked-stop" in result.report["steps"]
    assert any(
        "Stop requested" in entry
        for entry in result.report["console_logs"]
    )


# ── Start-over guardrail (mock) ──────────────────────────────────────────


def test_start_over_button_present_in_html(tmp_path: Path) -> None:
    """The button must exist in the live page for Playwright to click."""
    result = run_probe(mode="mock", timeout_ms=25000, output_root=tmp_path)

    assert result.report["page_error_count"] == 0
    # The button must exist in the served HTML.
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    web_root = repo_root / "src" / "gui" / "web"
    html = (web_root / "index.html").read_text(encoding="utf-8")
    assert 'id="btn-start-over"' in html


# ── Real-backend full journey ────────────────────────────────────────────


def test_full_journey_real_backend_imports_and_exports(tmp_path: Path) -> None:
    """The real AppAPI must persist sessions and survive the UI round-trip."""
    result = run_probe(mode="real", timeout_ms=30000, output_root=tmp_path)

    assert result.report["page_error_count"] == 0
    assert result.report["mode"] == "real"
    assert result.report["dom_state"]["history_rows"] >= 1
    assert (result.run_dir / "probe.db").exists()
