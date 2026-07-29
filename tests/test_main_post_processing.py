from src.main import (
    MainApp,
    POST_PROCESS_ACTION_ALL,
    POST_PROCESS_ACTION_QUIT,
    POST_PROCESS_ACTION_REPORT,
)


def test_post_processing_action_all_runs_conversion_before_report() -> None:
    app = MainApp.__new__(MainApp)
    calls = []

    app._execute_msg_conversion = lambda: calls.append("convert") or {"converted": 1}
    app._execute_final_report = lambda: calls.append("report") or "/tmp/report.xlsx"

    outcome = MainApp._execute_post_processing_action(app, POST_PROCESS_ACTION_ALL)

    assert calls == ["convert", "report"]
    assert outcome["action"] == POST_PROCESS_ACTION_ALL


def test_post_processing_action_quit_does_nothing() -> None:
    app = MainApp.__new__(MainApp)
    calls = []

    app._execute_msg_conversion = lambda: calls.append("convert")
    app._execute_final_report = lambda: calls.append("report")

    outcome = MainApp._execute_post_processing_action(app, POST_PROCESS_ACTION_QUIT)

    assert calls == []
    assert outcome["msg_conversion"] is None
    assert outcome["report_path"] is None


def test_report_action_uses_non_interactive_executor() -> None:
    app = MainApp.__new__(MainApp)
    calls = []

    app._execute_msg_conversion = lambda: calls.append("convert")
    app._execute_final_report = lambda: calls.append("report") or "/tmp/report.xlsx"

    outcome = MainApp._execute_post_processing_action(app, POST_PROCESS_ACTION_REPORT)

    assert calls == ["report"]
    assert outcome["report_path"] == "/tmp/report.xlsx"


def test_automatic_post_processing_runs_both_steps() -> None:
    app = MainApp.__new__(MainApp)
    calls = []

    app._execute_msg_conversion = lambda: calls.append("convert") or {"converted": 1}
    app._execute_final_report = lambda: calls.append("report") or "/tmp/report.xlsx"

    outcome = MainApp._execute_post_processing_action(app, POST_PROCESS_ACTION_ALL)

    assert calls == ["convert", "report"]
    assert outcome["msg_conversion"]["converted"] == 1
    assert outcome["report_path"] == "/tmp/report.xlsx"
