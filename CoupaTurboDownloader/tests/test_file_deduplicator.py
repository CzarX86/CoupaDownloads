import os

from src.engine.file_deduplicator import FileDeduplicator


def test_hard_link_failure_preserves_duplicate_file(tmp_path, monkeypatch):
    root = tmp_path / "files"
    root.mkdir()
    first = root / "a.pdf"
    duplicate = root / "b.pdf"
    first.write_bytes(b"same-valid-content")
    duplicate.write_bytes(b"same-valid-content")

    def fail_link(_source, _destination):
        raise OSError("cross-device link unavailable")

    monkeypatch.setattr(os, "link", fail_link)
    deduplicator = FileDeduplicator(str(tmp_path / "hashes.db"))
    summary = deduplicator.process_tree(root)

    assert first.read_bytes() == b"same-valid-content"
    assert duplicate.read_bytes() == b"same-valid-content"
    assert (root / "b.pdf.duplicate.json").exists()
    assert summary["duplicates"] == 1
    assert summary["references"] == 1


def test_successful_deduplication_uses_hard_link(tmp_path):
    root = tmp_path / "files"
    root.mkdir()
    first = root / "a.pdf"
    duplicate = root / "b.pdf"
    first.write_bytes(b"same-valid-content")
    duplicate.write_bytes(b"same-valid-content")

    deduplicator = FileDeduplicator(str(tmp_path / "hashes.db"))
    summary = deduplicator.process_tree(root)

    assert first.read_bytes() == duplicate.read_bytes()
    assert os.path.samefile(first, duplicate)
    assert summary["duplicates"] == 1
    assert summary["hardlinks"] == 1
