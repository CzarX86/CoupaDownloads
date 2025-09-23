"""Utility to print current tables for debugging."""
from __future__ import annotations

import asyncio

from sqlalchemy import inspect

from .session import async_session


async def _main() -> None:
    async with async_session() as session:
        async with session.bind.connect() as conn:  # type: ignore[attr-defined]
            def _list(sync_conn):
                inspector = inspect(sync_conn)
                return sorted(inspector.get_table_names())

            tables = await conn.run_sync(_list)
            for name in tables:
                print(name)


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
