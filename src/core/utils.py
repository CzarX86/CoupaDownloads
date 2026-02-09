"""
Shared utility functions for CoupaDownloads.
"""

import os
import time
import re
from typing import Optional, Dict, Any, List
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchWindowException,
    TimeoutException,
)

def _has_active_downloads(folder_path: str) -> bool:
    try:
        names = os.listdir(folder_path)
    except Exception:
        return False
    return any(name.endswith(('.crdownload', '.tmp', '.partial')) for name in names)


def _wait_for_downloads_complete(folder_path: str, timeout: int = 180, poll: float = 0.2, expected_count: Optional[int] = None) -> None:
    start = time.time()
    quiet_required = 0.4  # Matches standardized aggressive wait
    quiet_start = None
    while time.time() - start < timeout:
        active = _has_active_downloads(folder_path)
        
        if expected_count is not None:
            try:
                # Count only finalized files (not matching download suffixes)
                current_files = len([f for f in os.listdir(folder_path) if not any(f.endswith(s) for s in ('.crdownload', '.tmp', '.partial'))])
                if current_files >= expected_count and not active:
                    return
            except Exception:
                pass

        if not active:
            if quiet_start is None:
                quiet_start = time.time()
            elif time.time() - quiet_start >= quiet_required:
                return
        else:
            quiet_start = None
        time.sleep(poll)


def _parse_counts_from_message(message: str) -> tuple[Optional[int], Optional[int]]:
    """Extract (downloaded, total) from messages like 'Initiated download for X/Y attachments.'"""
    if not message:
        return None, None
    m = re.search(r"(\d+)\s*/\s*(\d+)", message)
    if not m:
        return None, None
    try:
        return int(m.group(1)), int(m.group(2))
    except Exception:
        return None, None


def _humanize_exception(exc: Exception) -> str:
    mapping: Dict[type, str] = {
        InvalidSessionIdException: 'Browser session expired while processing the PO.',
        NoSuchWindowException: 'Browser window closed unexpectedly.',
        TimeoutException: 'Timed out waiting for the page to finish loading.',
    }
    for exc_type, friendly in mapping.items():
        if isinstance(exc, exc_type):
            return friendly

    text = str(exc).strip()
    if not text:
        text = exc.__class__.__name__
    if len(text) > 150:
        text = text[:147] + '...'
    return f"{exc.__class__.__name__}: {text}"


def _derive_status_label(result: Optional[Dict[str, Any]]) -> str:
    if not result:
        return 'FAILED'
    if 'status_code' in result and result['status_code']:
        return result['status_code']

    success = result.get('success', False)
    message = result.get('message', '') or ''
    msg_lower = message.lower()
    dl, total = _parse_counts_from_message(message)
    if success:
        if total == 0 or 'no attachments' in msg_lower:
            return 'NO_ATTACHMENTS'
        if dl is not None and total is not None and dl < total:
            return 'PARTIAL'
        return 'COMPLETED'
    if 'oops' in msg_lower or 'not found' in msg_lower:
        return 'PO_NOT_FOUND'
    return 'FAILED'


def _suffix_for_status(status_code: str) -> str:
    """Return folder suffix for a given status code."""
    mapping = {
        'COMPLETED': '_COMPLETED',
        'FAILED': '_FAILED',
        'NO_ATTACHMENTS': '_NO_ATTACHMENTS',
        'PARTIAL': '_PARTIAL',
        'PO_NOT_FOUND': '_PO_NOT_FOUND',
        'TIMEOUT': '_TIMEOUT',
    }
    return mapping.get(status_code, f'_{status_code}')






def _build_csv_updates(result: Dict[str, Any]) -> Dict[str, Any]:
    """Translate a processing result into CSV column updates."""
    from datetime import datetime
    status_code = (result.get('status_code') or '').upper() or 'FAILED'
    attachment_names = result.get('attachment_names') or []
    if isinstance(attachment_names, str):
        attachment_names = [name for name in attachment_names.split(';') if name]

    error_message = ''
    success = result.get('success')
    if success is None:
        success = status_code in {'COMPLETED', 'NO_ATTACHMENTS', 'PARTIAL'}
    if not success:
        error_message = result.get('message', '') or result.get('error', '')

    updates: Dict[str, Any] = {
        'STATUS': status_code,
        'ATTACHMENTS_FOUND': result.get('attachments_found', 0),
        'ATTACHMENTS_DOWNLOADED': result.get('attachments_downloaded', 0),
        'AttachmentName': attachment_names,
        'DOWNLOAD_FOLDER': result.get('final_folder', ''),
        'COUPA_URL': result.get('coupa_url', ''),
        'ERROR_MESSAGE': error_message,
    }

    supplier_name = result.get('supplier_name')
    if supplier_name:
        updates['SUPPLIER'] = supplier_name

    last_processed = result.get('last_processed')
    if isinstance(last_processed, datetime):
        updates['LAST_PROCESSED'] = last_processed.isoformat()
    elif isinstance(last_processed, str) and last_processed:
        updates['LAST_PROCESSED'] = last_processed

    return updates


def _compose_csv_message(result_payload: dict) -> str:
    """Compose error message for CSV from result payload."""
    status_code = (result_payload.get('status_code') or '').upper()
    status_reason = result_payload.get('status_reason', '') or ''
    fallback_used = bool(result_payload.get('fallback_used'))
    fallback_details = result_payload.get('fallback_details') or {}
    trigger_reason = (
        result_payload.get('fallback_trigger_reason')
        or fallback_details.get('trigger_reason')
        or ''
    )
    message = result_payload.get('message', '') or ''

    if fallback_used:
        parts: List[str] = []
        if message:
            parts.append(message)

        if trigger_reason == 'po_without_pdf':
            parts.append('PO page did not expose PDF attachments.')
        elif trigger_reason == 'po_without_attachments':
            parts.append('PO page did not expose attachments.')

        source = (fallback_details.get('source') or '').strip()
        if source:
            friendly_source = source.replace('::', ' via ')
            parts.append(f"PR link source: {friendly_source}")

        pr_url = (fallback_details.get('url') or '').strip()
        if pr_url:
            parts.append(f"PR URL: {pr_url}")

        if not parts:
            parts.append('PR fallback used to retrieve documents.')
        return ' — '.join(parts)

    if status_code == 'COMPLETED':
        return ''
    if message:
        return message
    if status_code == 'NO_ATTACHMENTS':
        return status_reason.replace('_', ' ').title() if status_reason else 'No attachments found.'
    if status_reason:
        return status_reason.replace('_', ' ').title()
    return 'Processing failed.'
