import os
import sys
import httpx
from bs4 import BeautifulSoup
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.lib.direct_http_downloader import DirectHTTPDownloader
from src.lib.config import Config

def test_turbo_mode_extraction():
    # 1. Setup mock data
    mock_url = "https://unilever.coupahost.com/order_headers/123456"
    mock_html = """
    <html>
        <body>
            <span data-supplier-name="MOCKED_SUPPLIER">MOCKED_SUPPLIER</span>
            <div class="attachments">
                <a href="/order_headers/123456/attachments/1" title="Invoice_PO123456.pdf">Download Invoice</a>
                <a href="https://other-domain.com/download?id=999" download>Other Attachment</a>
            </div>
        </body>
    </html>
    """
    
    # 2. Setup Mock Transport
    def handler(request):
        if "/order_headers/123456" in str(request.url) and not "attachments" in str(request.url):
            return httpx.Response(200, content=mock_html, headers={"Content-Type": "text/html"})
        if "attachments/1" in str(request.url):
            return httpx.Response(200, content=b"PDF_CONTENT", headers={"Content-Disposition": 'attachment; filename="Invoice_Real_Name.pdf"'})
        if "download?id=999" in str(request.url):
            return httpx.Response(200, content=b"OTHER_CONTENT", headers={"Content-Disposition": 'attachment; filename="Other.docx"'})
        return httpx.Response(404)

    # 3. Initialize downloader with mock transport
    cookies = {"session": "mocked_cookie"}
    downloader = DirectHTTPDownloader(cookies)
    downloader.client = httpx.Client(transport=httpx.MockTransport(handler), cookies=cookies)

    # 4. Run download
    temp_dir = "temp_verification_downloads"
    os.makedirs(temp_dir, exist_ok=True)
    
    def on_findings(data):
        return temp_dir

    print(f"DEBUG: Config.BASE_URL: {Config.BASE_URL}")
    # Force BASE_URL for test logic consistency in downloader
    old_base = Config.BASE_URL
    Config.BASE_URL = "https://unilever.coupahost.com"
    
    try:
        result = downloader.download_attachments_for_po("PO123456", on_attachments_found=on_findings)
        
        print("\n--- TEST RESULTS ---")
        print(f"Success: {result['success']}")
        print(f"Status: {result['status_code']}")
        print(f"Supplier: {result['supplier_name']}")
        print(f"Found: {result['attachments_found']}")
        print(f"Downloaded: {result['attachments_downloaded']}")
        print(f"Filenames: {result['attachment_names']}")

        # Assertions
        assert result['success'] is True
        assert result['supplier_name'] == "MOCKED_SUPPLIER"
        assert result['attachments_found'] == 2
        assert result['attachments_downloaded'] == 2
        assert "Invoice_Real_Name.pdf" in result['attachment_names']
        assert "Other.docx" in result['attachment_names']
        
        # Check files on disk
        for filename in result['attachment_names']:
            path = os.path.join(temp_dir, filename)
            assert os.path.exists(path)
            print(f"Verified file on disk: {path}")

        print("\n✅ TURBO MODE VERIFICATION PASSED!")

    finally:
        Config.BASE_URL = old_base
        # Cleanup
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    try:
        test_turbo_mode_extraction()
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
