"""E2E: column mapping flow for non-standard input files.

A file without PO_NUMBER/SUPPLIER headers must trigger the mapping card on
the input step, allow mapping, and become valid after applying it.
"""

from pathlib import Path

from scripts.repro_mapping_flow import run_mapping_flow


def test_non_standard_input_offers_mapping_and_becomes_valid(tmp_path: Path) -> None:
    result = run_mapping_flow(output_root=tmp_path)

    assert result["page_error_count"] == 0, result["page_errors"]
    assert result["mapping_card_visible"] is True
    assert "Map the file columns" in result["mapping_title"]
    assert "File is valid" in result["feedback_after_mapping"]
    assert result["after_mapping_valid"] is True
    assert result["next_hierarchy_enabled"] is True


def test_mapping_notice_appears_on_input_step_before_validation(tmp_path: Path) -> None:
    result = run_mapping_flow(output_root=tmp_path, check_notice=True)

    assert result["page_error_count"] == 0, result["page_errors"]
    assert result["mapping_notice_visible"] is True
