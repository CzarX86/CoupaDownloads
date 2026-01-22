"""
UI Helper Utilities: Enhanced UI Feedback

Thread-safe UI update utilities and helper functions for Tkinter components.
Provides common functionality for feedback display components.
"""

import logging
import threading
from typing import Callable, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class UIThreadHelper:
    """Helper for thread-safe UI updates in Tkinter."""

    def __init__(self, root_window):
        """Initialize with the root Tkinter window."""
        self.root = root_window
        self._update_lock = threading.Lock()

    def safe_update(self, callback: Callable, *args, **kwargs) -> None:
        """Safely update UI from any thread."""
        try:
            with self._update_lock:
                if self.root and hasattr(self.root, 'after'):
                    # Schedule update on main thread
                    self.root.after(0, lambda: self._execute_callback(callback, *args, **kwargs))
        except Exception as e:
            logger.error(f"Error scheduling UI update: {e}")

    def _execute_callback(self, callback: Callable, *args, **kwargs) -> None:
        """Execute callback on main thread."""
        try:
            callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error executing UI callback: {e}")


class ProgressFormatter:
    """Format progress information for display."""

    @staticmethod
    def format_percentage(value: float) -> str:
        """Format percentage with one decimal place."""
        return f"{value:.1f}%"

    @staticmethod
    def format_file_size(bytes_size: int) -> str:
        """Format file size in human-readable format."""
        if bytes_size == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        size_index = 0
        size = float(bytes_size)

        while size >= 1024.0 and size_index < len(size_names) - 1:
            size /= 1024.0
            size_index += 1

        if size_index == 0:
            return f"{int(size)} {size_names[size_index]}"
        else:
            return f"{size:.1f} {size_names[size_index]}"

    @staticmethod
    def format_time_remaining(seconds: Optional[float]) -> str:
        """Format estimated time remaining."""
        if seconds is None:
            return "Calculating..."

        if seconds < 60:
            return f"{int(seconds)}s remaining"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s remaining"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m remaining"

    @staticmethod
    def format_speed(bytes_per_second: Optional[float]) -> str:
        """Format download speed."""
        if bytes_per_second is None:
            return "N/A"

        return ProgressFormatter.format_file_size(int(bytes_per_second)) + "/s"


class StatusMessageFormatter:
    """Format status messages for display."""

    @staticmethod
    def format_timestamp(timestamp: datetime) -> str:
        """Format timestamp for display."""
        now = datetime.now()
        diff = now - timestamp

        if diff.days > 0:
            return timestamp.strftime("%m/%d %H:%M")
        elif diff.seconds < 60:
            return "Just now"
        elif diff.seconds < 3600:
            return f"{diff.seconds // 60}m ago"
        else:
            return timestamp.strftime("%H:%M")

    @staticmethod
    def get_status_color(message_type: str) -> str:
        """Get color for status message type."""
        colors = {
            'info': '#0066cc',      # Blue
            'success': '#28a745',   # Green
            'warning': '#ffc107',   # Yellow/Orange
            'error': '#dc3545',     # Red
            'progress': '#17a2b8'   # Teal
        }
        return colors.get(message_type, '#6c757d')  # Default gray


class ErrorFormatter:
    """Format error information for user-friendly display."""

    @staticmethod
    def format_error_message(error_info) -> str:
        """Format error for display."""
        message = error_info.user_message

        if error_info.recovery_suggestions:
            suggestions = "\n".join(f"• {suggestion}" for suggestion in error_info.recovery_suggestions)
            message += f"\n\nSuggested actions:\n{suggestions}"

        if error_info.contact_support:
            message += "\n\nIf the problem persists, please contact support."

        return message

    @staticmethod
    def get_error_icon(error_type: str) -> str:
        """Get icon name for error type."""
        icons = {
            'network': 'wifi_off',
            'auth': 'lock',
            'filesystem': 'folder_off',
            'config': 'settings',
            'validation': 'error_outline',
            'unknown': 'help'
        }
        return icons.get(error_type, 'error')


class StatisticsFormatter:
    """Format download statistics for display."""

    @staticmethod
    def format_success_rate(rate: float) -> str:
        """Format success rate percentage."""
        return f"{rate:.1f}%"

    @staticmethod
    def format_duration(duration: Optional[timedelta]) -> str:
        """Format duration for display."""
        if not duration:
            return "N/A"

        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    @staticmethod
    def format_summary(stats) -> str:
        """Format statistics summary."""
        lines = [
            f"Files: {stats.successful_downloads}/{stats.total_files} successful",
            f"Data: {ProgressFormatter.format_file_size(stats.total_bytes_downloaded)}",
            f"Duration: {StatisticsFormatter.format_duration(stats.total_duration)}",
            f"Success Rate: {StatisticsFormatter.format_success_rate(stats.success_rate)}"
        ]

        if stats.average_speed:
            lines.append(f"Average Speed: {ProgressFormatter.format_speed(stats.average_speed)}")

        return "\n".join(lines)


class AnimationHelper:
    """Helper for smooth UI animations."""

    @staticmethod
    def smooth_progress_update(current: float, target: float, steps: int = 10) -> list[float]:
        """Generate smooth progress update steps."""
        if steps <= 1:
            return [target]

        step_size = (target - current) / steps
        return [current + step_size * i for i in range(1, steps + 1)]

    @staticmethod
    def animate_value(start: float, end: float, duration_ms: int, callback: Callable) -> None:
        """Animate a value change over time."""
        import threading
        import time

        def animate():
            start_time = time.time()
            while time.time() - start_time < duration_ms / 1000:
                elapsed = time.time() - start_time
                progress = min(elapsed / (duration_ms / 1000), 1.0)

                # Easing function (ease-out)
                eased_progress = 1 - (1 - progress) ** 3
                current_value = start + (end - start) * eased_progress

                try:
                    callback(current_value)
                except Exception as e:
                    logger.error(f"Animation callback error: {e}")
                    break

                time.sleep(0.016)  # ~60 FPS

            # Ensure final value is set
            try:
                callback(end)
            except Exception as e:
                logger.error(f"Final animation callback error: {e}")

        threading.Thread(target=animate, daemon=True).start()