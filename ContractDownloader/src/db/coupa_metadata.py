"""Persistence adapter for the independently extracted Coupa metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from src.engine.coupa_metadata import CoupaLineMetadata, CoupaPOMetadata


class CoupaMetadataRepository:
    """Store PO metadata without coupling the extractor to SQLite details."""

    def __init__(self, db: Any):
        if not hasattr(db, "conn"):
            raise TypeError("CoupaMetadataRepository requires a database with a conn attribute")
        self.conn = db.conn
        self.ensure_schema()

    def ensure_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS coupa_po_metadata (
                session_id INTEGER NOT NULL,
                po_number TEXT NOT NULL,
                company_code TEXT,
                ship_to_user TEXT,
                payment_term TEXT,
                source_url TEXT,
                metadata_status TEXT NOT NULL DEFAULT 'PARTIAL',
                metadata_error TEXT,
                scraped_at TEXT,
                PRIMARY KEY (session_id, po_number)
            );

            CREATE TABLE IF NOT EXISTS coupa_po_lines (
                session_id INTEGER NOT NULL,
                po_number TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                crg_code TEXT,
                crg_raw TEXT,
                currency_code TEXT,
                PRIMARY KEY (session_id, po_number, line_number)
            );
            """
        )
        self.conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def save(self, session_id: int, metadata: CoupaPOMetadata) -> None:
        self.conn.execute(
            """
            INSERT INTO coupa_po_metadata (
                session_id, po_number, company_code, ship_to_user, payment_term,
                source_url, metadata_status, metadata_error, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, po_number) DO UPDATE SET
                company_code = excluded.company_code,
                ship_to_user = excluded.ship_to_user,
                payment_term = excluded.payment_term,
                source_url = excluded.source_url,
                metadata_status = excluded.metadata_status,
                metadata_error = excluded.metadata_error,
                scraped_at = excluded.scraped_at
            """,
            (
                session_id,
                metadata.po_number,
                metadata.company_code,
                metadata.ship_to_user,
                metadata.payment_term,
                metadata.source_url,
                metadata.metadata_status,
                metadata.metadata_error,
                self._now(),
            ),
        )
        self.conn.execute(
            "DELETE FROM coupa_po_lines WHERE session_id = ? AND po_number = ?",
            (session_id, metadata.po_number),
        )
        self.conn.executemany(
            """
            INSERT INTO coupa_po_lines (
                session_id, po_number, line_number, crg_code, crg_raw, currency_code
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    session_id,
                    metadata.po_number,
                    line.line_number,
                    line.crg_code,
                    line.crg_raw,
                    line.currency_code,
                )
                for line in metadata.lines
            ],
        )
        self.conn.commit()

    def save_error(self, session_id: int, po_number: str, error: str, source_url: str = "") -> None:
        metadata = CoupaPOMetadata(
            po_number=str(po_number),
            source_url=source_url or None,
            metadata_status="UNAVAILABLE",
            metadata_error=str(error),
        )
        self.save(session_id, metadata)

    def list_po_metadata(self, session_id: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT session_id, po_number, company_code, ship_to_user, payment_term,
                   source_url, metadata_status, metadata_error, scraped_at
            FROM coupa_po_metadata
            WHERE session_id = ?
            ORDER BY rowid ASC
            """,
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_line_metadata(self, session_id: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT session_id, po_number, line_number, crg_code, crg_raw, currency_code
            FROM coupa_po_lines
            WHERE session_id = ?
            ORDER BY po_number, line_number
            """,
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_po_metadata(self, session_id: int, po_number: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM coupa_po_metadata WHERE session_id = ? AND po_number = ?",
            (session_id, po_number),
        ).fetchone()
        return dict(row) if row else None

    def get_line_metadata(self, session_id: int, po_number: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT * FROM coupa_po_lines
            WHERE session_id = ? AND po_number = ?
            ORDER BY line_number
            """,
            (session_id, po_number),
        ).fetchall()
        return [dict(row) for row in rows]
