from pathlib import Path

from src.engine.msg_converter import _extract_attachments_to_subfolder, find_msg_files


def test_find_msg_files_is_case_insensitive(tmp_path):
    lower = tmp_path / "mail.msg"
    upper = tmp_path / "approval.MSG"
    lower.write_bytes(b"msg")
    upper.write_bytes(b"msg")
    (tmp_path / "not-a-message.txt").write_text("text", encoding="utf-8")

    assert set(find_msg_files(tmp_path)) == {lower, upper}


class _FakeMessage:
    def __init__(self, attachments):
        self.attachments = attachments


class _SaveAttachment:
    def __init__(self, name: str, content: bytes):
        self.longFilename = name
        self._content = content

    def save(self, **kwargs):
        target = Path(kwargs["customPath"]) / kwargs["customFilename"]
        target.write_bytes(self._content)
        return (1, str(target))


class _BytesAttachment:
    def __init__(self, name: str, data: bytes):
        self.longFilename = name
        self.data = data

    def save(self, **kwargs):
        raise RuntimeError("simulate attachment save failure")


class _InlineImageAttachment:
    def __init__(self, name: str):
        self.longFilename = name
        self.cid = f"{name}@cid"
        self.contentId = self.cid
        self.mimetype = "image/png"
        self.hidden = True
        self.data = b"png-inline"

    def save(self, **kwargs):
        target = Path(kwargs["customPath"]) / kwargs["customFilename"]
        target.write_bytes(self.data)
        return (1, str(target))


def test_extract_attachments_creates_subfolder(tmp_path):
    msg_path = tmp_path / "mail.msg"
    msg_path.write_bytes(b"placeholder")

    message = _FakeMessage([
        _SaveAttachment("invoice-123.pdf", b"pdf-content"),
        _SaveAttachment("plan.xlsx", b"xlsx-content"),
    ])

    saved = _extract_attachments_to_subfolder(message, msg_path)

    att_dir = tmp_path / "mail_attachments"
    assert att_dir.exists()
    assert len(saved) == 2
    assert (att_dir / "invoice-123.pdf").read_bytes() == b"pdf-content"
    assert (att_dir / "plan.xlsx").read_bytes() == b"xlsx-content"


def test_extract_attachments_fallback_to_bytes(tmp_path):
    msg_path = tmp_path / "mail.msg"
    msg_path.write_bytes(b"placeholder")

    message = _FakeMessage([
        _BytesAttachment("Outplacement-Oznur.docx", b"docx-bytes"),
    ])

    saved = _extract_attachments_to_subfolder(message, msg_path)

    att_dir = tmp_path / "mail_attachments"
    assert att_dir.exists()
    assert len(saved) == 1
    assert (att_dir / "Outplacement-Oznur.docx").read_bytes() == b"docx-bytes"


def test_extract_attachments_ignores_inline_signature_images(tmp_path):
    msg_path = tmp_path / "mail.msg"
    msg_path.write_bytes(b"placeholder")

    message = _FakeMessage([
        _InlineImageAttachment("image001.png"),
        _SaveAttachment("contract.pdf", b"contract"),
    ])

    saved = _extract_attachments_to_subfolder(message, msg_path)

    att_dir = tmp_path / "mail_attachments"
    assert att_dir.exists()
    assert len(saved) == 1
    assert (att_dir / "contract.pdf").exists()
    assert not (att_dir / "image001.png").exists()
