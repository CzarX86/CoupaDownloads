"""
Integration tests for ResultAggregator.

Tests the result aggregation and persistence layer.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile
import os

from src.orchestrators.result_aggregator import ResultAggregator
from src.core.telemetry import TelemetryProvider
from src.core.status import StatusLevel


class TestResultAggregatorInitialization:
    """Test ResultAggregator initialization."""

    def test_init_with_all_handlers(self) -> None:
        """Test initialization with all handlers."""
        mock_csv = Mock()
        mock_sqlite = Mock()
        mock_telemetry = Mock(spec=TelemetryProvider)

        aggregator = ResultAggregator(
            csv_handler=mock_csv,
            sqlite_handler=mock_sqlite,
            telemetry=mock_telemetry
        )

        assert aggregator.csv_handler is mock_csv
        assert aggregator.sqlite_handler is mock_sqlite
        assert aggregator.telemetry is mock_telemetry
        assert aggregator._successful_count == 0
        assert aggregator._failed_count == 0
        assert aggregator._start_time is None

    def test_init_with_no_handlers(self) -> None:
        """Test initialization with no handlers."""
        aggregator = ResultAggregator()

        assert aggregator.csv_handler is None
        assert aggregator.sqlite_handler is None
        assert aggregator.telemetry is None

    def test_init_sets_statistics(self) -> None:
        """Test that statistics are initialized to zero."""
        aggregator = ResultAggregator()

        stats = aggregator.get_statistics()
        assert stats['total_processed'] == 0
        assert stats['successful'] == 0
        assert stats['failed'] == 0


class TestResultAggregatorRecordSuccess:
    """Test recording successful operations."""

    def test_record_success_increments_counter(self) -> None:
        """Test that record_success increments successful count."""
        aggregator = ResultAggregator()

        aggregator.record_success("PO123", {'status_code': 'COMPLETED'})

        assert aggregator._successful_count == 1
        assert aggregator._failed_count == 0

    @patch.object(ResultAggregator, '_persist_result')
    def test_record_success_persists_result(
        self,
        mock_persist: Mock
    ) -> None:
        """Test that record_success persists the result."""
        aggregator = ResultAggregator()

        result = {'status_code': 'COMPLETED', 'attachments_found': 5}
        aggregator.record_success("PO123", result)

        mock_persist.assert_called_once_with("PO123", result)

    def test_record_success_emits_telemetry(self) -> None:
        """Test that record_success emits telemetry."""
        mock_telemetry = Mock(spec=TelemetryProvider)
        aggregator = ResultAggregator(telemetry=mock_telemetry)

        aggregator.record_success("PO123", {'status_code': 'COMPLETED'})

        mock_telemetry.emit_status.assert_called_once()
        call_args = mock_telemetry.emit_status.call_args
        assert call_args[0][0] == StatusLevel.SUCCESS
        assert "PO123" in call_args[0][1]
        assert "COMPLETED" in call_args[0][1]

    def test_record_success_multiple_times(self) -> None:
        """Test recording multiple successes."""
        aggregator = ResultAggregator()

        aggregator.record_success("PO123", {'status_code': 'COMPLETED'})
        aggregator.record_success("PO124", {'status_code': 'COMPLETED'})
        aggregator.record_success("PO125", {'status_code': 'NO_ATTACHMENTS'})

        assert aggregator._successful_count == 3
        assert aggregator._failed_count == 0


class TestResultAggregatorRecordFailure:
    """Test recording failed operations."""

    def test_record_failure_increments_counter(self) -> None:
        """Test that record_failure increments failed count."""
        aggregator = ResultAggregator()

        aggregator.record_failure("PO123", {'status_code': 'FAILED'})

        assert aggregator._successful_count == 0
        assert aggregator._failed_count == 1

    @patch.object(ResultAggregator, '_persist_result')
    def test_record_failure_persists_result(
        self,
        mock_persist: Mock
    ) -> None:
        """Test that record_failure persists the result."""
        aggregator = ResultAggregator()

        result = {'status_code': 'FAILED', 'message': 'Error'}
        aggregator.record_failure("PO123", result)

        mock_persist.assert_called_once_with("PO123", result)

    def test_record_failure_emits_telemetry(self) -> None:
        """Test that record_failure emits telemetry."""
        mock_telemetry = Mock(spec=TelemetryProvider)
        aggregator = ResultAggregator(telemetry=mock_telemetry)

        aggregator.record_failure("PO123", {'status_code': 'FAILED'})

        mock_telemetry.emit_status.assert_called_once()
        call_args = mock_telemetry.emit_status.call_args
        assert call_args[0][0] == StatusLevel.ERROR
        assert "PO123" in call_args[0][1]
        assert "FAILED" in call_args[0][1]

    def test_record_failure_with_error_message(self) -> None:
        """Test recording failure with error message."""
        mock_telemetry = Mock(spec=TelemetryProvider)
        aggregator = ResultAggregator(telemetry=mock_telemetry)

        aggregator.record_failure(
            "PO123",
            {'status_code': 'FAILED'},
            error="Connection timeout"
        )

        call_args = mock_telemetry.emit_status.call_args
        assert "Connection timeout" in call_args[0][1]


class TestResultAggregatorStatistics:
    """Test statistics tracking."""

    def test_get_statistics_empty(self) -> None:
        """Test statistics with no data."""
        aggregator = ResultAggregator()

        stats = aggregator.get_statistics()

        assert stats['total_processed'] == 0
        assert stats['successful'] == 0
        assert stats['failed'] == 0
        assert stats['success_rate'] == 0.0
        assert stats['elapsed_time_seconds'] == 0.0

    def test_get_statistics_with_data(self) -> None:
        """Test statistics with processed data."""
        aggregator = ResultAggregator()
        aggregator._successful_count = 8
        aggregator._failed_count = 2

        stats = aggregator.get_statistics()

        assert stats['total_processed'] == 10
        assert stats['successful'] == 8
        assert stats['failed'] == 2
        assert stats['success_rate'] == 80.0

    def test_get_statistics_with_elapsed_time(self) -> None:
        """Test statistics with elapsed time."""
        import time
        aggregator = ResultAggregator()
        start = time.perf_counter()
        aggregator._start_time = start
        time.sleep(0.1)  # Sleep 100ms

        stats = aggregator.get_statistics()

        assert stats['elapsed_time_seconds'] >= 0.1
        assert stats['elapsed_time_seconds'] < 1.0  # Should be reasonable

    def test_get_statistics_success_rate_calculation(self) -> None:
        """Test success rate calculation edge cases."""
        aggregator = ResultAggregator()

        # 0 total - should be 0%
        stats = aggregator.get_statistics()
        assert stats['success_rate'] == 0.0

        # All successful
        aggregator._successful_count = 10
        aggregator._failed_count = 0
        stats = aggregator.get_statistics()
        assert stats['success_rate'] == 100.0

        # All failed
        aggregator._successful_count = 0
        aggregator._failed_count = 10
        stats = aggregator.get_statistics()
        assert stats['success_rate'] == 0.0

    def test_set_run_start_time(self) -> None:
        """Test setting run start time."""
        aggregator = ResultAggregator()
        aggregator.set_run_start_time(123.456)

        assert aggregator._start_time == 123.456


class TestResultAggregatorProperties:
    """Test property accessors."""

    def test_successful_count_property(self) -> None:
        """Test successful_count property."""
        aggregator = ResultAggregator()
        aggregator._successful_count = 5

        assert aggregator.successful_count == 5

    def test_failed_count_property(self) -> None:
        """Test failed_count property."""
        aggregator = ResultAggregator()
        aggregator._failed_count = 3

        assert aggregator.failed_count == 3


class TestResultAggregatorBuildCSVUpdates:
    """Test CSV update building."""

    def test_build_csv_updates_basic(self) -> None:
        """Test building basic CSV updates."""
        aggregator = ResultAggregator()

        result = {
            'status_code': 'COMPLETED',
            'attachments_found': 5,
            'attachments_downloaded': 5,
            'attachment_names': ['file1.pdf', 'file2.pdf'],
            'final_folder': '/path/to/folder',
            'coupa_url': 'https://example.com/po/123'
        }

        updates = aggregator._build_csv_updates(result)

        assert updates['STATUS'] == 'COMPLETED'
        assert updates['ATTACHMENTS_FOUND'] == 5
        assert updates['ATTACHMENTS_DOWNLOADED'] == 5
        assert updates['AttachmentName'] == ['file1.pdf', 'file2.pdf']
        assert updates['DOWNLOAD_FOLDER'] == '/path/to/folder'
        assert updates['COUPA_URL'] == 'https://example.com/po/123'

    def test_build_csv_updates_with_supplier(self) -> None:
        """Test building CSV updates with supplier."""
        aggregator = ResultAggregator()

        result = {
            'status_code': 'COMPLETED',
            'supplier_name': 'Acme Corp'
        }

        updates = aggregator._build_csv_updates(result)

        assert updates['SUPPLIER'] == 'Acme Corp'

    def test_build_csv_updates_with_datetime(self) -> None:
        """Test building CSV updates with datetime."""
        from datetime import datetime
        aggregator = ResultAggregator()

        test_datetime = datetime(2024, 1, 15, 10, 30, 0)
        result = {
            'status_code': 'COMPLETED',
            'last_processed': test_datetime
        }

        updates = aggregator._build_csv_updates(result)

        assert updates['LAST_PROCESSED'] == '2024-01-15T10:30:00'

    def test_build_csv_updates_failed_status(self) -> None:
        """Test building CSV updates for failed status."""
        aggregator = ResultAggregator()

        result = {
            'status_code': 'FAILED',
            'message': 'Connection error',
            'attachments_found': 0,
            'attachments_downloaded': 0
        }

        updates = aggregator._build_csv_updates(result)

        assert updates['STATUS'] == 'FAILED'
        assert updates['ERROR_MESSAGE'] == 'Connection error'

    def test_build_csv_updates_attachment_names_string(self) -> None:
        """Test building CSV updates when attachment_names is string."""
        aggregator = ResultAggregator()

        result = {
            'status_code': 'COMPLETED',
            'attachment_names': 'file1.pdf;file2.pdf;file3.pdf'
        }

        updates = aggregator._build_csv_updates(result)

        assert updates['AttachmentName'] == ['file1.pdf', 'file2.pdf', 'file3.pdf']


class TestResultAggregatorFinalize:
    """Test finalization and cleanup."""

    def test_finalize_with_no_handlers(self) -> None:
        """Test finalize with no handlers."""
        aggregator = ResultAggregator()

        # Should not raise
        aggregator.finalize()

    def test_finalize_with_csv_handler(self) -> None:
        """Test finalize with CSV handler."""
        mock_csv = Mock()
        aggregator = ResultAggregator(csv_handler=mock_csv)

        aggregator.finalize()

        mock_csv.shutdown_csv_handler.assert_called_once()

    def test_finalize_with_sqlite_handler(self) -> None:
        """Test finalize with SQLite handler."""
        mock_sqlite = Mock()
        aggregator = ResultAggregator(sqlite_handler=mock_sqlite)

        aggregator.finalize()

        mock_sqlite.close.assert_called_once()

    def test_finalize_continues_on_csv_error(self) -> None:
        """Test that finalize continues on CSV error."""
        mock_csv = Mock()
        mock_csv.shutdown_csv_handler.side_effect = Exception("CSV error")
        mock_sqlite = Mock()

        aggregator = ResultAggregator(
            csv_handler=mock_csv,
            sqlite_handler=mock_sqlite
        )

        # Should not raise, should continue to SQLite
        aggregator.finalize()

        mock_csv.shutdown_csv_handler.assert_called_once()
        mock_sqlite.close.assert_called_once()

    def test_finalize_continues_on_sqlite_error(self) -> None:
        """Test that finalize continues on SQLite error."""
        mock_sqlite = Mock()
        mock_sqlite.close.side_effect = Exception("SQLite error")

        aggregator = ResultAggregator(sqlite_handler=mock_sqlite)

        # Should not raise
        aggregator.finalize()

        mock_sqlite.close.assert_called_once()


# Integration test with real file system
@pytest.mark.integration
class TestResultAggregatorRealFileSystem:
    """Integration tests with real file system."""

    def test_build_csv_updates_real_data(self) -> None:
        """Test building CSV updates with realistic data."""
        aggregator = ResultAggregator()

        result = {
            'po_number': 'PO123456',
            'status_code': 'COMPLETED',
            'supplier_name': 'Acme Corporation',
            'attachments_found': 3,
            'attachments_downloaded': 3,
            'attachment_names': ['spec.pdf', 'drawing.dwg', 'invoice.pdf'],
            'final_folder': '/tmp/test_downloads/PO123456_COMPLETED',
            'coupa_url': 'https://example.coupahost.com/order_headers/123456',
            'last_processed': '2024-01-15T10:30:00'
        }

        updates = aggregator._build_csv_updates(result)

        # Verify all expected fields are present
        assert len(updates) >= 7
        assert updates['STATUS'] == 'COMPLETED'
        assert updates['SUPPLIER'] == 'Acme Corporation'
        assert isinstance(updates['AttachmentName'], list)
        assert len(updates['AttachmentName']) == 3
