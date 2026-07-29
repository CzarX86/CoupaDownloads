import sys
from pathlib import Path

import pytest

from src.services.msg_conversion_service import MsgToPdfConverter


class DummyAttachment:
    def __init__(self, name: str):
        self.longFilename = name
        self.shortFilename = name
        self.filename = name


class DummyMessage:
    def __init__(self):
        self.subject = "Test Subject"
        self.sender = "sender@example.com"
        self.sender_email = "sender@example.com"
        self.to = ["to@example.com"]
        self.cc = ["cc@example.com"]
        self.date = "2026-03-04"
        self.body = "Hello world\nLine 2"
        self.htmlBody = ""
        self.attachments = [DummyAttachment("file.txt")]


class DummyExtractMsg:
    def Message(self, _path: str) -> DummyMessage:  # noqa: N802 - keep external API name
        return DummyMessage()

class DummyBytesMessage(DummyMessage):
    def __init__(self):
        super().__init__()
        self.subject = b"Subject in bytes"
        self.sender = b"sender@example.com"
        self.to = [b"to@example.com"]
        self.cc = [b"cc@example.com"]
        self.body = b"Hello from bytes\x00with null char"
        self.htmlBody = b""


class DummyExtractMsgBytes:
    def Message(self, _path: str) -> DummyBytesMessage:  # noqa: N802 - keep external API name
        return DummyBytesMessage()


@pytest.fixture(autouse=True)
def patch_extract_msg(monkeypatch):
    """Provide a dummy extract_msg module for all tests."""
    monkeypatch.setitem(sys.modules, "extract_msg", DummyExtractMsg())


def test_convert_creates_pdf(tmp_path: Path):
    msg_path = tmp_path / "mail.msg"
    msg_path.write_text("dummy")

    converter = MsgToPdfConverter(overwrite=True)
    result = converter.convert(msg_path)

    pdf_path = msg_path.with_suffix(".pdf")
    assert result.status == "converted"
    assert pdf_path.exists()
    data = pdf_path.read_bytes()
    assert b"Test Subject" in data
    assert b"Hello world" in data


def test_convert_skips_when_pdf_exists(tmp_path: Path):
    msg_path = tmp_path / "mail.msg"
    msg_path.write_text("dummy")

    converter = MsgToPdfConverter(overwrite=False)
    first = converter.convert(msg_path)
    second = converter.convert(msg_path)

    assert first.status == "converted"
    assert second.status == "skipped"


def test_convert_handles_bytes_fields(tmp_path: Path, monkeypatch):
    msg_path = tmp_path / "mail.msg"
    msg_path.write_text("dummy")
    monkeypatch.setitem(sys.modules, "extract_msg", DummyExtractMsgBytes())

    converter = MsgToPdfConverter(overwrite=True)
    result = converter.convert(msg_path)

    pdf_path = msg_path.with_suffix(".pdf")
    assert result.status == "converted"
    assert pdf_path.exists()
