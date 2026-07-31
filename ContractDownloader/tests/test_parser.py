import pytest
from src.engine.parser import CoupaParser


# ——— Authenticity Token ———


def test_extract_authenticity_token():
    html = '<html><body><form><input type="hidden" name="authenticity_token" value="abc123token"/></form></body></html>'
    assert CoupaParser.extract_authenticity_token(html) == "abc123token"


def test_extract_authenticity_token_not_found():
    assert CoupaParser.extract_authenticity_token("<html><body></body></html>") is None


# ——— Two-Pass Attachment Extraction ———


def test_extract_attachments_href_pass():
    """Pass 2: href in anchor tags with attachment/download patterns."""
    html = """
    <html><body>
        <a href="/attachments/1/download" title="Download file1.pdf">file1.pdf</a>
        <a href="/attachments/2/download">file2.docx</a>
        <a href="/other/link">ignore.txt</a>
    </body></html>
    """
    attachments = CoupaParser.extract_attachments(html)
    assert len(attachments) == 2
    assert attachments[0]["filename"] == "file1.pdf"
    assert attachments[0]["url"] == "/attachments/1/download"
    assert attachments[1]["filename"] == "file2.docx"


def test_extract_attachments_data_url_pass():
    """Pass 1: data-url attributes in elements."""
    html = """
    <html><body>
        <span data-url="/attachments/55/download" title="report.pdf">report.pdf</span>
        <div data-url="/download/file/99">invoice.pdf</div>
    </body></html>
    """
    attachments = CoupaParser.extract_attachments(html)
    assert len(attachments) == 2
    filenames = {a["filename"] for a in attachments}
    assert "report.pdf" in filenames
    assert "invoice.pdf" in filenames


def test_extract_attachments_download_attribute():
    """Anchor tags with 'download' attribute."""
    html = """
    <html><body>
        <a href="/files/data.csv" download>data.csv</a>
        <a href="/files/report.pdf" download="report.pdf">Report</a>
    </body></html>
    """
    attachments = CoupaParser.extract_attachments(html)
    assert len(attachments) == 2


def test_extract_attachments_prefers_title_over_concatenated_text():
    html = """
    <html><body>
        <a href="/attachments/1/download" title="Invoice_123.pdf">
            Invoice_123.pdf ================================= Invoice_456.pdf =================================
        </a>
    </body></html>
    """
    attachments = CoupaParser.extract_attachments(html)
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "Invoice_123.pdf"


def test_extract_attachments_ignores_message_like_text_without_filename_pattern():
    html = """
    <html><body>
        <a href="/attachments/1/download?filename=REQ_4455.pdf" title="Mensagem do aprovador: verificar detalhes">
            Mensagem do aprovador: verificar detalhes
        </a>
    </body></html>
    """
    attachments = CoupaParser.extract_attachments(html)
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "REQ_4455.pdf"


def test_extract_attachments_ignores_page_link_with_download_word_only():
    html = """
    <html><body>
        <a href="/order_headers/12345/download_summary">Download summary</a>
    </body></html>
    """
    attachments = CoupaParser.extract_attachments(html)
    assert attachments == []


def test_extract_attachments_accepts_download_url_with_filename_query():
    html = """
    <html><body>
        <a href="/api/blob/download?id=99&filename=Thread.msg">Abrir mensagem</a>
    </body></html>
    """
    attachments = CoupaParser.extract_attachments(html)
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "Thread.msg"


def test_extract_attachments_ignores_generic_attachment_show_route():
    html = """
    <html><body>
        <li class="attachment" data-url="/attachments/1270815590">
            <span class="attachment-file" data-url="https://unilever.coupahost.com/attachment/attachment_file/type/1270815590/example.eml">
                <span role="button" title="example.eml" aria-label="example.eml file attachment">example.eml</span>
            </span>
        </li>
    </body></html>
    """
    attachments = CoupaParser.extract_attachments(html)
    assert len(attachments) == 1
    assert attachments[0]["url"].endswith("/attachment/attachment_file/type/1270815590/example.eml")


def test_extract_attachments_from_span_attachment_widget_and_ancestor_data_url():
    html = """
    <html><body>
        <div data-url="/api/blob/download?id=42&filename=RE__Approved_PO_Amounts_for_2025.eml">
            <span
                aria-label="RE__Approved_PO_Amounts_for_2025.eml file attachment"
                class="underline"
                role="button"
                tabindex="0"
                title="RE__Approved_PO_Amounts_for_2025.eml"
            >RE__Approved_PO_Amounts_for_2025.eml</span>
        </div>
    </body></html>
    """
    attachments = CoupaParser.extract_attachments(html)
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "RE__Approved_PO_Amounts_for_2025.eml"


def test_extract_attachments_combined():
    """Both passes together, with deduplication handled separately."""
    html = """
    <html><body>
        <span data-url="/attachments/a/download">from_data_url.pdf</span>
        <a href="/attachments/b/download">from_href.docx</a>
    </body></html>
    """
    attachments = CoupaParser.extract_attachments(html)
    assert len(attachments) == 2


def test_extract_attachments_empty():
    assert CoupaParser.extract_attachments("<html><body>No links</body></html>") == []


# ——— URL Resolution ———


def test_extract_attachments_url_resolution():
    """Relative URLs resolved against base_url."""
    html = '<a href="/attachments/1/download">f.pdf</a>'
    attachments = CoupaParser.extract_attachments(html, base_url="https://unilever.coupahost.com")
    assert attachments[0]["url"] == "https://unilever.coupahost.com/attachments/1/download"


def test_extract_attachments_absolute_url_unchanged():
    html = '<a href="https://cdn.example.com/attachments/download/file.pdf">f.pdf</a>'
    attachments = CoupaParser.extract_attachments(html, base_url="https://unilever.coupahost.com")
    assert attachments[0]["url"] == "https://cdn.example.com/attachments/download/file.pdf"


# ——— PR Link Extraction ———


def test_extract_pr_link():
    html = '<html><body><a href="/requisition_headers/7890">REQ-7890</a><a href="/other">Ignore</a></body></html>'
    assert CoupaParser.extract_pr_link(html) == "/requisition_headers/7890"


def test_extract_pr_link_not_found():
    assert CoupaParser.extract_pr_link("<html><body><a href='/purchase_orders/123'>PO</a></body></html>") is None


def test_extract_pr_links_multiple_unique():
    html = """
    <html><body>
        <a href="/requisition_headers/111">REQ-111</a>
        <a href="/other">Ignore</a>
        <a href="/requisition_headers/222">REQ-222</a>
        <a href="/requisition_headers/111">REQ-111 duplicate</a>
    </body></html>
    """
    assert CoupaParser.extract_pr_links(html) == ["/requisition_headers/111", "/requisition_headers/222"]


# ——— Deduplication ———


def test_deduplicate_by_url():
    attachments = [
        {"filename": "invoice.pdf", "url": "/attachments/1/download"},
        {"filename": "invoice.pdf", "url": "/attachments/1/download"},
        {"filename": "contract.docx", "url": "/attachments/2/download"},
    ]
    unique = CoupaParser.deduplicate_attachments(attachments)
    assert len(unique) == 2


def test_deduplicate_by_filename():
    attachments = [
        {"filename": "report.pdf", "url": "/attachments/10/download"},
        {"filename": "report.pdf", "url": "/attachments/99/download"},
        {"filename": "other.xlsx", "url": "/attachments/11/download"},
    ]
    unique = CoupaParser.deduplicate_attachments(attachments)
    assert len(unique) == 2
    assert unique[0]["url"] == "/attachments/10/download"


def test_deduplicate_empty():
    assert CoupaParser.deduplicate_attachments([]) == []


# ——— Filename Sanitization ———


def test_sanitize_filename():
    assert CoupaParser._sanitize_filename("file:name*.pdf") == "file_name_.pdf"
    assert CoupaParser._sanitize_filename("nice-name.pdf") == "nice-name.pdf"
