import os
from pathlib import Path

from src.core.folder_finalizer import FolderFinalizer


def _create_work_folder(base: Path, name: str, filename: str = "file.txt") -> Path:
    folder = base / f"{name}__WORK"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / filename).write_text("content", encoding="utf-8")
    return folder


def test_folder_finalizer_renames_work_folder(tmp_path: Path):
    finalizer = FolderFinalizer(batch_interval=0.05, batch_size=10, ack_timeout_seconds=2)
    work_folder = _create_work_folder(tmp_path, "PO_123")
    result_ref = {"task_id": "t1", "po_number": "PO_123", "status_code": "COMPLETED", "final_folder": str(work_folder)}

    try:
        ack = finalizer.enqueue({"task_id": "t1", "po_number": "PO_123"}, result_ref).result(timeout=5)
        assert ack.success is True
        assert ack.final_folder.endswith("_COMPLETED")
        assert "__WORK" not in ack.final_folder
        assert os.path.isdir(ack.final_folder)
        assert result_ref["final_folder"] == ack.final_folder
    finally:
        finalizer.shutdown()


def test_folder_finalizer_noop_for_already_finalized_folder(tmp_path: Path):
    finalizer = FolderFinalizer(batch_interval=0.05, batch_size=10, ack_timeout_seconds=2)
    completed_folder = tmp_path / "PO_456_COMPLETED"
    completed_folder.mkdir(parents=True, exist_ok=True)
    result_ref = {
        "task_id": "t2",
        "po_number": "PO_456",
        "status_code": "COMPLETED",
        "final_folder": str(completed_folder),
    }

    try:
        future = finalizer.enqueue({"task_id": "t2", "po_number": "PO_456"}, result_ref)
        ack = future.result(timeout=1)
        assert ack.success is True
        assert ack.final_folder == str(completed_folder)
        assert finalizer.pending_count() == 0
    finally:
        finalizer.shutdown()


def test_folder_finalizer_merges_when_target_exists(tmp_path: Path):
    finalizer = FolderFinalizer(batch_interval=0.05, batch_size=10, ack_timeout_seconds=2)
    work_folder = _create_work_folder(tmp_path, "PO_777", filename="new.txt")
    target_folder = tmp_path / "PO_777_COMPLETED"
    target_folder.mkdir(parents=True, exist_ok=True)
    (target_folder / "existing.txt").write_text("existing", encoding="utf-8")
    result_ref = {"task_id": "t3", "po_number": "PO_777", "status_code": "COMPLETED", "final_folder": str(work_folder)}

    try:
        ack = finalizer.enqueue({"task_id": "t3", "po_number": "PO_777"}, result_ref).result(timeout=5)
        assert ack.success is True
        assert ack.final_folder == str(target_folder)
        assert (target_folder / "existing.txt").exists()
        assert (target_folder / "new.txt").exists()
        assert not work_folder.exists()
    finally:
        finalizer.shutdown()


def test_folder_finalizer_fallback_finalizes_when_ack_isnt_waited(tmp_path: Path):
    finalizer = FolderFinalizer(batch_interval=5.0, batch_size=10, ack_timeout_seconds=1)
    work_folder = _create_work_folder(tmp_path, "PO_888")
    result_ref = {"task_id": "t4", "po_number": "PO_888", "status_code": "COMPLETED", "final_folder": str(work_folder)}
    task_ref = {"task_id": "t4", "po_number": "PO_888"}

    try:
        ack = finalizer.finalize_now(task_ref, result_ref, reason="test_timeout_fallback")
        assert ack.success is True
        assert ack.final_folder.endswith("_COMPLETED")
        assert "__WORK" not in ack.final_folder
        assert os.path.isdir(ack.final_folder)
    finally:
        finalizer.shutdown(flush=False)


def test_folder_finalizer_flush_drains_queue(tmp_path: Path):
    finalizer = FolderFinalizer(batch_interval=0.05, batch_size=2, ack_timeout_seconds=2)
    futures = []

    try:
        for idx in range(5):
            work_folder = _create_work_folder(tmp_path, f"PO_{idx}")
            result_ref = {
                "task_id": f"t{idx}",
                "po_number": f"PO_{idx}",
                "status_code": "COMPLETED",
                "final_folder": str(work_folder),
            }
            futures.append(finalizer.enqueue({"task_id": f"t{idx}", "po_number": f"PO_{idx}"}, result_ref))

        assert finalizer.flush(timeout=20) is True
        assert finalizer.pending_count() == 0
        assert all(f.done() for f in futures)
    finally:
        finalizer.shutdown()
