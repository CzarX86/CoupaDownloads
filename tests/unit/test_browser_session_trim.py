from src.workers.browser_session import BrowserSession


class _SwitchToStub:
    def __init__(self, driver):
        self._driver = driver

    def window(self, handle):
        if handle not in self._driver.window_handles:
            raise RuntimeError(f"Unknown handle: {handle}")
        self._driver._current_handle = handle


class _DriverStub:
    def __init__(self, handles, current_handle):
        self._handles = list(handles)
        self._current_handle = current_handle
        self.switch_to = _SwitchToStub(self)

    @property
    def window_handles(self):
        return list(self._handles)

    @property
    def current_window_handle(self):
        return self._current_handle

    def close(self):
        self._handles.remove(self._current_handle)
        if self._handles:
            self._current_handle = self._handles[0]


def test_browser_session_collapses_restored_tabs_to_single_keeper():
    session = BrowserSession()
    session.driver = _DriverStub(
        handles=["restored-1", "restored-2", "restored-3"],
        current_handle="restored-2",
    )
    session.main_window_handle = "restored-2"
    session.keeper_handle = "restored-2"
    session.active_tabs = {"task-1": object()}

    collapsed = session.trim_to_single_tab(preferred_handle="restored-2")

    assert collapsed is True
    assert session.driver.window_handles == ["restored-2"]
    assert session.driver.current_window_handle == "restored-2"
    assert session.main_window_handle == "restored-2"
    assert session.keeper_handle == "restored-2"
    assert session.active_tabs == {}
