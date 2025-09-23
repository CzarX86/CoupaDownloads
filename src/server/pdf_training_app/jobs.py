"""Async job management backed by the database."""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set
from uuid import uuid4

from server.db import repository
from server.db.models import JobStatus, JobType
from server.db.session import async_session

from .models import JobDetail, JobStatus as ApiJobStatus, JobType as ApiJobType

JobCoroutine = Callable[[str], Awaitable[Optional[Dict[str, Any]]]]


class JobManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._tasks: Set[asyncio.Task[Any]] = set()

    async def submit(
        self,
        *,
        job_type: JobType,
        coro_factory: JobCoroutine,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> str:
        job_id = uuid4().hex
        async with async_session() as session:
            await repository.create_job(
                session,
                job_id=job_id,
                job_type=job_type,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            await session.commit()

        async def runner() -> None:
            async with async_session() as session:
                await repository.mark_job_running(session, job_id)
                await session.commit()
            try:
                payload = await coro_factory(job_id)
            except Exception as exc:  # pragma: no cover
                async with async_session() as session:
                    await repository.mark_job_failed(session, job_id, str(exc))
                    await session.commit()
                raise
            else:
                async with async_session() as session:
                    await repository.mark_job_succeeded(session, job_id, payload)
                    await session.commit()

        task = asyncio.create_task(runner())
        self._tasks.add(task)

        def _cleanup(fut: asyncio.Future[Any]) -> None:  # pragma: no cover - best-effort clean-up
            self._tasks.discard(task)

        task.add_done_callback(_cleanup)
        return job_id

    async def get(self, job_id: str) -> Optional[JobDetail]:
        async with async_session() as session:
            job = await repository.get_job(session, job_id)
        if not job:
            return None
        return JobDetail(
            id=job.id,
            job_type=ApiJobType(job.job_type.value),
            status=ApiJobStatus(job.status.value),
            detail=job.detail,
            payload=job.payload,
            resource_type=job.resource_type,
            resource_id=job.resource_id,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    async def list(self) -> List[JobDetail]:
        async with async_session() as session:
            jobs = await repository.list_jobs(session)
        return [
            JobDetail(
                id=job.id,
                job_type=ApiJobType(job.job_type.value),
                status=ApiJobStatus(job.status.value),
                detail=job.detail,
                payload=job.payload,
                resource_type=job.resource_type,
                resource_id=job.resource_id,
                started_at=job.started_at,
                finished_at=job.finished_at,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
            for job in jobs
        ]

    async def wait_until_complete(
        self,
        job_id: str,
        *,
        timeout: float = 30.0,
        poll_interval: float = 0.25,
    ) -> JobDetail:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            job = await self.get(job_id)
            if job is None:
                raise ValueError(f"Job not found: {job_id}")
            if job.status in {ApiJobStatus.succeeded, ApiJobStatus.failed}:
                return job
            if loop.time() >= deadline:
                raise TimeoutError(f"Job {job_id} did not finish within {timeout} seconds")
            await asyncio.sleep(poll_interval)


job_manager = JobManager()
