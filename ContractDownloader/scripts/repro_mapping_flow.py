"""Playwright reproduction of the column-mapping flow with a non-standard file.

Shared by the e2e test suite (tests/e2e/test_gui_mapping_flow.py) and usable
standalone for debugging:
    uv run python scripts/repro_mapping_flow.py
"""

import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright

from scripts.gui_playwright_debug import RealBridge, start_server

INIT_BRIDGE_SCRIPT = """
window.pywebview = { api: new Proxy({}, { get: (t, name) => (...args) => window.__pw_api_call(name, args) }) };
window.addEventListener('pywebviewready', () => window.dispatchEvent(new Event('pywebviewready')));
"""

NON_STANDARD_CSV = (
    "Document;Vendor Name;Region\n"
    "PO111;Acme Corp;BR\n"
    "PO222;Globex;US\n"
)


def run_mapping_flow(
    output_root: Path | None = None,
    check_notice: bool = False,
    timeout_ms: int = 15000,
) -> dict[str, Any]:
    """Drive the mapping journey and report what the page shows."""
    repo_root = Path(__file__).resolve().parents[1]
    web_root = repo_root / "src" / "gui" / "web"
    evidence_root = output_root or (repo_root / "artifacts" / "gui-playwright")
    run_dir = evidence_root / "mapping_flow"
    run_dir.mkdir(parents=True, exist_ok=True)

    bridge = RealBridge(run_dir=run_dir)
    non_standard = run_dir / "master_data.csv"
    non_standard.write_text(NON_STANDARD_CSV, encoding="utf-8")

    server, _thread = start_server(web_root)
    base_url = f"http://127.0.0.1:{server.server_port}/index.html"

    page_errors: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(timeout_ms)
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.on("dialog", lambda dialog: dialog.accept())
            page.expose_function("__pw_api_call", lambda method, args: bridge.call(method, args))
            page.add_init_script(INIT_BRIDGE_SCRIPT)
            page.goto(base_url, wait_until="domcontentloaded")
            page.wait_for_timeout(600)

            page.locator("#file-input").set_input_files(str(non_standard))
            page.wait_for_timeout(900)

            notice_visible = page.locator("#mapping-notice").is_visible()
            if notice_visible:
                page.screenshot(path=str(run_dir / "01_mapping_notice.png"), full_page=True)
                # The notice button must take the user straight to mapping.
                page.click("#btn-map-columns")
                page.wait_for_selector("#column-mapping-card:not([hidden])", timeout=8000)
                page.wait_for_timeout(400)
            else:
                page.click("#btn-next-input")
                page.wait_for_selector("#validation-feedback:not([hidden])", timeout=8000)
                page.wait_for_timeout(400)

            mapping_card_visible = page.locator("#column-mapping-card").is_visible()
            mapping_title = page.locator("#mapping-title").inner_text() if mapping_card_visible else "(hidden)"
            feedback = page.locator("#validation-feedback").inner_text()

            after_mapping_valid = False
            feedback_after_mapping = ""
            next_hierarchy_enabled = False
            if mapping_card_visible:
                page.select_option("#mapping-po-select", "Document")
                page.select_option("#mapping-supplier-select", "Vendor Name")
                page.click("#btn-apply-mapping")
                page.wait_for_timeout(1500)
                feedback_after_mapping = page.locator("#validation-feedback").inner_text()
                after_mapping_valid = page.locator(".validation-success").count() > 0
                next_hierarchy_enabled = page.locator("#btn-next-hierarchy").is_enabled()
                page.screenshot(path=str(run_dir / "02_mapping_applied.png"), full_page=True)

            browser.close()
            return {
                "page_error_count": len(page_errors),
                "page_errors": page_errors,
                "mapping_notice_visible": notice_visible,
                "mapping_card_visible": mapping_card_visible,
                "mapping_title": mapping_title,
                "feedback": feedback,
                "feedback_after_mapping": feedback_after_mapping,
                "after_mapping_valid": after_mapping_valid,
                "next_hierarchy_enabled": next_hierarchy_enabled,
            }
    finally:
        server.shutdown()


def main() -> int:
    result = run_mapping_flow()
    print("PAGE_ERRORS:", result["page_errors"])
    print("NOTICE_VISIBLE:", result["mapping_notice_visible"])
    print("CARD_VISIBLE:", result["mapping_card_visible"])
    print("TITLE:", result["mapping_title"])
    print("VALID_AFTER_MAPPING:", result["after_mapping_valid"])
    print("NEXT_HIERARCHY_ENABLED:", result["next_hierarchy_enabled"])
    return 0 if result["page_error_count"] == 0 and result["after_mapping_valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
