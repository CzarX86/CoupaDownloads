from src.ui.textual_ui_app import FinalSummaryPanel


def test_final_summary_text_marks_completed_run_without_active_downloads() -> None:
    text = FinalSummaryPanel.build_summary_text(
        "completed",
        {
            "processed": 5,
            "successful": 4,
            "failed": 1,
            "duration_seconds": 125,
            "download_root": "/tmp/coupa",
            "msg_files_available": 2,
            "report_available": True,
            "worker_count": 3,
            "post_process": {
                "stage": "done",
                "status_message": "Automatic post-processing completed.",
                "msg_conversion": {"executed": True, "converted": 2, "skipped": 0, "failed": 0},
                "report_path": "/tmp/coupa/report.xlsx",
            },
        },
    )

    assert "COMPLETED" in text
    assert "No downloads in progress." in text
    assert "Processed: [bold]5" in text
    assert "Automatic post-processing completed." in text
    assert "MSG to PDF" in text
    assert "/tmp/coupa/report.xlsx" in text


def test_final_summary_text_shows_failed_message_when_present() -> None:
    text = FinalSummaryPanel.build_summary_text(
        "failed",
        {
            "processed": 2,
            "successful": 1,
            "failed": 1,
            "duration_seconds": 20,
            "download_root": "/tmp/coupa",
            "msg_files_available": 0,
            "report_available": False,
            "worker_count": 1,
            "error": "cleanup timeout",
        },
    )

    assert "FAILED" in text
    assert "cleanup timeout" in text
