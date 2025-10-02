"""
TaskQueue service for efficient task distribution and load balancing.
Manages PO task queuing, prioritization, and assignment to workers.
"""

import time
import threading
from typing import Optional, List, Dict, Any, Callable
from queue import Queue, PriorityQueue, Empty, Full
from dataclasses import dataclass, field
from ..models.tab import POTask
from ..models.worker import Worker


@dataclass
class PriorityTask:
    """Wrapper for prioritized task queuing."""
    priority: int  # Lower numbers = higher priority
    timestamp: float
    task: POTask
    
    def __lt__(self, other):
        """Compare for priority queue ordering."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


class TaskQueue:
    """
    Service for managing PO task queuing and distribution.
    
    Responsibilities:
    - Queue tasks with priority and retry logic
    - Distribute tasks to available workers efficiently
    - Handle task failures and retry attempts
    - Provide task status and queue metrics
    - Load balance across workers based on capacity
    """
    
    def __init__(self, 
                 max_queue_size: int = 1000,
                 default_priority: int = 5,
                 max_retries: int = 3,
                 retry_delay: int = 30,
                 assignment_callback: Optional[Callable[[POTask, str], bool]] = None):
        """
        Initialize TaskQueue.
        
        Args:
            max_queue_size: Maximum number of queued tasks
            default_priority: Default task priority (1-10, lower = higher priority)
            max_retries: Maximum retry attempts for failed tasks
            retry_delay: Delay between retries in seconds
            assignment_callback: Callback for task assignment
        """
        self.max_queue_size = max_queue_size
        self.default_priority = default_priority
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.assignment_callback = assignment_callback
        
        # Queues
        self.pending_queue: PriorityQueue = PriorityQueue(maxsize=max_queue_size)
        self.retry_queue: List[Dict[str, Any]] = []  # Tasks waiting for retry
        
        # Task tracking
        self.active_tasks: Dict[str, POTask] = {}  # task_id -> task
        self.completed_tasks: Dict[str, POTask] = {}  # task_id -> task
        self.failed_tasks: Dict[str, POTask] = {}  # task_id -> task
        
        # Worker tracking
        self.workers: Dict[str, Worker] = {}
        self.worker_assignments: Dict[str, List[str]] = {}  # worker_id -> [task_ids]
        
        # Threading
        self._lock = threading.RLock()
        self._retry_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Statistics
        self.stats = {
            'total_queued': 0,
            'total_assigned': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_retries': 0,
            'queue_high_watermark': 0,
            'average_queue_time': 0.0,
            'average_processing_time': 0.0
        }
        
        # Start retry processing
        self._start_retry_processing()
        
    def add_task(self, task: POTask, priority: Optional[int] = None) -> bool:
        """
        Add a task to the queue.
        
        Args:
            task: PO task to queue
            priority: Task priority (1-10, lower = higher priority)
            
        Returns:
            True if task was queued successfully
        """
        if priority is None:
            priority = self.default_priority
            
        try:
            priority_task = PriorityTask(
                priority=priority,
                timestamp=time.time(),
                task=task
            )
            
            self.pending_queue.put(priority_task, timeout=1.0)
            
            with self._lock:
                self.stats['total_queued'] += 1
                current_size = self.pending_queue.qsize()
                if current_size > self.stats['queue_high_watermark']:
                    self.stats['queue_high_watermark'] = current_size
                    
            return True
            
        except Full:
            return False
            
    def add_tasks(self, tasks: List[POTask], priority: Optional[int] = None) -> int:
        """
        Add multiple tasks to the queue.
        
        Args:
            tasks: List of PO tasks to queue
            priority: Task priority for all tasks
            
        Returns:
            Number of tasks successfully queued
        """
        queued_count = 0
        
        for task in tasks:
            if self.add_task(task, priority):
                queued_count += 1
            else:
                break  # Stop if queue is full
                
        return queued_count
        
    def get_next_task(self, worker_id: str) -> Optional[POTask]:
        """
        Get the next task for a worker.
        
        Args:
            worker_id: ID of requesting worker
            
        Returns:
            Next task for the worker, or None if no tasks available
        """
        if worker_id not in self.workers:
            return None
            
        try:
            priority_task = self.pending_queue.get_nowait()
            task = priority_task.task
            
            with self._lock:
                # Track active task
                self.active_tasks[task.task_id] = task
                
                # Track worker assignment
                if worker_id not in self.worker_assignments:
                    self.worker_assignments[worker_id] = []
                self.worker_assignments[worker_id].append(task.task_id)
                
                self.stats['total_assigned'] += 1
                
                # Calculate queue time
                queue_time = time.time() - priority_task.timestamp
                self._update_average_queue_time(queue_time)
                
            return task
            
        except Empty:
            return None
            
    def complete_task(self, task_id: str, success: bool = True, processing_time: Optional[float] = None) -> bool:
        """
        Mark a task as completed.
        
        Args:
            task_id: ID of completed task
            success: Whether task completed successfully
            processing_time: Time taken to process task
            
        Returns:
            True if task was marked as completed
        """
        with self._lock:
            if task_id not in self.active_tasks:
                return False
                
            task = self.active_tasks.pop(task_id)
            task.completed_at = time.time()
            
            # Remove from worker assignments
            for worker_id, task_ids in self.worker_assignments.items():
                if task_id in task_ids:
                    task_ids.remove(task_id)
                    break
                    
            if success:
                self.completed_tasks[task_id] = task
                self.stats['total_completed'] += 1
            else:
                # Check if task can be retried
                if task.can_retry:
                    task.retry_count += 1
                    self._schedule_retry(task)
                    self.stats['total_retries'] += 1
                else:
                    self.failed_tasks[task_id] = task
                    self.stats['total_failed'] += 1
                    
            # Update processing time statistics
            if processing_time:
                self._update_average_processing_time(processing_time)
                
            return True
            
    def register_worker(self, worker: Worker) -> None:
        """
        Register a worker for task assignment.
        
        Args:
            worker: Worker to register
        """
        with self._lock:
            self.workers[worker.worker_id] = worker
            self.worker_assignments[worker.worker_id] = []
            
    def unregister_worker(self, worker_id: str) -> List[str]:
        """
        Unregister a worker and return its active tasks.
        
        Args:
            worker_id: ID of worker to unregister
            
        Returns:
            List of task IDs that were assigned to the worker
        """
        with self._lock:
            if worker_id not in self.workers:
                return []
                
            # Get active task IDs for this worker
            active_task_ids = self.worker_assignments.get(worker_id, [])
            
            # Move active tasks back to retry queue
            for task_id in active_task_ids:
                if task_id in self.active_tasks:
                    task = self.active_tasks.pop(task_id)
                    self._schedule_retry(task)
                    
            # Remove worker
            del self.workers[worker_id]
            if worker_id in self.worker_assignments:
                del self.worker_assignments[worker_id]
                
            return active_task_ids
            
    def get_available_workers(self) -> List[Worker]:
        """
        Get list of workers available for new tasks.
        
        Returns:
            List of available workers
        """
        available_workers = []
        
        with self._lock:
            for worker in self.workers.values():
                if worker.is_available_for_tasks:
                    available_workers.append(worker)
                    
        return available_workers
        
    def distribute_tasks(self) -> int:
        """
        Distribute pending tasks to available workers.
        
        Returns:
            Number of tasks distributed
        """
        distributed = 0
        available_workers = self.get_available_workers()
        
        if not available_workers:
            return 0
            
        # Sort workers by current load (ascending)
        available_workers.sort(key=lambda w: len(self.worker_assignments.get(w.worker_id, [])))
        
        worker_index = 0
        while not self.pending_queue.empty() and available_workers:
            worker = available_workers[worker_index]
            task = self.get_next_task(worker.worker_id)
            
            if task and self.assignment_callback:
                if self.assignment_callback(task, worker.worker_id):
                    distributed += 1
                else:
                    # Assignment failed, put task back
                    self.complete_task(task.task_id, success=False)
                    
            # Round-robin to next worker
            worker_index = (worker_index + 1) % len(available_workers)
            
            # Check if workers are still available (may have become unavailable)
            available_workers = [w for w in available_workers if w.is_available_for_tasks]
            if not available_workers:
                break
                
        return distributed
        
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive task queue status.
        
        Returns:
            Dictionary with queue status
        """
        with self._lock:
            worker_status = []
            for worker_id, worker in self.workers.items():
                assigned_tasks = len(self.worker_assignments.get(worker_id, []))
                worker_status.append({
                    'worker_id': worker_id,
                    'assigned_tasks': assigned_tasks,
                    'is_available': worker.is_available_for_tasks,
                    'status': worker.status.value
                })
                
            return {
                'pending_tasks': self.pending_queue.qsize(),
                'active_tasks': len(self.active_tasks),
                'completed_tasks': len(self.completed_tasks),
                'failed_tasks': len(self.failed_tasks),
                'retry_tasks': len(self.retry_queue),
                'registered_workers': len(self.workers),
                'available_workers': len(self.get_available_workers()),
                'worker_status': worker_status,
                'max_queue_size': self.max_queue_size,
                'queue_utilization': round(self.pending_queue.qsize() / self.max_queue_size, 2),
                'statistics': self.stats.copy()
            }
            
    def _schedule_retry(self, task: POTask) -> None:
        """
        Schedule a task for retry.
        
        Args:
            task: Task to retry
        """
        retry_time = time.time() + self.retry_delay
        retry_entry = {
            'task': task,
            'retry_time': retry_time,
            'scheduled_at': time.time()
        }
        
        self.retry_queue.append(retry_entry)
        
    def _start_retry_processing(self) -> None:
        """
        Start the retry processing thread.
        """
        self._retry_thread = threading.Thread(
            target=self._retry_processing_loop,
            name="TaskQueue-Retry",
            daemon=True
        )
        self._retry_thread.start()
        
    def _retry_processing_loop(self) -> None:
        """
        Process retry queue continuously.
        """
        while not self._stop_event.wait(5):  # Check every 5 seconds
            try:
                self._process_retries()
            except Exception:
                # Continue processing even if there's an error
                pass
                
    def _process_retries(self) -> None:
        """
        Process tasks that are ready for retry.
        """
        current_time = time.time()
        ready_tasks = []
        
        with self._lock:
            # Find tasks ready for retry
            remaining_retries = []
            for retry_entry in self.retry_queue:
                if retry_entry['retry_time'] <= current_time:
                    ready_tasks.append(retry_entry['task'])
                else:
                    remaining_retries.append(retry_entry)
                    
            self.retry_queue = remaining_retries
            
        # Re-queue ready tasks
        for task in ready_tasks:
            self.add_task(task, priority=1)  # High priority for retries
            
    def _update_average_queue_time(self, queue_time: float) -> None:
        """
        Update average queue time statistic.
        
        Args:
            queue_time: Time task spent in queue
        """
        total_assigned = self.stats['total_assigned']
        if total_assigned == 1:
            self.stats['average_queue_time'] = queue_time
        else:
            # Running average
            current_avg = self.stats['average_queue_time']
            self.stats['average_queue_time'] = ((current_avg * (total_assigned - 1)) + queue_time) / total_assigned
            
    def _update_average_processing_time(self, processing_time: float) -> None:
        """
        Update average processing time statistic.
        
        Args:
            processing_time: Time taken to process task
        """
        total_completed = self.stats['total_completed']
        if total_completed == 1:
            self.stats['average_processing_time'] = processing_time
        else:
            # Running average
            current_avg = self.stats['average_processing_time']
            self.stats['average_processing_time'] = ((current_avg * (total_completed - 1)) + processing_time) / total_completed
            
    def shutdown(self) -> None:
        """
        Shutdown task queue and stop retry processing.
        """
        self._stop_event.set()
        
        if self._retry_thread and self._retry_thread.is_alive():
            self._retry_thread.join(timeout=10)
