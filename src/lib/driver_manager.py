"""EdgeDriver resolution backed by a persistent per-user cache.

Automatic resolution follows this policy:
1. Use ``EDGE_DRIVER_PATH`` when explicitly configured and valid.
2. Reuse a compatible driver from the user cache.
3. Download, validate, and atomically publish a compatible driver to the cache.

The cache lives outside the repository so it persists between executions and can
be safely reused by sequential and parallel workers.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

import requests
from requests.adapters import HTTPAdapter


@dataclass(frozen=True)
class DriverResolutionConfig:
    """Runtime configuration used by the driver resolver."""

    explicit_driver_path: Optional[Path]
    auto_download: bool
    cache_enabled: bool
    cache_dir: Optional[Path]
    cache_cleanup_enabled: bool


class EdgePlatform:
    """Detect the current OS/platform tuple used by EdgeDriver releases."""

    @staticmethod
    def current() -> str:
        system = platform.system().lower()
        machine = platform.machine().lower()

        if system == "windows":
            return "win64"
        if system == "darwin":
            return "mac64_m1" if "arm" in machine or "aarch64" in machine else "mac64"
        if system == "linux":
            return "linux64"
        raise OSError(f"Unsupported platform: {system} {machine}")


class EdgeVersionProvider:
    """Resolve the installed Microsoft Edge version for the host system."""

    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    def get_edge_version(self) -> Optional[str]:
        try:
            if self.platform_name == "win64":
                return self._get_edge_version_windows()
            if self.platform_name.startswith("mac"):
                return self._get_edge_version_macos()
            if self.platform_name == "linux64":
                return self._get_edge_version_linux()
        except Exception as exc:
            print(f"⚠️ Warning: Could not detect Edge version: {exc}")
        return None

    def _get_edge_version_windows(self) -> Optional[str]:
        commands = [
            ["powershell", "-Command", "(Get-AppxPackage Microsoft.MicrosoftEdge.Stable).Version"],
            ["reg", "query", r"HKEY_CURRENT_USER\Software\Microsoft\Edge\BLBeacon", "/v", "version"],
        ]
        for command in commands:
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
            except Exception:
                continue
            if result.returncode != 0:
                continue
            match = re.search(r"([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", result.stdout)
            if match:
                return match.group(1)
        return None

    def _get_edge_version_macos(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception:
            return None
        if result.returncode != 0:
            return None
        match = re.search(r"Microsoft Edge\s+([0-9.]+)", result.stdout)
        return match.group(1) if match else None

    def _get_edge_version_linux(self) -> Optional[str]:
        paths = [
            "/usr/bin/microsoft-edge",
            "/usr/bin/microsoft-edge-stable",
            "/opt/microsoft/msedge/microsoft-edge",
        ]
        for binary in paths:
            if not os.path.exists(binary):
                continue
            try:
                result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=10, check=False)
            except Exception:
                continue
            if result.returncode != 0:
                continue
            match = re.search(r"Microsoft Edge\s+([0-9.]+)", result.stdout)
            if match:
                return match.group(1)
        return None


class DriverValidator:
    """Validate downloaded or cached EdgeDriver binaries."""

    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    def verify(self, driver_path: Path | str) -> bool:
        path = Path(driver_path)
        if not path.exists():
            print(f"❌ Verification failed: Driver not found at {path}")
            return False
        try:
            self.prepare(path)
            result = subprocess.run([str(path), "--version"], capture_output=True, text=True, timeout=10)
        except Exception as exc:
            print(f"❌ EdgeDriver verification error: {exc}")
            return False

        if result.returncode == 0 and "Edge" in result.stdout:
            print(f"✅ EdgeDriver verification successful: {result.stdout.strip()}")
            return True

        print(f"❌ EdgeDriver verification failed. stderr: {result.stderr.strip()}")
        return False

    def get_driver_version(self, driver_path: Path | str) -> Optional[str]:
        path = Path(driver_path)
        try:
            result = subprocess.run([str(path), "--version"], capture_output=True, text=True, timeout=8)
        except Exception:
            return None
        if result.returncode != 0:
            return None
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)", result.stdout)
        return match.group(1) if match else None

    def is_compatible_with_edge(self, driver_path: Path | str, edge_version: Optional[str]) -> bool:
        if edge_version is None:
            return self.verify(driver_path)
        driver_version = self.get_driver_version(driver_path)
        if not driver_version:
            return False
        return self.major(driver_version) == self.major(edge_version)

    def prepare(self, driver_path: Path | str) -> None:
        path = Path(driver_path)
        if self.platform_name != "win64":
            try:
                path.chmod(path.stat().st_mode | 0o111)
            except Exception:
                pass
            if self._is_macos():
                try:
                    subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(path)], capture_output=True, check=False)
                except Exception:
                    pass

    def is_compatible_arch(self, driver_path: Path | str) -> bool:
        path = Path(driver_path)
        system = platform.system().lower()
        machine = platform.machine().lower()
        try:
            if system == "windows":
                return True
            if system == "darwin":
                want = "arm64" if ("arm" in machine or "aarch64" in machine) else "x86_64"
                for command in (["lipo", "-info", str(path)], ["file", "-b", str(path)]):
                    try:
                        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
                    except Exception:
                        continue
                    if result.returncode != 0:
                        continue
                    output = result.stdout.lower()
                    if want == "arm64":
                        return "arm64" in output or "aarch64" in output
                    return "x86_64" in output or "x86-64" in output or "intel" in output
                return True
            if system == "linux":
                try:
                    result = subprocess.run(["file", "-b", str(path)], capture_output=True, text=True, timeout=5)
                except Exception:
                    return True
                if result.returncode != 0:
                    return True
                output = result.stdout.lower()
                if "x86_64" in machine or "amd64" in machine:
                    return "x86-64" in output or "x86_64" in output
                if "aarch64" in machine or "arm64" in machine:
                    return "aarch64" in output or "arm64" in output
                return True
        except Exception:
            return True
        return True

    @staticmethod
    def major(version: str) -> int:
        try:
            return int(version.split(".")[0])
        except Exception:
            return -1

    @staticmethod
    def is_version_string(value: str) -> bool:
        return bool(re.match(r"^\d+\.\d+\.\d+\.\d+$", value))

    @staticmethod
    def version_tuple(version: str) -> tuple[int, int, int, int]:
        parts = (version.split(".") + ["0", "0", "0", "0"])[:4]
        return tuple(int(part) for part in parts)  # type: ignore[return-value]

    def _is_macos(self) -> bool:
        return self.platform_name.startswith("mac") or platform.system().lower() == "darwin"


class DriverDownloader:
    """Download and extract EdgeDriver archives into temporary staging areas."""

    EDGEDRIVER_BASE_URL = "https://msedgedriver.microsoft.com"

    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    def resolve_driver_version(self, edge_version: Optional[str]) -> str:
        if edge_version:
            major_version = edge_version.split(".")[0]
            preferred_url = f"{self.EDGEDRIVER_BASE_URL}/LATEST_RELEASE_{major_version}"
            try:
                response = requests.get(preferred_url, timeout=10)
                response.raise_for_status()
                driver_version = response.text.strip()
                if DriverValidator.is_version_string(driver_version):
                    print(f"🔧 Found compatible driver version online: {driver_version}")
                    return driver_version
                raise ValueError("Could not parse driver version from response.")
            except Exception as exc:
                print(f"⚠️ Warning: Could not get compatible driver version: {exc}. Falling back to latest stable.")
        stable_url = f"{self.EDGEDRIVER_BASE_URL}/LATEST_STABLE"
        response = requests.get(stable_url, timeout=10)
        response.raise_for_status()
        driver_version = response.text.strip()
        if not DriverValidator.is_version_string(driver_version):
            raise ValueError(f"Unexpected EdgeDriver version response: {driver_version!r}")
        print(f"🔧 Using latest stable EdgeDriver version: {driver_version}")
        return driver_version

    def download_and_extract(self, driver_version: str) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
        temp_dir = tempfile.TemporaryDirectory(prefix="coupa_edgedriver_")
        temp_path = Path(temp_dir.name)
        zip_name = f"edgedriver_{self.platform_name}.zip"
        archive_path = temp_path / f"edgedriver_{self.platform_name}_{driver_version}.zip"
        download_url = f"{self.EDGEDRIVER_BASE_URL}/{driver_version}/{zip_name}"

        session = requests.Session()
        adapter = HTTPAdapter(pool_connections=5, pool_maxsize=5)
        session.mount("https://", adapter)

        print(f"📥 Downloading EdgeDriver from: {download_url}")
        response = session.get(download_url, stream=True, timeout=60)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))

        with archive_path.open("wb") as handle:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                handle.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    print(f"\r📥 Download progress: {progress:.1f}%", end="", flush=True)
        if total_size > 0:
            print()

        extracted_driver = self.extract_driver(archive_path)
        print(f"✅ EdgeDriver downloaded successfully (staging): {archive_path}")
        return extracted_driver, temp_dir

    def extract_driver(self, archive_path: Path) -> Path:
        driver_name = "msedgedriver.exe" if self.platform_name == "win64" else "msedgedriver"
        extract_dir = archive_path.parent
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_infos = zip_ref.infolist()
            driver_entry = next((info for info in zip_infos if driver_name == Path(info.filename).name), None)
            if driver_entry is None:
                raise FileNotFoundError(f"{driver_name!r} not found in the zip file.")
            driver_path = extract_dir / driver_name
            with zip_ref.open(driver_entry) as source, driver_path.open("wb") as target:
                shutil.copyfileobj(source, target)
        if self.platform_name != "win64":
            driver_path.chmod(0o755)
        print(f"✅ EdgeDriver extracted to staging: {driver_path}")
        return driver_path


class DriverCache:
    """Persistent cache for validated EdgeDriver binaries."""

    def __init__(self, platform_name: str, validator: DriverValidator, cache_dir: Optional[Path] = None):
        self.platform_name = platform_name
        self.validator = validator
        self.root = (cache_dir.expanduser() if cache_dir else self.default_cache_root()).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def default_cache_root() -> Path:
        home = Path.home()
        system = platform.system().lower()
        if system == "darwin":
            return home / "Library" / "Caches" / "CoupaDownloads" / "drivers" / "edgedriver"
        if system == "windows":
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                return Path(local_appdata) / "CoupaDownloads" / "drivers" / "edgedriver"
            return home / "AppData" / "Local" / "CoupaDownloads" / "drivers" / "edgedriver"
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache_home:
            return Path(xdg_cache_home) / "CoupaDownloads" / "drivers" / "edgedriver"
        return home / ".cache" / "CoupaDownloads" / "drivers" / "edgedriver"

    def driver_path_for(self, driver_version: str) -> Path:
        filename = "msedgedriver.exe" if self.platform_name == "win64" else "msedgedriver"
        return self.root / self.platform_name / driver_version / filename

    def get_cached_driver(self, driver_version: str) -> Optional[Path]:
        path = self.driver_path_for(driver_version)
        if path.exists():
            return path
        return None

    def find_compatible_driver(self, edge_version: Optional[str]) -> Optional[Path]:
        platform_dir = self.root / self.platform_name
        if not platform_dir.exists():
            return None

        candidates: list[tuple[tuple[int, int, int, int], Path]] = []
        for version_dir in platform_dir.iterdir():
            if not version_dir.is_dir() or not DriverValidator.is_version_string(version_dir.name):
                continue
            driver_path = self.driver_path_for(version_dir.name)
            if not driver_path.exists():
                continue
            if edge_version and not self.validator.is_compatible_with_edge(driver_path, edge_version):
                continue
            candidates.append((self.validator.version_tuple(version_dir.name), driver_path))

        if not candidates:
            return None

        candidates.sort(reverse=True)
        return candidates[0][1]

    def remove_entry(self, driver_version: str) -> None:
        version_dir = self.driver_path_for(driver_version).parent
        if version_dir.exists():
            shutil.rmtree(version_dir, ignore_errors=True)

    def publish(self, driver_version: str, staged_driver_path: Path) -> Path:
        target_path = self.driver_path_for(driver_version)
        target_dir = target_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        temp_publish_path = target_dir / f".{target_path.name}.tmp"
        shutil.copy2(staged_driver_path, temp_publish_path)
        if self.platform_name != "win64":
            temp_publish_path.chmod(0o755)
        os.replace(temp_publish_path, target_path)
        return target_path

    def cleanup(self, current_version: str, keep_latest: int = 2) -> None:
        platform_dir = self.root / self.platform_name
        if not platform_dir.exists():
            return
        version_dirs = [path for path in platform_dir.iterdir() if path.is_dir() and DriverValidator.is_version_string(path.name)]
        version_dirs.sort(key=lambda path: self.validator.version_tuple(path.name), reverse=True)
        keep = {current_version}
        for path in version_dirs:
            if len(keep) >= keep_latest:
                break
            keep.add(path.name)
        for path in version_dirs:
            if path.name not in keep:
                shutil.rmtree(path, ignore_errors=True)

    @contextmanager
    def acquire_version_lock(self, driver_version: str, timeout_seconds: float = 120.0, stale_seconds: float = 300.0) -> Iterator[None]:
        lock_path = self.driver_path_for(driver_version).parent / ".lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + timeout_seconds
        while True:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(str(os.getpid()))
                break
            except FileExistsError:
                try:
                    age = time.time() - lock_path.stat().st_mtime
                except FileNotFoundError:
                    continue
                if age > stale_seconds:
                    try:
                        lock_path.unlink()
                    except FileNotFoundError:
                        continue
                    continue
                if time.time() >= deadline:
                    raise TimeoutError(f"Timed out waiting for driver cache lock: {lock_path}")
                print(f"⏳ Waiting for EdgeDriver cache lock: {lock_path}")
                time.sleep(0.25)
        try:
            yield
        finally:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass


class DriverResolver:
    """Orchestrate override, cache lookup, download, and publication."""

    def __init__(
        self,
        config: DriverResolutionConfig,
        platform_name: str,
        version_provider: EdgeVersionProvider,
        validator: DriverValidator,
        cache: DriverCache,
        downloader: DriverDownloader,
    ):
        self.config = config
        self.platform_name = platform_name
        self.version_provider = version_provider
        self.validator = validator
        self.cache = cache
        self.downloader = downloader

    def resolve(self) -> Path:
        explicit_driver_path = self.config.explicit_driver_path
        if explicit_driver_path:
            explicit_driver_path = explicit_driver_path.expanduser()
            if explicit_driver_path.exists() and self.validator.verify(explicit_driver_path):
                print(f"✅ Using driver from EDGE_DRIVER_PATH: {explicit_driver_path}")
                return explicit_driver_path
            print("⚠️ EDGE_DRIVER_PATH provided but invalid; ignoring.")

        edge_version = self.version_provider.get_edge_version()

        if self.config.cache_enabled:
            cached_path = self.cache.find_compatible_driver(edge_version)
            if cached_path and self.validator.verify(cached_path):
                print(f"✅ Reusing cached EdgeDriver: {cached_path}")
                return cached_path
            if cached_path:
                print(f"⚠️ Cached EdgeDriver invalid. Removing: {cached_path}")
                self.cache.remove_entry(cached_path.parent.name)

        if not self.config.auto_download:
            raise RuntimeError(
                "No compatible cached EdgeDriver found and DRIVER_AUTO_DOWNLOAD is disabled. "
                "Set EDGE_DRIVER_PATH or re-enable automatic downloads."
            )

        driver_version = self.downloader.resolve_driver_version(edge_version)

        with self.cache.acquire_version_lock(driver_version):
            if self.config.cache_enabled:
                cached_path = self.cache.get_cached_driver(driver_version)
                if cached_path and self.validator.verify(cached_path):
                    print(f"✅ Reusing cached EdgeDriver after lock wait: {cached_path}")
                    return cached_path
                if cached_path:
                    self.cache.remove_entry(driver_version)

            staged_driver_path, temp_dir = self.downloader.download_and_extract(driver_version)
            try:
                self.validator.prepare(staged_driver_path)
                if not self.validator.is_compatible_arch(staged_driver_path):
                    raise RuntimeError(f"Downloaded EdgeDriver has incompatible architecture: {staged_driver_path}")
                if not self.validator.verify(staged_driver_path):
                    raise RuntimeError("Downloaded EdgeDriver failed verification.")
                published_path = self.cache.publish(driver_version, staged_driver_path)
            finally:
                temp_dir.cleanup()

        print(f"✅ Cached EdgeDriver for reuse: {published_path}")
        if self.config.cache_cleanup_enabled:
            self.cache.cleanup(current_version=driver_version)
        return published_path


class DriverManager:
    """Compatibility facade used by worker startup code."""

    def __init__(self):
        from ..config.app_config import Config as RuntimeConfig  # local import avoids cycles

        self.platform = EdgePlatform.current()
        self.config = DriverResolutionConfig(
            explicit_driver_path=getattr(RuntimeConfig, "EDGE_DRIVER_PATH", None),
            auto_download=bool(getattr(RuntimeConfig, "DRIVER_AUTO_DOWNLOAD", True)),
            cache_enabled=bool(getattr(RuntimeConfig, "DRIVER_CACHE_ENABLED", True)),
            cache_dir=getattr(RuntimeConfig, "EDGE_DRIVER_CACHE_DIR", None),
            cache_cleanup_enabled=bool(getattr(RuntimeConfig, "DRIVER_CACHE_CLEANUP_ENABLED", True)),
        )
        self.version_provider = EdgeVersionProvider(self.platform)
        self.validator = DriverValidator(self.platform)
        self.cache = DriverCache(self.platform, self.validator, self.config.cache_dir)
        self.downloader = DriverDownloader(self.platform)
        self.resolver = DriverResolver(
            config=self.config,
            platform_name=self.platform,
            version_provider=self.version_provider,
            validator=self.validator,
            cache=self.cache,
            downloader=self.downloader,
        )

    def get_driver_path(self) -> str:
        return str(self.resolver.resolve())

    def verify_driver(self, driver_path: str) -> bool:
        return self.validator.verify(driver_path)

    def get_edge_version(self) -> Optional[str]:
        return self.version_provider.get_edge_version()

    def get_compatible_driver_version(self, edge_version: str) -> str:
        return self.downloader.resolve_driver_version(edge_version)

    def download_driver(self, driver_version: str) -> str:
        staged_driver, temp_dir = self.downloader.download_and_extract(driver_version)
        try:
            self.validator.prepare(staged_driver)
            if not self.validator.verify(staged_driver):
                raise RuntimeError("Downloaded EdgeDriver failed verification.")
            return str(self.cache.publish(driver_version, staged_driver))
        finally:
            temp_dir.cleanup()

    def extract_driver(self, zip_path: str) -> str:
        return str(self.downloader.extract_driver(Path(zip_path)))
