"""
Statistics Panel Component

Displays download statistics and completion summaries.
Shows real-time metrics including success rates, speeds, and completion status.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
import threading
from datetime import datetime, timedelta

from src.ui.data_model import DownloadStatistics, UIFeedbackConfig
from src.ui.feedback_manager import FeedbackManager


class StatisticsPanel(ttk.LabelFrame):
    """
    Tkinter component for displaying download statistics.

    Features:
    - Real-time statistics display
    - Success rate calculations
    - Download speed metrics
    - Completion summaries
    - Thread-safe updates
    """

    def __init__(self, parent: tk.Widget, config: UIFeedbackConfig):
        """
        Initialize the statistics panel component.

        Args:
            parent: Parent Tkinter widget
            config: UI feedback configuration
        """
        super().__init__(parent, text="Download Statistics", padding="10")
        self.config = config
        self.current_stats: Optional[DownloadStatistics] = None

        # Thread safety
        self._lock = threading.Lock()
        self._update_pending = False

        # Create UI components
        self._create_widgets()

    def _create_widgets(self):
        """Create and layout the statistics display widgets."""
        # Statistics grid
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        # Row 1: Files
        ttk.Label(stats_frame, text="Total Files:", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.total_files_label = ttk.Label(stats_frame, text="0", font=("Arial", 9))
        self.total_files_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(stats_frame, text="Successful:", font=("Arial", 9, "bold")).grid(row=0, column=2, sticky=tk.W, padx=(20, 0), pady=2)
        self.successful_label = ttk.Label(stats_frame, text="0 (0%)", font=("Arial", 9))
        self.successful_label.grid(row=0, column=3, sticky=tk.W, padx=(10, 0), pady=2)

        # Row 2: Failed and duration
        ttk.Label(stats_frame, text="Failed:", font=("Arial", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.failed_label = ttk.Label(stats_frame, text="0", font=("Arial", 9))
        self.failed_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(stats_frame, text="Duration:", font=("Arial", 9, "bold")).grid(row=1, column=2, sticky=tk.W, padx=(20, 0), pady=2)
        self.duration_label = ttk.Label(stats_frame, text="N/A", font=("Arial", 9))
        self.duration_label.grid(row=1, column=3, sticky=tk.W, padx=(10, 0), pady=2)

        # Row 3: Data and speed
        ttk.Label(stats_frame, text="Data Downloaded:", font=("Arial", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.data_label = ttk.Label(stats_frame, text="0 B", font=("Arial", 9))
        self.data_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        ttk.Label(stats_frame, text="Avg Speed:", font=("Arial", 9, "bold")).grid(row=2, column=2, sticky=tk.W, padx=(20, 0), pady=2)
        self.speed_label = ttk.Label(stats_frame, text="N/A", font=("Arial", 9))
        self.speed_label.grid(row=2, column=3, sticky=tk.W, padx=(10, 0), pady=2)

        # Completion summary (shown when download completes)
        self.summary_frame = ttk.Frame(self)
        # Initially hidden - shown when operation completes

        ttk.Label(self.summary_frame, text="Download Complete!", font=("Arial", 10, "bold"), foreground="green").pack(pady=(0, 5))

        self.summary_label = ttk.Label(
            self.summary_frame,
            text="",
            wraplength=400,
            justify=tk.LEFT,
            font=("Arial", 9)
        )
        self.summary_label.pack(fill=tk.X)

        # Configure grid weights for proper resizing
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(3, weight=1)

    def update_statistics(self, stats: DownloadStatistics):
        """
        Update displayed statistics.

        Args:
            stats: New statistics data
        """
        with self._lock:
            self.current_stats = stats
            if not self._update_pending:
                self._update_pending = True
                # Schedule UI update on main thread
                self.after(0, self._update_display)

    def _update_display(self):
        """Update the UI components with current statistics."""
        with self._lock:
            self._update_pending = False

            if self.current_stats is None:
                return

            stats = self.current_stats

            # Update basic counts
            self.total_files_label.config(text=str(stats.total_files))
            self.successful_label.config(text=f"{stats.successful_downloads} ({stats.success_rate:.1f}%)")
            self.failed_label.config(text=str(stats.failed_downloads))

            # Update duration
            if stats.total_duration:
                self.duration_label.config(text=self._format_duration(stats.total_duration))
            else:
                self.duration_label.config(text="N/A")

            # Update data size
            self.data_label.config(text=self._format_bytes(stats.total_bytes_downloaded))

            # Update speed
            if stats.average_speed:
                self.speed_label.config(text=self._format_speed(stats.average_speed))
            else:
                self.speed_label.config(text="N/A")

            # Show completion summary if operation is complete
            if stats.end_time and stats.total_files > 0:
                self._show_completion_summary(stats)

    def _format_duration(self, duration: timedelta) -> str:
        """Format duration for display."""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def _format_bytes(self, bytes_count: int) -> str:
        """Format byte count for display."""
        if bytes_count == 0:
            return "0 B"

        size = float(bytes_count)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def _format_speed(self, bytes_per_second: float) -> str:
        """Format download speed for display."""
        if bytes_per_second == 0:
            return "0 B/s"

        for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
            if bytes_per_second < 1024.0:
                return f"{bytes_per_second:.1f} {unit}"
            bytes_per_second /= 1024.0
        return f"{bytes_per_second:.1f} TB/s"

    def _show_completion_summary(self, stats: DownloadStatistics):
        """Show completion summary when download finishes."""
        if stats.total_files == 0:
            return

        success_rate = stats.success_rate
        total_files = stats.total_files
        successful = stats.successful_downloads
        failed = stats.failed_downloads

        # Create summary text
        summary_parts = []

        if success_rate == 100.0:
            summary_parts.append("All downloads completed successfully!")
        elif success_rate >= 80.0:
            summary_parts.append(f"Downloads mostly successful ({successful}/{total_files} files).")
        elif success_rate >= 50.0:
            summary_parts.append(f"Downloads partially successful ({successful}/{total_files} files).")
        else:
            summary_parts.append(f"Downloads had issues ({successful}/{total_files} files successful).")

        if stats.total_duration:
            duration_str = self._format_duration(stats.total_duration)
            summary_parts.append(f"Total time: {duration_str}.")

        if stats.total_bytes_downloaded > 0:
            data_str = self._format_bytes(stats.total_bytes_downloaded)
            summary_parts.append(f"Data downloaded: {data_str}.")

        # Add next steps
        if failed > 0:
            summary_parts.append("\nNext steps:")
            summary_parts.append("• Check error details for failed downloads")
            summary_parts.append("• Retry failed downloads if needed")
            summary_parts.append("• Review download logs for issues")
        else:
            summary_parts.append("\nNext steps:")
            summary_parts.append("• Review downloaded files")
            summary_parts.append("• Process or organize downloaded data")
            summary_parts.append("• Generate reports if needed")

        summary_text = "\n".join(summary_parts)

        # Update summary label
        self.summary_label.config(text=summary_text)

        # Show summary frame
        if not self.summary_frame.winfo_ismapped():
            self.summary_frame.pack(fill=tk.X, pady=(10, 0))

    def reset_statistics(self):
        """Reset all statistics to zero."""
        empty_stats = DownloadStatistics()
        self.update_statistics(empty_stats)

        # Hide summary
        if self.summary_frame.winfo_ismapped():
            self.summary_frame.pack_forget()

    def register_with_feedback_manager(self, feedback_manager: FeedbackManager):
        """
        Register this panel with a feedback manager for automatic updates.

        Args:
            feedback_manager: FeedbackManager instance to register with
        """
        feedback_manager.register_callback("statistics_updated", self._on_statistics_update)

    def unregister_from_feedback_manager(self, feedback_manager: FeedbackManager):
        """
        Unregister this panel from a feedback manager.

        Args:
            feedback_manager: FeedbackManager instance to unregister from
        """
        feedback_manager.unregister_callback("statistics_updated", self._on_statistics_update)

    def _on_statistics_update(self, stats: DownloadStatistics):
        """
        Callback for statistics updates from feedback manager.

        Args:
            stats: Updated statistics
        """
        self.update_statistics(stats)

    def destroy(self):
        """Clean up the component."""
        super().destroy()