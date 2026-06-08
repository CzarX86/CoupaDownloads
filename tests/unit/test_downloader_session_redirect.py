from src.core.exceptions import SessionExpiredError
from src.lib.downloader import Downloader


class _DriverStub:
    def __init__(self):
        self.current_url = "https://unilever.coupahost.com/sessions/new"

    def get(self, _url: str) -> None:
        return None


class _BrowserManagerStub:
    def update_download_directory(self, _path: str) -> None:
        return None


def test_downloader_escalates_session_redirect_instead_of_po_not_found(monkeypatch):
    downloader = Downloader(driver=_DriverStub(), browser_manager=_BrowserManagerStub())

    monkeypatch.setattr(
        downloader,
        "_detect_error_page",
        lambda _phase, timeout=None: {"marker": "Oops!", "phase": "early", "source": "body", "elapsed": 0.03},
    )

    try:
        downloader.download_attachments_for_po("PO123")
        assert False, "Expected SessionExpiredError for session redirect URL"
    except SessionExpiredError:
        pass
