import os
import sys
import asyncio

import webview

from src.db.session_db import SessionDB
from src.gui.api import AppAPI
from src.engine.authenticator import get_coupa_cookies
from src.engine.benchmarker import benchmark
from src.engine.updater import check_for_update


def resolve_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def get_database_path() -> str:
    user_home = os.path.expanduser("~")
    app_data_dir = os.path.join(user_home, ".coupa_turbo")
    os.makedirs(app_data_dir, exist_ok=True)
    return os.path.join(app_data_dir, "sessions.db")


class TurboAPI(AppAPI):
    """Extended API with authenticator, benchmarker, and updater bridge methods."""

    def authenticate(self) -> dict:
        """Open Edge for Coupa login, return extracted cookies dict."""
        try:
            cookies = asyncio.run(get_coupa_cookies(load_from_file=True))
            return {"success": True, "cookies": cookies}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_benchmark(self, urls: list[str], base_url: str = "https://unilever.coupahost.com") -> dict:
        """Run network benchmark against sample URLs, return optimal params."""
        try:
            cookies = asyncio.run(get_coupa_cookies(load_from_file=True))
            result = asyncio.run(benchmark(urls, cookies=cookies, base_url=base_url))
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_updates(self) -> dict:
        """Check GitHub Releases for newer version."""
        try:
            update_info = asyncio.run(check_for_update())
            if update_info:
                return {"success": True, "update_available": True, **update_info}
            return {"success": True, "update_available": False}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_download(self, session_id: int, download_dir: str, concurrency: int = 11) -> dict:
        return super().start_download(session_id, download_dir, concurrency)


def main():
    db_path = get_database_path()
    db = SessionDB(db_path)

    api = TurboAPI(db, default_download_dir=os.path.expanduser("~/Downloads/CoupaAttachments"))

    html_file = resolve_path(os.path.join("gui", "web", "index.html"))

    window = webview.create_window(
        title="Coupa Turbo Downloader",
        url=html_file,
        js_api=api,
        width=1100,
        height=680,
        resizable=False,
    )

    webview.start(debug=True)
    db.close()


if __name__ == "__main__":
    main()
