"""
Result aggregation and reporting for worker pool processing.

This module provides the ResultCollector class for aggregating
processing results with support for:
- Real-time result collection
- Summary report generation
- Error analysis and reporting
- Export to multiple formats
- Performance metrics tracking
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import structlog

from ..workers.models import POTask, TaskStatus

logger = structlog.get_logger(__name__)


@dataclass
class ProcessingResult:
    """Individual PO processing result."""
    po_number: str
    task_id: str
    status: str
    success: bool
    processing_time_seconds: Optional[float]
    downloaded_files: List[str]
    error_message: Optional[str]
    retry_count: int
    worker_id: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    metadata: Dict[str, Any]


@dataclass  
class ProcessingSummary:
    """Overall processing summary statistics."""
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    pending_tasks: int
    total_processing_time_seconds: float
    average_processing_time_seconds: float
    success_rate_percent: float
    total_files_downloaded: int
    total_retries: int
    start_time: datetime
    end_time: Optional[datetime]
    worker_statistics: Dict[str, Any]
    error_summary: Dict[str, int]


class ResultCollector:
    """
    Collector for aggregating and reporting worker pool results.
    
    Provides real-time result collection, summary generation,
    and export capabilities for processing analytics.
    """
    
    def __init__(self):
        """Initialize result collector."""
        self.results: Dict[str, ProcessingResult] = {}  # task_id -> result
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        
        # Statistics tracking
        self.total_tasks_submitted = 0
        self.worker_task_counts: Dict[str, int] = {}
        self.error_counts: Dict[str, int] = {}
        
        logger.debug("ResultCollector initialized")
    
    def add_task_submission(self, task: POTask) -> None:
        """
        Record task submission for tracking.
        
        Args:
            task: POTask that was submitted
        """
        self.total_tasks_submitted += 1
        
        # Initialize result with pending status
        result = ProcessingResult(
            po_number=task.po_number,
            task_id=task.task_id,
            status=TaskStatus.PENDING.value,
            success=False,
            processing_time_seconds=None,
            downloaded_files=[],
            error_message=None,
            retry_count=0,
            worker_id=None,
            start_time=None,
            end_time=None,
            metadata=task.metadata.copy()
        )
        
        self.results[task.task_id] = result
        
        logger.debug("Task submission recorded", 
                    po_number=task.po_number, task_id=task.task_id)
    
    def update_task_result(self, task: POTask, processing_result: Dict[str, Any]) -> None:
        """
        Update task result with completion data.
        
        Args:
            task: Completed POTask
            processing_result: Result data from worker processing
        """
        if task.task_id not in self.results:
            logger.warning("Task result not found for update", task_id=task.task_id)
            return
        
        result = self.results[task.task_id]
        
        # Update result with completion data
        result.status = task.status.value
        result.success = task.status == TaskStatus.COMPLETED
        result.processing_time_seconds = task.get_processing_time()
        result.retry_count = task.retry_count
        result.worker_id = task.assigned_worker_id
        result.start_time = task.started_time
        result.end_time = task.completed_time
        result.error_message = task.error_message
        
        # Extract files and additional data from processing result
        if processing_result:
            result.downloaded_files = processing_result.get('files', [])
            
            # Merge additional metadata
            if 'data' in processing_result:
                result.metadata.update(processing_result['data'])
        
        # Update worker statistics
        if result.worker_id:
            self.worker_task_counts[result.worker_id] = \
                self.worker_task_counts.get(result.worker_id, 0) + 1
        
        # Update error statistics
        if result.error_message:
            error_type = self._categorize_error(result.error_message)
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        logger.debug("Task result updated", 
                    po_number=result.po_number,
                    status=result.status,
                    success=result.success)
    
    def _categorize_error(self, error_message: str) -> str:
        """
        Categorize error message into error type.
        
        Args:
            error_message: Error message to categorize
            
        Returns:
            Error category string
        """
        error_lower = error_message.lower()
        
        # Common error patterns
        if 'not found' in error_lower or '404' in error_lower:
            return 'PO_NOT_FOUND'
        elif 'timeout' in error_lower:
            return 'TIMEOUT'
        elif 'authentication' in error_lower or 'login' in error_lower:
            return 'AUTHENTICATION'
        elif 'permission' in error_lower or 'access' in error_lower:
            return 'ACCESS_DENIED'
        elif 'network' in error_lower or 'connection' in error_lower:
            return 'NETWORK_ERROR'
        elif 'memory' in error_lower:
            return 'MEMORY_ERROR'
        elif 'browser' in error_lower or 'webdriver' in error_lower:
            return 'BROWSER_ERROR'
        else:
            return 'OTHER_ERROR'
    
    def mark_processing_complete(self) -> None:
        """Mark overall processing as complete."""
        self.end_time = datetime.now()
        logger.info("Processing marked as complete", 
                   total_duration=self.get_total_duration())
    
    def get_result(self, task_id: str) -> Optional[ProcessingResult]:
        """
        Get result for specific task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            ProcessingResult or None if not found
        """
        return self.results.get(task_id)
    
    def get_results_by_status(self, status: TaskStatus) -> List[ProcessingResult]:
        """
        Get all results with specific status.
        
        Args:
            status: Task status to filter by
            
        Returns:
            List of ProcessingResult instances
        """
        return [result for result in self.results.values() 
                if result.status == status.value]
    
    def get_successful_results(self) -> List[ProcessingResult]:
        """Get all successful processing results."""
        return [result for result in self.results.values() if result.success]
    
    def get_failed_results(self) -> List[ProcessingResult]:
        """Get all failed processing results."""
        return [result for result in self.results.values() 
                if not result.success and result.status != TaskStatus.CANCELLED.value]
    
    def get_summary(self) -> ProcessingSummary:
        """
        Generate comprehensive processing summary.
        
        Returns:
            ProcessingSummary with statistics
        """
        total_tasks = len(self.results)
        successful_tasks = len(self.get_successful_results())
        failed_tasks = len(self.get_failed_results())
        cancelled_tasks = len(self.get_results_by_status(TaskStatus.CANCELLED))
        pending_tasks = len(self.get_results_by_status(TaskStatus.PENDING))
        
        # Calculate processing times
        processing_times = [
            result.processing_time_seconds 
            for result in self.results.values() 
            if result.processing_time_seconds is not None
        ]
        
        total_processing_time = sum(processing_times) if processing_times else 0.0
        average_processing_time = (
            total_processing_time / len(processing_times) 
            if processing_times else 0.0
        )
        
        # Calculate success rate
        success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
        
        # Count total files downloaded
        total_files = sum(
            len(result.downloaded_files) 
            for result in self.results.values()
        )
        
        # Count total retries
        total_retries = sum(
            result.retry_count 
            for result in self.results.values()
        )
        
        # Generate worker statistics
        worker_stats = self._generate_worker_statistics()
        
        return ProcessingSummary(
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            cancelled_tasks=cancelled_tasks,
            pending_tasks=pending_tasks,
            total_processing_time_seconds=total_processing_time,
            average_processing_time_seconds=average_processing_time,
            success_rate_percent=round(success_rate, 2),
            total_files_downloaded=total_files,
            total_retries=total_retries,
            start_time=self.start_time,
            end_time=self.end_time,
            worker_statistics=worker_stats,
            error_summary=self.error_counts.copy()
        )
    
    def _generate_worker_statistics(self) -> Dict[str, Any]:
        """Generate detailed worker performance statistics."""
        worker_stats = {}
        
        for worker_id, task_count in self.worker_task_counts.items():
            # Get results for this worker
            worker_results = [
                result for result in self.results.values() 
                if result.worker_id == worker_id
            ]
            
            successful_count = sum(1 for r in worker_results if r.success)
            failed_count = sum(1 for r in worker_results if not r.success)
            
            # Calculate average processing time for this worker
            processing_times = [
                r.processing_time_seconds 
                for r in worker_results 
                if r.processing_time_seconds is not None
            ]
            
            avg_processing_time = (
                sum(processing_times) / len(processing_times) 
                if processing_times else 0.0
            )
            
            worker_stats[worker_id] = {
                'total_tasks': task_count,
                'successful_tasks': successful_count,
                'failed_tasks': failed_count,
                'success_rate_percent': round(successful_count / task_count * 100, 2) if task_count > 0 else 0,
                'average_processing_time_seconds': round(avg_processing_time, 2),
                'total_files_downloaded': sum(len(r.downloaded_files) for r in worker_results)
            }
        
        return worker_stats
    
    def get_total_duration(self) -> Optional[timedelta]:
        """Get total processing duration."""
        if self.end_time:
            return self.end_time - self.start_time
        else:
            return datetime.now() - self.start_time
    
    def export_to_json(self, file_path: Union[str, Path], 
                      include_summary: bool = True) -> None:
        """
        Export results to JSON file.
        
        Args:
            file_path: Output file path
            include_summary: Whether to include summary statistics
        """
        file_path = Path(file_path)
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'results': [asdict(result) for result in self.results.values()]
        }
        
        if include_summary:
            summary = self.get_summary()
            export_data['summary'] = asdict(summary)
        
        # Convert datetime objects to ISO strings for JSON serialization
        export_data = self._serialize_for_json(export_data)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Results exported to JSON", 
                       file=str(file_path), 
                       results_count=len(self.results))
            
        except Exception as e:
            logger.error("Failed to export to JSON", 
                        file=str(file_path), error=str(e))
            raise
    
    def export_to_csv(self, file_path: Union[str, Path]) -> None:
        """
        Export results to CSV file.
        
        Args:
            file_path: Output file path
        """
        file_path = Path(file_path)
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                if not self.results:
                    return
                
                # Get fieldnames from first result
                first_result = next(iter(self.results.values()))
                fieldnames = list(asdict(first_result).keys())
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in self.results.values():
                    # Convert result to dict and serialize datetime objects
                    result_dict = asdict(result)
                    result_dict = self._serialize_for_csv(result_dict)
                    writer.writerow(result_dict)
            
            logger.info("Results exported to CSV", 
                       file=str(file_path), 
                       results_count=len(self.results))
            
        except Exception as e:
            logger.error("Failed to export to CSV", 
                        file=str(file_path), error=str(e))
            raise
    
    def export_summary_report(self, file_path: Union[str, Path]) -> None:
        """
        Export formatted summary report.
        
        Args:
            file_path: Output file path
        """
        file_path = Path(file_path)
        summary = self.get_summary()
        
        report_lines = [
            "=== PO Processing Summary Report ===",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "=== Overall Statistics ===",
            f"Total Tasks: {summary.total_tasks}",
            f"Successful: {summary.successful_tasks}",
            f"Failed: {summary.failed_tasks}",
            f"Cancelled: {summary.cancelled_tasks}",
            f"Pending: {summary.pending_tasks}",
            f"Success Rate: {summary.success_rate_percent}%",
            "",
            f"Total Processing Time: {summary.total_processing_time_seconds:.2f} seconds",
            f"Average Processing Time: {summary.average_processing_time_seconds:.2f} seconds",
            f"Total Files Downloaded: {summary.total_files_downloaded}",
            f"Total Retries: {summary.total_retries}",
            "",
            f"Processing Period: {summary.start_time.strftime('%Y-%m-%d %H:%M:%S')} to " +
            (summary.end_time.strftime('%Y-%m-%d %H:%M:%S') if summary.end_time else "In Progress"),
            ""
        ]
        
        # Add worker statistics
        if summary.worker_statistics:
            report_lines.extend([
                "=== Worker Performance ===",
                f"{'Worker ID':<15} {'Tasks':<8} {'Success':<8} {'Failed':<8} {'Rate':<8} {'Avg Time':<10} {'Files':<8}",
                "-" * 75
            ])
            
            for worker_id, stats in summary.worker_statistics.items():
                report_lines.append(
                    f"{worker_id:<15} {stats['total_tasks']:<8} {stats['successful_tasks']:<8} "
                    f"{stats['failed_tasks']:<8} {stats['success_rate_percent']:>6.1f}% "
                    f"{stats['average_processing_time_seconds']:>8.2f}s {stats['total_files_downloaded']:<8}"
                )
            
            report_lines.append("")
        
        # Add error summary
        if summary.error_summary:
            report_lines.extend([
                "=== Error Summary ===",
                f"{'Error Type':<20} {'Count':<8}",
                "-" * 30
            ])
            
            for error_type, count in sorted(summary.error_summary.items(), 
                                          key=lambda x: x[1], reverse=True):
                report_lines.append(f"{error_type:<20} {count:<8}")
            
            report_lines.append("")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            logger.info("Summary report exported", file=str(file_path))
            
        except Exception as e:
            logger.error("Failed to export summary report", 
                        file=str(file_path), error=str(e))
            raise
    
    def _serialize_for_json(self, data: Any) -> Any:
        """Serialize data for JSON export (handle datetime objects)."""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {key: self._serialize_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize_for_json(item) for item in data]
        else:
            return data
    
    def _serialize_for_csv(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize data for CSV export (flatten complex types)."""
        serialized = {}
        
        for key, value in data.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat() if value else ''
            elif isinstance(value, list):
                serialized[key] = '; '.join(str(item) for item in value)
            elif isinstance(value, dict):
                serialized[key] = json.dumps(value) if value else ''
            else:
                serialized[key] = str(value) if value is not None else ''
        
        return serialized
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get collector statistics.
        
        Returns:
            Dictionary containing collector statistics
        """
        duration = self.get_total_duration()
        return {
            'total_results_tracked': len(self.results),
            'total_tasks_submitted': self.total_tasks_submitted,
            'unique_workers': len(self.worker_task_counts),
            'unique_error_types': len(self.error_counts),
            'processing_start_time': self.start_time.isoformat(),
            'processing_end_time': self.end_time.isoformat() if self.end_time else None,
            'total_duration_seconds': duration.total_seconds() if duration else None
        }
    
    def clear_results(self, older_than_hours: float = 24.0) -> int:
        """
        Clear old results to free memory.
        
        Args:
            older_than_hours: Remove results older than this many hours
            
        Returns:
            Number of results cleared
        """
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        cleared_count = 0
        
        for task_id in list(self.results.keys()):
            result = self.results[task_id]
            
            if (result.end_time and result.end_time < cutoff_time) or \
               (not result.end_time and result.start_time and result.start_time < cutoff_time):
                del self.results[task_id]
                cleared_count += 1
        
        logger.info("Old results cleared", count=cleared_count)
        return cleared_count