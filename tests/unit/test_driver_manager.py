from __future__ import annotations

import threading
import time
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from src.lib.driver_manager import DriverCache, DriverResolutionConfig, DriverResolver


class FakeVersionProvider:
    def __init__(self, edge_version: str | None):
        self.edge_version = edge_version

    def get_edge_version(self) -> str | None:
        return self.edge_version


class FakeValidator:
    def __init__(self):
        self.invalid_paths: set[Path] = set()

    def verify(self, driver_path: Path | str) -> bool:
        path = Path(driver_path)
        return path.exists() and path not in self.invalid_paths

    def is_compatible_with_edge(self, driver_path: Path | str, edge_version: str | None) -> bool:
        if edge_version is None:
            return self.verify(driver_path)
        path = Path(driver_path)
        return self.verify(path) and self.major(path.parent.name) == self.major(edge_version)

    def prepare(self, driver_path: Path | str) -> None:
        return None

    def is_compatible_arch(self, driver_path: Path | str) -> bool:
        return True

    def version_tuple(self, version: str) -> tuple[int, int, int, int]:
        parts = (version.split(".") + ["0", "0", "0", "0"])[:4]
        return tuple(int(part) for part in parts)

    @staticmethod
    def major(version: str) -> int:
        return int(version.split(".")[0])


@dataclass
class FakeDownloader:
    resolved_version: str
    download_calls: int = 0
    resolve_calls: int = 0
    delay_seconds: float = 0.0

    def resolve_driver_version(self, edge_version: str | None) -> str:
        self.resolve_calls += 1
        return self.resolved_version

    def download_and_extract(self, driver_version: str):
        self.download_calls += 1
        temp_dir = Path(tempfile.mkdtemp(prefix=f"driver-download-{self.download_calls}-"))
        driver_name = "msedgedriver"
        staged_driver = temp_dir / driver_name
        staged_driver.write_text(f"driver:{driver_version}", encoding="utf-8")
        if self.delay_seconds:
            time.sleep(self.delay_seconds)

        class _TempDir:
            def cleanup(self_inner):
                for child in temp_dir.iterdir():
                    child.unlink(missing_ok=True)
                temp_dir.rmdir()

        return staged_driver, _TempDir()


def make_resolver(tmp_path: Path, edge_version: str | None, downloader: FakeDownloader, validator: FakeValidator | None = None, **config_overrides):
    validator = validator or FakeValidator()
    config = DriverResolutionConfig(
        explicit_driver_path=config_overrides.get("explicit_driver_path"),
        auto_download=config_overrides.get("auto_download", True),
        cache_enabled=config_overrides.get("cache_enabled", True),
        cache_dir=tmp_path,
        cache_cleanup_enabled=config_overrides.get("cache_cleanup_enabled", True),
    )
    cache = DriverCache("linux64", validator, tmp_path)
    resolver = DriverResolver(
        config=config,
        platform_name="linux64",
        version_provider=FakeVersionProvider(edge_version),
        validator=validator,
        cache=cache,
        downloader=downloader,
    )
    return resolver, cache, validator


def test_resolver_prefers_explicit_driver_path(tmp_path: Path):
    explicit_driver = tmp_path / "manual-driver"
    explicit_driver.write_text("ok", encoding="utf-8")
    downloader = FakeDownloader(resolved_version="145.0.3800.82")
    resolver, _cache, _validator = make_resolver(
        tmp_path / "cache",
        edge_version="145.0.3800.82",
        downloader=downloader,
        explicit_driver_path=explicit_driver,
    )

    resolved = resolver.resolve()

    assert resolved == explicit_driver
    assert downloader.resolve_calls == 0
    assert downloader.download_calls == 0


def test_resolver_reuses_compatible_cached_driver_without_network(tmp_path: Path):
    downloader = FakeDownloader(resolved_version="145.0.3800.82")
    resolver, cache, _validator = make_resolver(tmp_path / "cache", edge_version="145.0.3800.82", downloader=downloader)
    cached_driver = cache.driver_path_for("145.0.3800.82")
    cached_driver.parent.mkdir(parents=True, exist_ok=True)
    cached_driver.write_text("cached", encoding="utf-8")

    resolved = resolver.resolve()

    assert resolved == cached_driver
    assert downloader.resolve_calls == 0
    assert downloader.download_calls == 0


def test_resolver_downloads_and_publishes_when_cache_misses(tmp_path: Path):
    downloader = FakeDownloader(resolved_version="145.0.3800.82")
    resolver, cache, _validator = make_resolver(tmp_path / "cache", edge_version="145.0.3800.82", downloader=downloader)

    resolved = resolver.resolve()

    assert resolved == cache.driver_path_for("145.0.3800.82")
    assert resolved.exists()
    assert downloader.resolve_calls == 1
    assert downloader.download_calls == 1


def test_resolver_replaces_invalid_cached_driver(tmp_path: Path):
    validator = FakeValidator()
    downloader = FakeDownloader(resolved_version="145.0.3800.82")
    resolver, cache, _validator = make_resolver(tmp_path / "cache", edge_version="145.0.3800.82", downloader=downloader, validator=validator)
    cached_driver = cache.driver_path_for("145.0.3800.82")
    cached_driver.parent.mkdir(parents=True, exist_ok=True)
    cached_driver.write_text("bad", encoding="utf-8")
    validator.invalid_paths.add(cached_driver)

    resolved = resolver.resolve()

    assert resolved == cached_driver
    assert cached_driver.exists()
    assert downloader.download_calls == 1


def test_resolver_respects_disabled_auto_download(tmp_path: Path):
    downloader = FakeDownloader(resolved_version="145.0.3800.82")
    resolver, _cache, _validator = make_resolver(
        tmp_path / "cache",
        edge_version="145.0.3800.82",
        downloader=downloader,
        auto_download=False,
    )

    with pytest.raises(RuntimeError, match="DRIVER_AUTO_DOWNLOAD"):
        resolver.resolve()

    assert downloader.resolve_calls == 0
    assert downloader.download_calls == 0


def test_driver_cache_default_root_linux(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg-cache"))
    monkeypatch.setattr("src.lib.driver_manager.platform.system", lambda: "Linux")

    cache_root = DriverCache.default_cache_root()

    assert cache_root == tmp_path / "xdg-cache" / "CoupaDownloads" / "drivers" / "edgedriver"


def test_concurrent_resolve_downloads_only_once(tmp_path: Path):
    downloader = FakeDownloader(resolved_version="145.0.3800.82", delay_seconds=0.2)
    resolver, cache, _validator = make_resolver(tmp_path / "cache", edge_version="145.0.3800.82", downloader=downloader)
    results: list[Path] = []

    def worker():
        results.append(resolver.resolve())

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert downloader.download_calls == 1
    assert len(results) == 2
    assert all(path == cache.driver_path_for("145.0.3800.82") for path in results)
