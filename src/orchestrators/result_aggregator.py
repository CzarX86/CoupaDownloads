"""
Result Aggregator module.

Handles aggregation and persistence of processing results from multiple workers.
Extracted from MainApp to improve separation of concerns.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

import pandas as pd

from .core.csv_handler import CSVHandler
from .core.sqlite_handler import SQLiteHandler
from .core.telemetry import TelemetryProvider
from .core.status import StatusLevel

logger = logging.getLogger(__name__)


class ResultAggregator:
    """
    Aggregates and persists processing results from workers.
    
    Responsibilities:
    - Collect results from sequential/parallel processing
    - Update CSV with final results
    - Merge SQLite data back to CSV
    - Track processing statistics
    
    This class was extracted from MainApp to reduce class complexity
    and improve testability.
    """
    
    def __init__(
        self,
        csv_handler: Optional[CSVHandler] = None,
        sqlite_handler: Optional[SQLiteHandler] = None,
        telemetry: Optional[TelemetryProvider] = None,
    ):
        """
        Initialize result aggregator.
        
        Args:
            csv_handler: CSV handler for file-based persistence
            sqlite_handler: SQLite handler for database persistence
            telemetry: Telemetry provider for status updates
        """
        self.csv_handler = csv_handler
        self.sqlite_handler = sqlite_handler
        self.telemetry = telemetry
        
        # Processing statistics
        self._successful_count = 0
        self._failed_count = 0
        self._start_time: Optional[float] = None
    
    def set_run_start_time(self, start_time: float) -> None:
        """
        Set the processing run start time.
        
        Args:
            start_time: Start time from time.perf_counter()
        """
        self._start_time = start_time
    
    def record_success(self, po_number: str, result: Dict[str, Any]) -> None:
        """
        Record a successful PO processing result.
        
        Args:
            po_number: PO number that was processed
            result: Processing result dictionary
        """
        self._successful_count += 1
        self._persist_result(po_number, result)
        
        if self.telemetry:
            self.telemetry.emit_status(
                StatusLevel.SUCCESS,
                f"✅ {po_number}: {result.get('status_code', 'COMPLETED')}"
            )
    
    def record_failure(self, po_number: str, result: Dict[str, Any], error: Optional[str] = None) -> None:
        """
        Record a failed PO processing result.
        
        Args:
            po_number: PO number that failed
            result: Processing result dictionary
            error: Optional error message
        """
        self._failed_count += 1
        self._persist_result(po_number, result)
        
        if self.telemetry:
            self.telemetry.emit_status(
                StatusLevel.ERROR,
                f"❌ {po_number}: {result.get('status_code', 'FAILED')} - {error or result.get('message', '')}"
            )
    
    def _persist_result(self, po_number: str, result: Dict[str, Any]) -> None:
        """
        Persist result to CSV/SQLite.
        
        Args:
            po_number: PO number
            result: Result dictionary
        """
        try:
            # Update SQLite (preferred for parallel processing)
            if self.sqlite_handler:
                self.sqlite_handler.update_record(po_number, result)
            
            # Update CSV (for incremental safety or if SQLite not available)
            if self.csv_handler and self.csv_handler.is_initialized():
                csv_updates = self._build_csv_updates(result)
                self.csv_handler.update_record(po_number, csv_updates)
                
        except Exception as e:
            logger.error(
                "Failed to persist result",
                extra={"po_number": po_number, "error": str(e)}
            )
    
    def _build_csv_updates(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate processing result into CSV column updates.
        
        Args:
            result: Processing result dictionary
            
        Returns:
            Dictionary of CSV column updates
        """
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
        
        # Optional fields
        supplier_name = result.get('supplier_name')
        if supplier_name:
            updates['SUPPLIER'] = supplier_name
        
        last_processed = result.get('last_processed')
        if isinstance(last_processed, datetime):
            updates['LAST_PROCESSED'] = last_processed.isoformat()
        elif isinstance(last_processed, str) and last_processed:
            updates['LAST_PROCESSED'] = last_processed
        
        return updates
    
    def merge_sqlite_to_csv(self, output_path: Path, input_path: Path) -> None:
        """
        Merge processed data from SQLite back to CSV file.
        
        Args:
            output_path: Path for output CSV file
            input_path: Path to original input CSV
        """
        if not self.sqlite_handler:
            logger.info("SQLite handler not available, skipping merge")
            return
        
        try:
            logger.info("Merging SQLite data to CSV", extra={"output": str(output_path)})
            
            # Read original CSV
            df = pd.read_csv(input_path)
            
            # Get processed data from SQLite
            processed_data = self.sqlite_handler.get_all_records()
            
            if not processed_data:
                logger.info("No processed records to merge")
                return
            
            # Convert to DataFrame
            df_sqlite = pd.DataFrame(processed_data)
            
            # Map SQLite columns to CSV columns
            column_mapping = {
                'status': 'STATUS',
                'supplier': 'SUPPLIER',
                'attachments_found': 'ATTACHMENTS_FOUND',
                'attachments_downloaded': 'ATTACHMENTS_DOWNLOADED',
                'attachment_names': 'AttachmentName',
                'last_processed': 'LAST_PROCESSED',
                'error_message': 'ERROR_MESSAGE',
                'download_folder': 'DOWNLOAD_FOLDER',
                'coupa_url': 'COUPA_URL',
            }
            
            # Update DataFrame with SQLite data
            for sqlite_col, csv_col in column_mapping.items():
                if sqlite_col in df_sqlite.columns and csv_col in df.columns:
                    # Create mapping from PO number to value
                    mapping = df_sqlite.set_index('po_number')[sqlite_col].to_dict()
                    df[csv_col] = df['PO_NUMBER'].map(mapping).fillna(df[csv_col])
            
            # Save to output path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_path, index=False)
            
            logger.info(
                "CSV merge completed",
                extra={"records_merged": len(processed_data), "output": str(output_path)}
            )
            
        except Exception as e:
            logger.error("Failed to merge SQLite to CSV", extra={"error": str(e)})
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        elapsed_time = 0.0
        if self._start_time:
            elapsed_time = time.perf_counter() - self._start_time
        
        total = self._successful_count + self._failed_count
        success_rate = (self._successful_count / total * 100) if total > 0 else 0.0
        
        return {
            'total_processed': total,
            'successful': self._successful_count,
            'failed': self._failed_count,
            'success_rate': round(success_rate, 2),
            'elapsed_time_seconds': round(elapsed_time, 2),
        }
    
    def finalize(self) -> None:
        """
        Finalize aggregation and cleanup resources.
        """
        logger.info("Finalizing result aggregator", extra=self.get_statistics())
        
        # Shutdown handlers
        if self.csv_handler:
            try:
                self.csv_handler.shutdown_csv_handler()
            except Exception as e:
                logger.warning("Error shutting down CSV handler", extra={"error": str(e)})
        
        if self.sqlite_handler:
            try:
                self.sqlite_handler.close()
            except Exception as e:
                logger.warning("Error closing SQLite handler", extra={"error": str(e)})
    
    @property
    def successful_count(self) -> int:
        """Get count of successful operations."""
        return self._successful_count
    
    @property
    def failed_count(self) -> int:
        """Get count of failed operations."""
        return self._failed_count
