"""
Main integration adapter for coordinating worker pool operations.

This module provides the WorkerPoolAdapter class that serves as the
primary interface for integrating worker pool operations with external
systems, coordinating data flow, result aggregation, and progress tracking.
"""

from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from datetime import datetime
from pathlib import Path
import asyncio
import structlog

from .csv_adapter import CSVAdapter
from .result_collector import ResultCollector, ProcessingResult
from .progress_tracker import ProgressTracker, ProgressEvent, ProgressSnapshot
from ..workers.persistent_pool import PersistentWorkerPool
from ..workers.models import POTask, TaskStatus, PoolConfig, TaskPriority

logger = structlog.get_logger(__name__)


class WorkerPoolAdapter:
    """
    Main adapter for coordinating worker pool operations.
    
    Provides unified interface for:
    - Input data processing
    - Worker pool coordination  
    - Progress monitoring
    - Result aggregation
    - Integration with external systems
    """
    
    def __init__(self, 
                 initial_workers: int = 3,
                 max_workers: int = 10,
                 enable_auto_scaling: bool = True,
                 memory_limit_mb: int = 4096):
        """
        Initialize worker pool adapter.
        
        Args:
            initial_workers: Initial number of workers to start
            max_workers: Maximum number of workers to scale to
            enable_auto_scaling: Whether to enable automatic scaling
            memory_limit_mb: Memory limit for scaling decisions
        """
        # Core components
        # Create pool configuration
        pool_config = PoolConfig()
        pool_config.worker_count = initial_workers
        pool_config.memory_threshold = memory_limit_mb / 1024  # Convert MB to ratio
        pool_config.headless_mode = True
        
        self.worker_pool = PersistentWorkerPool(config=pool_config)
        
        self.csv_adapter = CSVAdapter()
        self.result_collector = ResultCollector()
        self.progress_tracker = ProgressTracker()
        
        # Configuration
        self.initial_workers = initial_workers
        self.max_workers = max_workers
        self.enable_auto_scaling = enable_auto_scaling
        
        # State tracking
        self._is_initialized = False
        self._is_running = False
        self._shutdown_complete = False
        
        # Integration hooks
        self.progress_callbacks: List[Callable[[ProgressEvent], None]] = []
        self.completion_callbacks: List[Callable[[ProcessingResult], None]] = []
        
        logger.info("WorkerPoolAdapter initialized",
                   initial_workers=initial_workers,
                   max_workers=max_workers,
                   auto_scaling=enable_auto_scaling)
    
    async def initialize(self, coupa_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize adapter and worker pool.
        
        Args:
            coupa_config: Coupa system configuration
        """
        if self._is_initialized:
            logger.warning("Adapter already initialized")
            return
        
        try:
            # Start worker pool
            await self.worker_pool.start()
            
            # Setup progress event integration
            self.progress_tracker.add_event_listener(self._handle_progress_event)
            
            self._is_initialized = True
            logger.info("WorkerPoolAdapter initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize adapter", error=str(e))
            raise
    
    async def process_csv_file(self, 
                              file_path: Union[str, Path],
                              output_dir: Optional[Union[str, Path]] = None,
                              batch_size: int = 50,
                              enable_progress_tracking: bool = True) -> Dict[str, Any]:
        """
        Process PO data from CSV file through worker pool.
        
        Args:
            file_path: Path to CSV file containing PO data
            output_dir: Directory for downloaded files
            batch_size: Number of tasks to process in each batch
            enable_progress_tracking: Whether to track progress
            
        Returns:
            Processing results summary
        """
        if not self._is_initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        logger.info("Starting CSV file processing",
                   file=str(file_path),
                   batch_size=batch_size)
        
        try:
            # Load and validate CSV data
            po_tasks = await self._load_csv_data(file_path, Path(output_dir) if output_dir else None)
            
            if not po_tasks:
                logger.warning("No valid PO tasks found in CSV file")
                return {
                    'success': False,
                    'message': 'No valid PO tasks found',
                    'total_tasks': 0,
                    'results': []
                }
            
            # Process tasks through worker pool
            results = await self._process_tasks_batch(
                po_tasks, 
                batch_size=batch_size,
                enable_progress_tracking=enable_progress_tracking
            )
            
            return results
            
        except Exception as e:
            logger.error("CSV processing failed", file=str(file_path), error=str(e))
            raise
    
    async def process_tasks(self, 
                           tasks: List[POTask],
                           enable_progress_tracking: bool = True) -> Dict[str, Any]:
        """
        Process list of POTask objects through worker pool.
        
        Args:
            tasks: List of POTask objects to process
            enable_progress_tracking: Whether to track progress
            
        Returns:
            Processing results summary
        """
        if not self._is_initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")
        
        if not tasks:
            logger.warning("No tasks provided for processing")
            return {
                'success': True,
                'message': 'No tasks to process',
                'total_tasks': 0,
                'results': []
            }
        
        logger.info("Starting task processing", task_count=len(tasks))
        
        try:
            results = await self._process_tasks_batch(
                tasks,
                enable_progress_tracking=enable_progress_tracking
            )
            return results
            
        except Exception as e:
            logger.error("Task processing failed", error=str(e))
            raise
    
    def add_progress_callback(self, callback: Callable[[ProgressEvent], None]) -> None:
        """
        Add callback for progress events.
        
        Args:
            callback: Function to call on progress events
        """
        self.progress_callbacks.append(callback)
        logger.debug("Progress callback added", total_callbacks=len(self.progress_callbacks))
    
    def add_completion_callback(self, callback: Callable[[ProcessingResult], None]) -> None:
        """
        Add callback for task completion.
        
        Args:
            callback: Function to call on task completion
        """
        self.completion_callbacks.append(callback)
        logger.debug("Completion callback added", total_callbacks=len(self.completion_callbacks))
    
    def get_progress_snapshot(self) -> ProgressSnapshot:
        """Get current progress snapshot."""
        return self.progress_tracker.get_snapshot()
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """Get comprehensive processing summary."""
        summary = self.result_collector.get_summary()
        progress = self.progress_tracker.get_snapshot()
        worker_status = self.worker_pool.get_status()
        
        return {
            'processing_summary': summary,
            'current_progress': progress,
            'worker_pool_status': worker_status,
            'integration_stats': {
                'adapter_initialized': self._is_initialized,
                'adapter_running': self._is_running,
                'progress_callbacks': len(self.progress_callbacks),
                'completion_callbacks': len(self.completion_callbacks)
            }
        }
    
    def export_results(self, 
                      output_dir: Union[str, Path],
                      formats: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Export results to various formats.
        
        Args:
            output_dir: Directory to save exports
            formats: List of formats ('json', 'csv', 'summary')
            
        Returns:
            Dictionary mapping format to file path
        """
        if formats is None:
            formats = ['json', 'csv', 'summary']
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        exported_files = {}
        
        try:
            if 'json' in formats:
                json_file = output_dir / f"results_{timestamp}.json"
                self.result_collector.export_to_json(json_file)
                exported_files['json'] = str(json_file)
            
            if 'csv' in formats:
                csv_file = output_dir / f"results_{timestamp}.csv"
                self.result_collector.export_to_csv(csv_file)
                exported_files['csv'] = str(csv_file)
            
            if 'summary' in formats:
                summary_file = output_dir / f"summary_{timestamp}.txt"
                self.result_collector.export_summary_report(summary_file)
                exported_files['summary'] = str(summary_file)
            
            # Export progress data
            progress_file = output_dir / f"progress_{timestamp}.json"
            self.progress_tracker.save_progress(progress_file)
            exported_files['progress'] = str(progress_file)
            
            logger.info("Results exported", formats=formats, output_dir=str(output_dir))
            return exported_files
            
        except Exception as e:
            logger.error("Failed to export results", error=str(e))
            raise
    
    async def shutdown(self, timeout_seconds: float = 30.0) -> None:
        """
        Gracefully shutdown adapter and worker pool.
        
        Args:
            timeout_seconds: Maximum time to wait for shutdown
        """
        if self._shutdown_complete:
            logger.info("Adapter already shutdown")
            return
        
        logger.info("Starting adapter shutdown", timeout=timeout_seconds)
        
        try:
            # Mark processing as complete
            self.progress_tracker.mark_processing_complete()
            self.result_collector.mark_processing_complete()
            
            # Shutdown worker pool
            await self.worker_pool.shutdown()
            
            self._is_running = False
            self._shutdown_complete = True
            
            logger.info("Adapter shutdown completed")
            
        except Exception as e:
            logger.error("Adapter shutdown failed", error=str(e))
            raise
    
    async def _load_csv_data(self, 
                           file_path: Path, 
                           output_dir: Optional[Path]) -> List[POTask]:
        """Load and convert CSV data to POTask objects."""
        try:
            # Load CSV data directly to POTasks
            po_tasks = self.csv_adapter.load_from_csv(str(file_path))
            
            logger.info("CSV data loaded", 
                       file=str(file_path),
                       tasks_created=len(po_tasks))
            
            return po_tasks
            
        except Exception as e:
            logger.error("Failed to load CSV data", file=str(file_path), error=str(e))
            raise
    
    async def _process_tasks_batch(self, 
                                 tasks: List[POTask],
                                 batch_size: int = 50,
                                 enable_progress_tracking: bool = True) -> Dict[str, Any]:
        """Process tasks through worker pool with batching."""
        self._is_running = True
        total_tasks = len(tasks)
        
        try:
            # Submit all tasks for tracking
            for task in tasks:
                if enable_progress_tracking:
                    self.progress_tracker.track_task_submission(task)
                self.result_collector.add_task_submission(task)
            
            # Start worker pool if not already running
            if not self.worker_pool._is_running:
                await self.worker_pool.start()
            
            # Process tasks in batches
            processed_count = 0
            for i in range(0, total_tasks, batch_size):
                batch = tasks[i:i + batch_size]
                
                logger.info("Processing batch", 
                           batch_number=i // batch_size + 1,
                           batch_size=len(batch),
                           total_progress=f"{processed_count}/{total_tasks}")
                
                # Submit batch to worker pool
                batch_results = await self._submit_batch(batch)
                
                # Update tracking
                for task, result in zip(batch, batch_results):
                    if enable_progress_tracking:
                        self._update_task_tracking(task, result)
                    self.result_collector.update_task_result(task, result)
                
                processed_count += len(batch)
                
                # Track batch completion
                if enable_progress_tracking:
                    self.progress_tracker.track_batch_completed(len(batch), f"batch_{i // batch_size + 1}")
            
            # Generate final results
            summary = self.result_collector.get_summary()
            
            return {
                'success': True,
                'total_tasks': total_tasks,
                'successful_tasks': summary.successful_tasks,
                'failed_tasks': summary.failed_tasks,
                'cancelled_tasks': summary.cancelled_tasks,
                'success_rate_percent': summary.success_rate_percent,
                'total_processing_time_seconds': summary.total_processing_time_seconds,
                'total_files_downloaded': summary.total_files_downloaded,
                'worker_statistics': summary.worker_statistics,
                'error_summary': summary.error_summary
            }
            
        except Exception as e:
            logger.error("Batch processing failed", error=str(e))
            raise
        finally:
            self._is_running = False
    
    async def _submit_batch(self, batch: List[POTask]) -> List[Dict[str, Any]]:
        """Submit batch of tasks to worker pool."""
        # Submit tasks to worker pool
        submitted_tasks = []
        for task in batch:
            task_handle = self.worker_pool.submit_task(
                po_number=task.po_number,
                priority=task.priority,
                metadata=task.metadata
            )
            submitted_tasks.append((task, task_handle))
        
                # Wait for completion
        results = []
        for task, task_handle in submitted_tasks:
            # Wait for task completion (simplified - in real implementation 
            # would use proper async coordination)
            result = await self._wait_for_task_completion(task, task_handle)
            results.append(result)
        
        return results
    
    async def _wait_for_task_completion(self, task: POTask, task_handle) -> Dict[str, Any]:
        """Wait for individual task completion."""
        # Simplified implementation - in real version would use 
        # proper async coordination with worker pool
        max_wait_seconds = 300  # 5 minutes
        check_interval = 1.0
        
        waited = 0.0
        while waited < max_wait_seconds:
            # Check if task is complete using task handle
            if task_handle.is_completed():
                # Get result from task handle
                result_data = task_handle.get_result()
                return {
                    'success': result_data.get('success', False),
                    'status': result_data.get('status', 'unknown'),
                    'files': result_data.get('files', []),
                    'data': result_data.get('data', {}),
                    'processing_time': result_data.get('processing_time')
                }
            
            await asyncio.sleep(check_interval)
            waited += check_interval
        
        # Timeout
        return {
            'success': False,
            'status': 'timeout',
            'files': [],
            'data': {},
            'processing_time': None,
            'error': 'Task completion timeout'
        }
    
    def _update_task_tracking(self, task: POTask, result: Dict[str, Any]) -> None:
        """Update task tracking with completion result."""
        worker_id = task.assigned_worker_id
        
        if result['success']:
            self.progress_tracker.track_task_completed(task, worker_id)
        else:
            # Update task with error information
            task.error_message = result.get('error', 'Unknown error')
            task.status = TaskStatus.FAILED
            self.progress_tracker.track_task_completed(task, worker_id)
    
    def _handle_progress_event(self, event: ProgressEvent) -> None:
        """Handle progress events and notify callbacks."""
        # Notify registered progress callbacks
        for callback in self.progress_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.warning("Progress callback failed", error=str(e))
        
        # Handle completion events for completion callbacks
        if event.event_type.value in ['task_completed', 'task_failed']:
            task_id = event.task_id
            if task_id:
                result = self.result_collector.get_result(task_id)
                if result:
                    for callback in self.completion_callbacks:
                        try:
                            callback(result)
                        except Exception as e:
                            logger.warning("Completion callback failed", error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive adapter statistics.
        
        Returns:
            Dictionary containing adapter statistics
        """
        return {
            'adapter_state': {
                'initialized': self._is_initialized,
                'running': self._is_running,
                'shutdown_complete': self._shutdown_complete
            },
            'worker_pool': self.worker_pool.get_status() if self._is_initialized else {},
            'result_collector': self.result_collector.get_stats(),
            'progress_tracker': self.progress_tracker.get_stats(),
            'integration_hooks': {
                'progress_callbacks': len(self.progress_callbacks),
                'completion_callbacks': len(self.completion_callbacks)
            }
        }
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        if not self._is_initialized:
            await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()