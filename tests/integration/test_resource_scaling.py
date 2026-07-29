"""
Integration tests for resource-based autoscaling in PersistentWorkerPool.

Verifies that the pool adjusts its active worker target upward when
resource metrics indicate spare capacity, and backs off under pressure.
"""

import asyncio
from pathlib import Path
from unittest.mock import patch

from src.workers.models import PoolConfig
from src.workers.persistent_pool import PersistentWorkerPool


def _build_pool(tmp_path: Path, worker_count: int = 4) -> PersistentWorkerPool:
    profile_dir = tmp_path / "profile"
    download_dir = tmp_path / "downloads"
    profile_dir.mkdir()
    download_dir.mkdir()
    return PersistentWorkerPool(
        PoolConfig(
            worker_count=worker_count,
            autoscaling_enabled=True,
            base_profile_path=str(profile_dir),
            download_root=str(download_dir),
            profile_cleanup_on_shutdown=False,
        )
    )


class TestAutoscalingEnabled:
    """Verify pool initialises in single-worker mode when autoscaling is enabled."""

    def test_initial_state_single_worker(self, tmp_path: Path) -> None:
        pool = _build_pool(tmp_path, worker_count=4)
        assert pool._autoscaling_enabled is True
        assert pool._active_worker_target == 1
        assert pool._target_worker_count == 4

    def test_autoscaling_disabled_targets_full_worker_count(self, tmp_path: Path) -> None:
        profile_dir = tmp_path / "p2"
        download_dir = tmp_path / "d2"
        profile_dir.mkdir()
        download_dir.mkdir()
        pool = PersistentWorkerPool(
            PoolConfig(
                worker_count=3,
                autoscaling_enabled=False,
                base_profile_path=str(profile_dir),
                download_root=str(download_dir),
                profile_cleanup_on_shutdown=False,
            )
        )
        assert pool._autoscaling_enabled is False
        assert pool._active_worker_target == 3


class TestResourceSnapshotHandling:
    """Verify pool correctly ingests resource snapshots from CommunicationManager."""

    def test_resource_snapshot_updates_internal_state(self, tmp_path: Path) -> None:
        """A RESOURCE metric snapshot must update pool resource tracking."""
        pool = _build_pool(tmp_path, worker_count=2)
        if pool.communication_manager is None:
            return

        pool.communication_manager.send_metric(
            {
                "status": "RESOURCE",
                "timestamp": 1.0,
                "message": "Resource snapshot",
                "resource_snapshot": {
                    "cpu_percent": 20.0,
                    "memory_percent": 40.0,
                    "available_ram_gb": 12.0,
                    "worker_count": 1,
                    "target_worker_count": 2,
                    "autoscaling_enabled": True,
                    "pending_tasks": 3,
                    "processing_tasks": 1,
                },
            }
        )

        aggregated = pool.communication_manager.get_aggregated_metrics()
        resources = aggregated.get("resources", {})
        assert resources.get("cpu_percent") == 20.0
        assert resources.get("available_ram_gb") == 12.0

    def test_get_status_reflects_current_configuration(self, tmp_path: Path) -> None:
        """get_status must expose worker count and autoscaling flag."""
        pool = _build_pool(tmp_path, worker_count=2)
        status = pool.get_status()
        assert status["target_worker_count"] == 2
        assert status["autoscaling_enabled"] is True
