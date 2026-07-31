import asyncio
import os
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from src.engine.crawler import CoupaCrawler, RateLimitError, AuthError
from src.engine.rate_limiter import RateLimiter


class MockSessionDB:
    def __init__(self):
        self.company_stats = {}
        self.po_records = {}
        self.updates = []
        self.suspended = set()

    def get_company_stats(self, session_id: int, company_code: str):
        return self.company_stats.get(
            (session_id, company_code),
            {"total": 0, "processed": 0, "errors": 0, "success": 0},
        )

    def suspend_company_code(self, session_id: int, company_code: str):
        self.suspended.add((session_id, company_code))

    def get_po(self, session_id: int, po_number: str):
        return self.po_records.get((session_id, po_number))

    def update_po_status(
        self,
        session_id: int,
        po_number: str,
        status: str,
        download_folder: str | None = None,
        attachment_count: int | None = None,
        error_message: str | None = None,
    ):
        self.updates.append({
            "session_id": session_id,
            "po_number": po_number,
            "status": status,
            "download_folder": download_folder,
            "attachment_count": attachment_count,
            "error_message": error_message,
        })
        self.po_records[(session_id, po_number)] = {
            "status": status,
            "download_folder": download_folder,
            "error_message": error_message,
        }

    def set_company_stats(self, session_id: int, company_code: str, total: int, processed: int, errors: int):
        self.company_stats[(session_id, company_code)] = {
            "total": total,
            "processed": processed,
            "errors": errors,
            "success": processed - errors,
        }


@pytest.fixture
def tmp_download_dir(tmp_path):
    return str(tmp_path)


# ——— PO Processing ———


@pytest.mark.asyncio
async def test_process_po_with_pr_and_dedup(tmp_download_dir):
    db = MockSessionDB()
    db.set_company_stats(session_id=1, company_code="CC1", total=10, processed=2, errors=0)

    crawler = CoupaCrawler(db=db, session_id=1, base_download_dir=tmp_download_dir)

    po_html = """
    <html><body>
        <a href='/attachments/po1/download'>fileA.pdf</a>
        <a href='/requisition_headers/PR123'>PR Link</a>
    </body></html>
    """
    pr_html = """
    <html><body>
        <a href='/attachments/po1/download'>fileA.pdf</a>
        <a href='/attachments/pr2/download'>fileB.docx</a>
    </body></html>
    """

    call_count = 0

    async def mock_fetch_html(url: str, label: str = ""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return po_html
        return pr_html

    crawler._fetch_html = mock_fetch_html
    crawler._download_attachment = AsyncMock()

    await crawler.process_po(po_number="PO123", company_code="CC1")

    assert crawler._download_attachment.call_count == 2
    downloaded = {call.args[1].split(os.sep)[-1] for call in crawler._download_attachment.call_args_list}
    assert downloaded == {"fileA.pdf", "fileB.docx"}

    po_record = db.get_po(1, "PO123")
    assert po_record["status"] == "SUCCESS"
    assert po_record["download_folder"] is not None
    await crawler.close()


@pytest.mark.asyncio
async def test_retry_preserves_valid_files_and_downloads_only_missing(tmp_download_dir):
    db = MockSessionDB()
    po_dir = os.path.join(tmp_download_dir, "CC1", "PO123")
    os.makedirs(po_dir, exist_ok=True)
    with open(os.path.join(po_dir, "fileA.pdf"), "wb") as stream:
        stream.write(b"%PDF-1.7 existing-valid-file")

    db.po_records[(1, "PO123")] = {
        "status": "PENDING",
        "output_subdir": "CC1",
    }
    crawler = CoupaCrawler(
        db=db,
        session_id=1,
        base_download_dir=tmp_download_dir,
        preserve_existing_files=True,
    )
    crawler._fetch_html = AsyncMock(return_value="""<html><body>
        <a href='/attachments/a/download'>fileA.pdf</a>
        <a href='/attachments/b/download'>fileB.docx</a>
    </body></html>""")
    crawler._download_attachment = AsyncMock()

    await crawler.process_po(po_number="PO123", company_code="CC1")

    assert crawler._download_attachment.call_count == 1
    assert crawler._download_attachment.call_args.args[1].endswith("fileB.docx")
    assert crawler._download_attachment.call_args.kwargs["replace_existing"] is True
    with open(os.path.join(po_dir, "fileA.pdf"), "rb") as stream:
        assert stream.read().startswith(b"%PDF-")
    await crawler.close()


@pytest.mark.asyncio
async def test_process_po_no_attachments(tmp_download_dir):
    db = MockSessionDB()
    crawler = CoupaCrawler(db=db, session_id=1, base_download_dir=tmp_download_dir)
    crawler._fetch_html = AsyncMock(return_value="<html><body>No attachments</body></html>")
    crawler._download_attachment = AsyncMock()

    await crawler.process_po(po_number="PO001", company_code="CC1")

    assert crawler._download_attachment.call_count == 0
    po_record = db.get_po(1, "PO001")
    assert po_record["status"] == "SUCCESS"
    await crawler.close()


@pytest.mark.asyncio
async def test_process_po_uses_output_subdir_for_path(tmp_download_dir):
    db = MockSessionDB()
    db.po_records[(1, "PO777")] = {
        "status": "PENDING",
        "output_subdir": "2026/Q12026/Yellow_Wood",
    }

    crawler = CoupaCrawler(db=db, session_id=1, base_download_dir=tmp_download_dir)
    crawler._fetch_html = AsyncMock(return_value="<html><body><a href='/attachments/1/download'>f.pdf</a></body></html>")
    crawler._download_attachment = AsyncMock()

    await crawler.process_po(po_number="PO777", company_code="CC1")

    assert crawler._download_attachment.call_count == 1
    dest_path = os.path.normpath(crawler._download_attachment.call_args.args[1])
    expected_subdir = os.path.join("2026", "Q12026", "Yellow_Wood", "PO777")
    assert expected_subdir in dest_path
    await crawler.close()


# ——— Circuit Breaker ———


@pytest.mark.asyncio
async def test_circuit_breaker_triggers_suspend(tmp_download_dir):
    db = MockSessionDB()
    db.set_company_stats(session_id=1, company_code="CC2", total=10, processed=3, errors=3)
    db.po_records[(1, "PO999")] = {"status": "SKIPPED_VERIFICATION_REQUIRED"}

    crawler = CoupaCrawler(db=db, session_id=1, base_download_dir=tmp_download_dir)
    crawler._fetch_html = AsyncMock(return_value="<html></html>")
    crawler._download_attachment = AsyncMock()

    await crawler.process_po(po_number="PO999", company_code="CC2")

    assert (1, "CC2") in db.suspended
    assert crawler._download_attachment.call_count == 0
    await crawler.close()


@pytest.mark.asyncio
async def test_circuit_breaker_requires_min_3_processed(tmp_download_dir):
    """< 3 processed POs should NOT trigger circuit breaker, even if error rate is 100%."""
    db = MockSessionDB()
    db.set_company_stats(session_id=1, company_code="CC3", total=10, processed=2, errors=2)

    crawler = CoupaCrawler(db=db, session_id=1, base_download_dir=tmp_download_dir)
    crawler._fetch_html = AsyncMock(return_value="<html><body><a href='/attachments/1/download'>f.pdf</a></body></html>")
    crawler._download_attachment = AsyncMock()

    await crawler.process_po(po_number="PO100", company_code="CC3")

    # Should NOT suspend — only 2 POs processed (< 3 minimum)
    assert (1, "CC3") not in db.suspended
    await crawler.close()


@pytest.mark.asyncio
async def test_circuit_breaker_not_triggered_below_15_percent(tmp_download_dir):
    db = MockSessionDB()
    db.set_company_stats(session_id=1, company_code="CC4", total=100, processed=10, errors=10)

    crawler = CoupaCrawler(db=db, session_id=1, base_download_dir=tmp_download_dir)
    crawler._fetch_html = AsyncMock(return_value="<html></html>")

    await crawler.process_po(po_number="PO200", company_code="CC4")

    # 10/100 = 10% < 15% — should NOT suspend
    assert (1, "CC4") not in db.suspended
    await crawler.close()


@pytest.mark.asyncio
async def test_circuit_breaker_can_be_disabled(tmp_download_dir):
    db = MockSessionDB()
    db.set_company_stats(session_id=1, company_code="CCX", total=10, processed=3, errors=3)
    db.po_records[(1, "POX")] = {"status": "PENDING"}

    crawler = CoupaCrawler(
        db=db,
        session_id=1,
        base_download_dir=tmp_download_dir,
        enable_circuit_breaker=False,
    )
    crawler._fetch_html = AsyncMock(return_value="<html><body>No attachments</body></html>")

    await crawler.process_po(po_number="POX", company_code="CCX")

    assert (1, "CCX") not in db.suspended
    await crawler.close()


# ——— PO URL Resolution ———


def test_po_url_candidates_include_original_for_prefixed_ids():
    db = MockSessionDB()
    crawler = CoupaCrawler(db=db, session_id=1, base_download_dir="/tmp")
    assert crawler._po_url_candidates("PO14718345") == [
        "https://unilever.coupahost.com/order_headers/PO14718345",
        "https://unilever.coupahost.com/order_headers/14718345",
    ]
    assert crawler._po_url_candidates("PM12345") == [
        "https://unilever.coupahost.com/order_headers/PM12345",
        "https://unilever.coupahost.com/order_headers/12345",
    ]
    assert crawler._po_url_candidates("12345") == ["https://unilever.coupahost.com/order_headers/12345"]


@pytest.mark.asyncio
async def test_process_po_retries_original_url_when_primary_returns_404(tmp_download_dir):
    db = MockSessionDB()
    crawler = CoupaCrawler(db=db, session_id=1, base_download_dir=tmp_download_dir)

    async def mock_fetch_html(url: str, label: str = ""):
        if url.endswith("/order_headers/PO14718345"):
            req = httpx.Request("GET", url)
            resp = httpx.Response(404, request=req)
            raise httpx.HTTPStatusError("404", request=req, response=resp)
        if url.endswith("/order_headers/14718345"):
            return "<html><body>No attachments</body></html>"
        raise AssertionError(f"Unexpected URL called: {url}")

    crawler._fetch_html = mock_fetch_html
    crawler._download_attachment = AsyncMock()

    result = await crawler.process_po(po_number="PO14718345", company_code="CC1")

    assert result["success"] is True
    po_record = db.get_po(1, "PO14718345")
    assert po_record["status"] == "SUCCESS"
    await crawler.close()


def test_safe_attachment_filename_truncates_long_names():
    db = MockSessionDB()
    crawler = CoupaCrawler(db=db, session_id=1, base_download_dir="/tmp")

    long_name = "Invoice_" + ("very_long_segment_" * 30) + ".pdf"
    safe = crawler._safe_attachment_filename(long_name, "https://example.com/attachments/123/download.pdf")

    assert len(safe) <= 180
    assert safe.endswith(".pdf")
    assert " " not in safe


def test_filename_from_content_disposition_plain_filename():
    db = MockSessionDB()
    crawler = CoupaCrawler(db=db, session_id=1, base_download_dir="/tmp")

    header = 'attachment; filename="Invoice_2026_05_21.pdf"'
    assert crawler._filename_from_content_disposition(header) == "Invoice_2026_05_21.pdf"


def test_filename_from_content_disposition_filename_star():
    db = MockSessionDB()
    crawler = CoupaCrawler(db=db, session_id=1, base_download_dir="/tmp")

    header = "attachment; filename*=UTF-8''Invoice_%23ABC123.msg"
    assert crawler._filename_from_content_disposition(header) == "Invoice_#ABC123.msg"


# ——— Exception Handling ———


@pytest.mark.asyncio
async def test_process_po_cleans_up_on_error(tmp_download_dir):
    db = MockSessionDB()

    crawler = CoupaCrawler(db=db, session_id=1, base_download_dir=tmp_download_dir)
    crawler._fetch_html = AsyncMock(
        return_value="<html><body><a href='/attachments/1/download'>f.pdf</a></body></html>"
    )
    crawler._download_attachment = AsyncMock(side_effect=RateLimitError("429"))

    result = await crawler.process_po(po_number="PO500", company_code="CC5")

    assert result["success"] is False
    assert "429" in result["error"] or "Rate" in result["error"]

    po_dir = os.path.join(tmp_download_dir, "CC5", "PO500")
    assert not os.path.exists(po_dir)
    await crawler.close()


# ——— Concurrent Batch ———


@pytest.mark.asyncio
async def test_process_batch_concurrent(tmp_download_dir):
    db = MockSessionDB()
    po_html = "<html><body>No attachments</body></html>"

    crawler = CoupaCrawler(db=db, session_id=1, base_download_dir=tmp_download_dir, concurrency=5)
    crawler._fetch_html = AsyncMock(return_value=po_html)

    batch = [("PO001", "CC-A"), ("PO002", "CC-A"), ("PO003", "CC-B")]
    results = await crawler.process_batch(batch)

    assert len(results) == 3
    assert all(r["success"] for r in results)
    await crawler.close()
