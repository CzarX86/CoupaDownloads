import os
import pandas as pd
import pytest
from unittest.mock import AsyncMock

from src.db.session_db import SessionDB
from src.gui.api import AppAPI
from src.engine.crawler import CoupaCrawler


@pytest.mark.asyncio
async def test_e2e_pipeline_with_sample_from_input_csv(tmp_path):
    # Keep the E2E fixture deterministic and independent from ignored local
    # input files, which are intentionally unavailable on CI runners.
    normalized_df = pd.DataFrame({
        "PO Number": ["PO1001", "PO1002", "PO1003"],
        "legal entity": ["ACME-BR", "ACME-BR", "ACME-US"],
    })
    normalized_csv = tmp_path / "sample_for_e2e.csv"
    normalized_df.to_csv(normalized_csv, index=False)

    db = SessionDB(str(tmp_path / "e2e.db"))
    api = AppAPI(db, str(tmp_path / "downloads"))

    import_result = api.import_file(str(normalized_csv))
    assert import_result["success"] is True
    assert import_result["total_pos"] == 3

    session_id = import_result["session_id"]
    po_numbers = normalized_df["PO Number"].tolist()

    async def fake_fetch_html(url: str, label: str = "") -> str:
        if "/requisition_headers/" in url:
            po_number = url.split("/")[-1]
            return f'''
                <html>
                    <a href="/attachments/{po_number}-a/download">shared-{po_number}.pdf</a>
                    <a href="/attachments/{po_number}-b/download">unique-{po_number}.docx</a>
                </html>
            '''
        po_number = url.split("/")[-1]
        return f'''
            <html>
                <a href="/attachments/{po_number}-a/download">shared-{po_number}.pdf</a>
                <a href="/requisition_headers/{po_number}">REQ-{po_number}</a>
            </html>
        '''

    async def fake_download(url: str, dest_path: str):
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(f"downloaded:{url}")

    crawler = CoupaCrawler(db, session_id, str(tmp_path / "downloads"))
    crawler._fetch_html = fake_fetch_html
    crawler._download_attachment = AsyncMock(side_effect=fake_download)

    for po_number, company_code in normalized_df[["PO Number", "legal entity"]].itertuples(index=False):
        await crawler.process_po(po_number, company_code)

    assert crawler._download_attachment.await_count == 6

    for po_number, company_code in normalized_df[["PO Number", "legal entity"]].itertuples(index=False):
        po = db.get_po(session_id, po_number)
        assert po["status"] == "SUCCESS"

        po_folder = tmp_path / "downloads" / company_code / po_number
        assert po_folder.exists()

        downloaded_files = sorted([p.name for p in po_folder.glob("*") if p.is_file()])
        # Crawler tries original PO/PM id first and may fallback to stripped id on 404.
        order_number = po_number[2:] if po_number.upper().startswith(("PO", "PM")) else po_number
        expected_original = [f"shared-{po_number}.pdf", f"unique-{po_number}.docx"]
        expected_stripped = [f"shared-{order_number}.pdf", f"unique-{order_number}.docx"]
        assert downloaded_files in (expected_original, expected_stripped)

    await crawler.close()
    db.close()
