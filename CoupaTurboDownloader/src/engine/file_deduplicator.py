from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any


class FileDeduplicator:
    """Identify identical files and replace duplicates with hard links when possible."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = Path(db_path or (Path.home() / ".coupa_turbo" / "file_hashes.db")).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS file_hashes (
                sha256 TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                canonical_path TEXT NOT NULL,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS file_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sha256 TEXT NOT NULL,
                duplicate_path TEXT NOT NULL,
                canonical_path TEXT NOT NULL,
                method TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _reference_path(path: Path) -> Path:
        return path.with_name(f"{path.name}.duplicate.json")

    def process_tree(self, root: Path) -> dict[str, Any]:
        summary = {"scanned": 0, "duplicates": 0, "hardlinks": 0, "references": 0, "errors": []}
        if not root.exists():
            self.close()
            return summary
        try:
            files = sorted(path for path in root.rglob("*") if path.is_file() and not path.name.endswith(".duplicate.json"))
            for path in files:
                try:
                    digest = self._sha256(path)
                    size = path.stat().st_size
                    summary["scanned"] += 1
                    row = self.conn.execute(
                        "SELECT canonical_path FROM file_hashes WHERE sha256 = ? AND size = ?",
                        (digest, size),
                    ).fetchone()
                    canonical = Path(row[0]) if row else None
                    if canonical and canonical.exists() and canonical.resolve() != path.resolve():
                        method = "reference"
                        temporary_link = path.with_name(f".{path.name}.dedup-link-{os.getpid()}")
                        try:
                            temporary_link.unlink(missing_ok=True)
                            # Create the hard link first and atomically replace the
                            # duplicate only after it succeeds. The old sequence
                            # unlinked the valid file before os.link(), risking data
                            # loss when linking failed.
                            os.link(canonical, temporary_link)
                            os.replace(temporary_link, path)
                            method = "hardlink"
                            summary["hardlinks"] += 1
                        except OSError:
                            temporary_link.unlink(missing_ok=True)
                            reference = self._reference_path(path)
                            reference.write_text(
                                json.dumps({"sha256": digest, "canonical_path": str(canonical)}, indent=2),
                                encoding="utf-8",
                            )
                            summary["references"] += 1
                        summary["duplicates"] += 1
                        self.conn.execute(
                            "INSERT INTO file_references (sha256, duplicate_path, canonical_path, method) VALUES (?, ?, ?, ?)",
                            (digest, str(path), str(canonical), method),
                        )
                    else:
                        self.conn.execute(
                            "INSERT OR REPLACE INTO file_hashes (sha256, size, canonical_path) VALUES (?, ?, ?)",
                            (digest, size, str(path)),
                        )
                    self.conn.commit()
                except (OSError, ValueError) as exc:
                    summary["errors"].append({"path": str(path), "error": str(exc)})
        finally:
            self.close()
        return summary

    def close(self) -> None:
        self.conn.close()
