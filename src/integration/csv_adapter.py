"""
CSV to POTask conversion adapter.

This module provides the CSVAdapter class for converting CSV/Excel input
files to POTask instances with support for:
- Multiple input formats (CSV, Excel)
- Data validation and cleansing
- Priority assignment based on metadata
- Batch processing coordination
- Error handling and reporting
"""

import csv
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Union
import structlog
from datetime import datetime

from ..workers.models import POTask, TaskPriority

logger = structlog.get_logger(__name__)


class CSVAdapter:
    """
    Adapter for converting CSV/Excel files to POTask instances.
    
    Handles data validation, cleansing, and priority assignment
    for efficient worker pool processing.
    """
    
    def __init__(self, 
                 po_number_column: str = "PO Number",
                 priority_column: Optional[str] = None,
                 metadata_columns: Optional[List[str]] = None):
        """
        Initialize CSV adapter.
        
        Args:
            po_number_column: Name of column containing PO numbers
            priority_column: Optional column for priority assignment
            metadata_columns: Optional list of columns to include as metadata
        """
        self.po_number_column = po_number_column
        self.priority_column = priority_column
        self.metadata_columns = metadata_columns or []
        
        # Statistics
        self.total_rows_processed = 0
        self.valid_pos_created = 0
        self.invalid_rows_skipped = 0
        self.errors_encountered = 0
        
        logger.debug("CSVAdapter initialized", 
                    po_column=po_number_column,
                    priority_column=priority_column)
    
    def load_from_csv(self, file_path: Union[str, Path], 
                     encoding: str = 'utf-8',
                     delimiter: str = ',') -> List[POTask]:
        """
        Load POTasks from CSV file.
        
        Args:
            file_path: Path to CSV file
            encoding: File encoding
            delimiter: CSV delimiter
            
        Returns:
            List of POTask instances
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If required columns are missing
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        logger.info("Loading POTasks from CSV", file=str(file_path))
        
        try:
            # Read CSV using pandas for better handling
            df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter)
            
            # Validate required columns
            self._validate_columns(df)
            
            # Convert to POTasks
            po_tasks = self._dataframe_to_potasks(df)
            
            logger.info("CSV loading completed", 
                       file=str(file_path),
                       total_rows=len(df),
                       valid_tasks=len(po_tasks),
                       skipped=self.invalid_rows_skipped)
            
            return po_tasks
            
        except Exception as e:
            self.errors_encountered += 1
            logger.error("Failed to load CSV", file=str(file_path), error=str(e))
            raise
    
    def load_from_excel(self, file_path: Union[str, Path], 
                                              sheet_name: Union[str, int] = 0,
                       header_row: int = 0) -> List[POTask]:
        """
        Load POTasks from Excel file.
        
        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name or index to read
            header_row: Row containing headers (0-indexed)
            
        Returns:
            List of POTask instances
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If required columns are missing
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")
        
        logger.info("Loading POTasks from Excel", 
                   file=str(file_path), sheet=str(sheet_name))
        
        try:
            # Read Excel using pandas
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
            
            # Validate required columns
            self._validate_columns(df)
            
            # Convert to POTasks
            po_tasks = self._dataframe_to_potasks(df)
            
            logger.info("Excel loading completed", 
                       file=str(file_path),
                       total_rows=len(df),
                       valid_tasks=len(po_tasks),
                       skipped=self.invalid_rows_skipped)
            
            return po_tasks
            
        except Exception as e:
            self.errors_encountered += 1
            logger.error("Failed to load Excel", file=str(file_path), error=str(e))
            raise
    
    def load_from_dataframe(self, df: pd.DataFrame) -> List[POTask]:
        """
        Load POTasks from pandas DataFrame.
        
        Args:
            df: DataFrame containing PO data
            
        Returns:
            List of POTask instances
        """
        logger.debug("Loading POTasks from DataFrame", rows=len(df))
        
        try:
            # Validate required columns
            self._validate_columns(df)
            
            # Convert to POTasks
            po_tasks = self._dataframe_to_potasks(df)
            
            logger.debug("DataFrame loading completed", 
                        total_rows=len(df),
                        valid_tasks=len(po_tasks))
            
            return po_tasks
            
        except Exception as e:
            self.errors_encountered += 1
            logger.error("Failed to load DataFrame", error=str(e))
            raise
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Validate that required columns exist in DataFrame.
        
        Args:
            df: DataFrame to validate
            
        Raises:
            ValueError: If required columns are missing
        """
        missing_columns = []
        
        # Check PO number column
        if self.po_number_column not in df.columns:
            missing_columns.append(self.po_number_column)
        
        # Check priority column if specified
        if self.priority_column and self.priority_column not in df.columns:
            logger.warning("Priority column not found, using default priority", 
                          column=self.priority_column)
        
        if missing_columns:
            available_columns = list(df.columns)
            raise ValueError(
                f"Required columns missing: {missing_columns}. "
                f"Available columns: {available_columns}"
            )
        
        logger.debug("Column validation passed", 
                    po_column=self.po_number_column,
                    available_columns=list(df.columns))
    
    def _dataframe_to_potasks(self, df: pd.DataFrame) -> List[POTask]:
        """
        Convert DataFrame rows to POTask instances.
        
        Args:
            df: DataFrame containing PO data
            
        Returns:
            List of POTask instances
        """
        po_tasks = []
        
        for index, row in df.iterrows():
            self.total_rows_processed += 1
            
            try:
                # Extract PO number
                po_number = self._extract_po_number(row)
                
                if not po_number:
                    logger.warning("Skipping row with empty PO number", row_index=index)
                    self.invalid_rows_skipped += 1
                    continue
                
                # Extract priority
                priority = self._extract_priority(row)
                
                # Extract metadata
                metadata = self._extract_metadata(row)
                
                # Create POTask
                po_task = POTask(
                    po_number=po_number,
                    priority=priority,
                    metadata=metadata
                )
                
                po_tasks.append(po_task)
                self.valid_pos_created += 1
                
                logger.debug("POTask created", 
                           po_number=po_number, 
                           priority=priority.value,
                           row_index=index)
                
            except Exception as e:
                logger.warning("Failed to process row", 
                              row_index=index, error=str(e))
                self.invalid_rows_skipped += 1
                continue
        
        return po_tasks
    
    def _extract_po_number(self, row: pd.Series) -> Optional[str]:
        """
        Extract and validate PO number from row.
        
        Args:
            row: DataFrame row
            
        Returns:
            Cleaned PO number or None if invalid
        """
        try:
            po_value = row[self.po_number_column]
            
            # Handle NaN/None values
            if pd.isna(po_value):
                return None
            
            # Convert to string and clean
            po_number = str(po_value).strip()
            
            # Basic validation
            if len(po_number) == 0:
                return None
            
            # Remove common prefixes/suffixes if needed
            po_number = po_number.upper()
            
            # Additional validation can be added here
            # e.g., regex pattern matching, length checks
            
            return po_number
            
        except Exception as e:
            logger.warning("Error extracting PO number", error=str(e))
            return None
    
    def _extract_priority(self, row: pd.Series) -> TaskPriority:
        """
        Extract and map priority from row.
        
        Args:
            row: DataFrame row
            
        Returns:
            TaskPriority enum value
        """
        if not self.priority_column or self.priority_column not in row:
            return TaskPriority.NORMAL
        
        try:
            priority_value = row[self.priority_column]
            
            # Handle NaN/None values
            if pd.isna(priority_value):
                return TaskPriority.NORMAL
            
            # Convert to string for mapping
            priority_str = str(priority_value).strip().upper()
            
            # Map common priority values
            priority_mapping = {
                'URGENT': TaskPriority.URGENT,
                'HIGH': TaskPriority.HIGH,
                'NORMAL': TaskPriority.NORMAL,
                'LOW': TaskPriority.LOW,
                '4': TaskPriority.URGENT,
                '3': TaskPriority.HIGH,
                '2': TaskPriority.NORMAL,
                '1': TaskPriority.LOW,
                'CRITICAL': TaskPriority.URGENT,
                'IMPORTANT': TaskPriority.HIGH,
                'STANDARD': TaskPriority.NORMAL,
                'DEFERRED': TaskPriority.LOW
            }
            
            return priority_mapping.get(priority_str, TaskPriority.NORMAL)
            
        except Exception as e:
            logger.warning("Error extracting priority, using default", error=str(e))
            return TaskPriority.NORMAL
    
    def _extract_metadata(self, row: pd.Series) -> Dict[str, Any]:
        """
        Extract metadata from specified columns.
        
        Args:
            row: DataFrame row
            
        Returns:
            Dictionary containing metadata
        """
        metadata = {}
        
        # Add row index for tracking
        metadata['source_row_index'] = row.name
        metadata['import_timestamp'] = datetime.now().isoformat()
        
        # Extract specified metadata columns
        for column in self.metadata_columns:
            if column in row:
                value = row[column]
                
                # Handle NaN values
                if not pd.isna(value):
                    metadata[column] = value
        
        return metadata
    
    def create_batch_iterator(self, file_path: Union[str, Path], 
                             batch_size: int = 100) -> Iterator[List[POTask]]:
        """
        Create iterator for processing large files in batches.
        
        Args:
            file_path: Path to CSV/Excel file
            batch_size: Number of POTasks per batch
            
        Yields:
            Batches of POTask instances
        """
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.csv':
            yield from self._csv_batch_iterator(file_path, batch_size)
        elif file_path.suffix.lower() in ['.xlsx', '.xls']:
            yield from self._excel_batch_iterator(file_path, batch_size)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    def _csv_batch_iterator(self, file_path: Path, 
                           batch_size: int) -> Iterator[List[POTask]]:
        """
        Iterator for CSV files in batches.
        
        Args:
            file_path: Path to CSV file
            batch_size: Number of rows per batch
            
        Yields:
            Batches of POTask instances
        """
        logger.info("Starting CSV batch processing", 
                   file=str(file_path), batch_size=batch_size)
        
        try:
            # Read CSV in chunks
            chunk_reader = pd.read_csv(file_path, chunksize=batch_size)
            
            for chunk_num, chunk_df in enumerate(chunk_reader):
                logger.debug("Processing CSV batch", 
                           batch=chunk_num, rows=len(chunk_df))
                
                # Validate columns for first chunk
                if chunk_num == 0:
                    self._validate_columns(chunk_df)
                
                # Convert chunk to POTasks
                po_tasks = self._dataframe_to_potasks(chunk_df)
                
                if po_tasks:
                    yield po_tasks
                
        except Exception as e:
            logger.error("Error in CSV batch processing", 
                        file=str(file_path), error=str(e))
            raise
    
    def _excel_batch_iterator(self, file_path: Path, 
                             batch_size: int) -> Iterator[List[POTask]]:
        """
        Iterator for Excel files in batches.
        
        Note: Excel files are loaded entirely into memory first,
        then processed in batches.
        
        Args:
            file_path: Path to Excel file
            batch_size: Number of rows per batch
            
        Yields:
            Batches of POTask instances
        """
        logger.info("Starting Excel batch processing", 
                   file=str(file_path), batch_size=batch_size)
        
        try:
            # Load entire Excel file (limitation of pandas)
            df = pd.read_excel(file_path)
            self._validate_columns(df)
            
            # Process in batches
            for start_idx in range(0, len(df), batch_size):
                end_idx = min(start_idx + batch_size, len(df))
                batch_df = df.iloc[start_idx:end_idx]
                
                logger.debug("Processing Excel batch", 
                           start=start_idx, end=end_idx, rows=len(batch_df))
                
                # Convert batch to POTasks
                po_tasks = self._dataframe_to_potasks(batch_df)
                
                if po_tasks:
                    yield po_tasks
                
        except Exception as e:
            logger.error("Error in Excel batch processing", 
                        file=str(file_path), error=str(e))
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get adapter processing statistics.
        
        Returns:
            Dictionary containing processing statistics
        """
        return {
            'total_rows_processed': self.total_rows_processed,
            'valid_pos_created': self.valid_pos_created,
            'invalid_rows_skipped': self.invalid_rows_skipped,
            'errors_encountered': self.errors_encountered,
            'success_rate_percent': (
                (self.valid_pos_created / self.total_rows_processed * 100) 
                if self.total_rows_processed > 0 else 0
            ),
            'configuration': {
                'po_number_column': self.po_number_column,
                'priority_column': self.priority_column,
                'metadata_columns': self.metadata_columns
            }
        }
    
    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self.total_rows_processed = 0
        self.valid_pos_created = 0
        self.invalid_rows_skipped = 0
        self.errors_encountered = 0
        
        logger.debug("Adapter statistics reset")
    
    @staticmethod
    def detect_file_format(file_path: Union[str, Path]) -> str:
        """
        Detect file format based on extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            File format ('csv', 'excel', or 'unknown')
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        if extension == '.csv':
            return 'csv'
        elif extension in ['.xlsx', '.xls']:
            return 'excel'
        else:
            return 'unknown'
    
    @staticmethod
    def suggest_columns(file_path: Union[str, Path], 
                                              sample_rows: int = 5) -> Dict[str, Any]:
        """
        Analyze file and suggest column mappings.
        
        Args:
            file_path: Path to file
            sample_rows: Number of rows to sample
            
        Returns:
            Dictionary with suggested column mappings
        """
        file_path = Path(file_path)
        
        try:
            # Load sample data
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path, nrows=sample_rows)
            else:
                df = pd.read_excel(file_path, nrows=sample_rows)
            
            columns = list(df.columns)
            
            # Suggest PO number columns
            po_candidates = [col for col in columns 
                           if any(keyword in col.lower() 
                                 for keyword in ['po', 'purchase', 'order', 'number'])]
            
            # Suggest priority columns
            priority_candidates = [col for col in columns 
                                 if any(keyword in col.lower() 
                                       for keyword in ['priority', 'urgent', 'level'])]
            
            # Suggest metadata columns (exclude PO and priority candidates)
            metadata_candidates = [col for col in columns 
                                 if col not in po_candidates + priority_candidates]
            
            return {
                'all_columns': columns,
                'po_number_candidates': po_candidates,
                'priority_candidates': priority_candidates,
                'metadata_candidates': metadata_candidates,
                'sample_data': df.to_dict('records')
            }
            
        except Exception as e:
            logger.error("Failed to analyze file", file=str(file_path), error=str(e))
            return {
                'all_columns': [],
                'po_number_candidates': [],
                'priority_candidates': [],
                'metadata_candidates': [],
                'error': str(e)
            }