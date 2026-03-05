import warnings

from src.lib import downloader as dl_mod


class _FakeAttachment:
    def __init__(self):
        self.clicked = 0

    def click(self):
        self.clicked += 1


def test_downloader_uses_page_delay_without_attr_errors(monkeypatch):
    # Silence deprecation noise from Config shim
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        delay = getattr(dl_mod.Config, "PAGE_DELAY")

    sleeps = []
    monkeypatch.setattr(dl_mod.time, "sleep", lambda s: sleeps.append(s))

    attachment = _FakeAttachment()
    d = dl_mod.Downloader(driver=None, browser_manager=None)

    success, err = d._download_attachment(attachment, "file.pdf")

    assert success is True
    assert err is None
    assert attachment.clicked == 1
    assert sleeps and sleeps[0] == delay
