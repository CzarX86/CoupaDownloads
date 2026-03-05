from src.lib.playwright_manager import PlaywrightManager
from src.lib.config import Config


class _FakeElement:
    def __init__(self, href: str = "", visible: bool = True):
        self._href = href
        self._visible = visible

    def is_visible(self):
        return self._visible

    def get_attribute(self, name: str):
        if name == "href":
            return self._href
        return None


class _FakeLocator:
    def __init__(self, elements):
        self._elements = elements

    def all(self):
        return self._elements


class _FakePage:
    def __init__(self):
        self.goto_calls = []
        self._content = "<html><body>ok</body></html>"
        self._selectors = {}

    def goto(self, url, wait_until=None, timeout=None):
        self.goto_calls.append({"url": url, "wait_until": wait_until, "timeout": timeout})

    def content(self):
        return self._content

    def locator(self, selector):
        return _FakeLocator(self._selectors.get(selector, []))

    class _DownloadCtx:
        def __enter__(self):
            class _DownloadInfo:
                value = type("Download", (), {"suggested_filename": "x.pdf", "save_as": lambda self, p: None})()

            return _DownloadInfo()

        def __exit__(self, exc_type, exc, tb):
            return False

    def expect_download(self, timeout=None):
        return self._DownloadCtx()


def _make_manager_with_page(page):
    manager = PlaywrightManager()
    manager.page = page
    return manager


def test_process_po_uses_order_headers_and_strips_po_prefix(monkeypatch):
    page = _FakePage()
    manager = _make_manager_with_page(page)

    monkeypatch.setattr(
        "src.lib.playwright_manager.FolderHierarchyManager.create_folder_path",
        lambda self, po_data, hierarchy_cols, has_hierarchy: "/tmp/po-folder",
    )
    monkeypatch.setattr(
        "src.lib.playwright_manager.FolderHierarchyManager.finalize_folder",
        lambda self, folder, status: folder,
    )

    manager.process_po("PO123456", {"po_number": "PO123456"}, [], False)

    assert page.goto_calls
    assert page.goto_calls[0]["url"] == f"{Config.BASE_URL}/order_headers/123456"


def test_process_po_uses_base_url_for_pm_prefix(monkeypatch):
    page = _FakePage()
    manager = _make_manager_with_page(page)

    monkeypatch.setattr(
        "src.lib.playwright_manager.FolderHierarchyManager.create_folder_path",
        lambda self, po_data, hierarchy_cols, has_hierarchy: "/tmp/po-folder",
    )
    monkeypatch.setattr(
        "src.lib.playwright_manager.FolderHierarchyManager.finalize_folder",
        lambda self, folder, status: folder,
    )

    manager.process_po("PM987", {"po_number": "PM987"}, [], False)

    assert page.goto_calls
    assert page.goto_calls[0]["url"] == f"{Config.BASE_URL}/order_headers/987"
