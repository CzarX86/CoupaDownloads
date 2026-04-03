from src.workers.browser_session import BrowserSession
from src.workers.models import PoolConfig, Profile
from src.workers.worker_process import WorkerProcess


class _DriverStub:
    def __init__(self):
        self.current_window_handle = "main"

    def execute_cdp_cmd(self, *_args, **_kwargs):
        return None


def test_worker_process_uses_modern_headless_flag(tmp_path, monkeypatch):
    base_profile = tmp_path / "base-profile"
    worker_profile = tmp_path / "worker-profile"
    downloads = tmp_path / "downloads"
    base_profile.mkdir()
    worker_profile.mkdir()
    downloads.mkdir()

    process = WorkerProcess(
        worker_id="worker-1",
        profile=Profile(
            base_profile_path=str(base_profile),
            worker_profile_path=str(worker_profile),
            worker_id="worker-1",
        ),
        config=PoolConfig(
            worker_count=1,
            autoscaling_enabled=False,
            base_profile_path=str(base_profile),
            download_root=str(downloads),
            profile_cleanup_on_shutdown=False,
            headless_mode=True,
        ),
    )
    process.browser_session = BrowserSession()

    recorded = {}

    class _DriverManagerStub:
        def get_driver_path(self):
            return "/tmp/msedgedriver"

        def verify_driver(self, _path):
            return True

    def _edge_factory(*, service, options):
        recorded["arguments"] = list(getattr(options, "arguments", []))
        return _DriverStub()

    monkeypatch.setattr("src.workers.worker_process.DriverManager", _DriverManagerStub)
    monkeypatch.setattr("selenium.webdriver.Edge", _edge_factory)
    monkeypatch.setattr("src.workers.worker_process.time.sleep", lambda _seconds: None)
    monkeypatch.setattr(process.browser_session, "ensure_keeper_tab", lambda: True)
    monkeypatch.setattr(process.browser_session, "authenticate", lambda: True)
    monkeypatch.setattr(process.browser_session, "trim_to_single_tab", lambda preferred_handle=None: True)

    process._initialize_selenium_session()

    assert "--headless=new" in recorded["arguments"]
    assert "--headless" not in recorded["arguments"]
