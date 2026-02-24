"""
Health checks for CoupaDownloads.

Provides health check endpoints for monitoring and orchestration.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time
import os
import psutil


@dataclass
class HealthStatus:
    """Represents the status of a health check."""
    name: str
    status: str  # 'healthy', 'unhealthy', 'degraded'
    message: str = ""
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """
    Performs health checks on system components.
    
    Checks can be run individually or all together for an overall health status.
    """
    
    def __init__(self) -> None:
        """Initialize health checker."""
        self._last_check: Optional[float] = None
        self._checks: Dict[str, HealthStatus] = {}
    
    # =========================================================================
    # Individual Health Checks
    # =========================================================================
    
    def check_browser(self) -> HealthStatus:
        """
        Check if browser can be initialized.
        
        Returns:
            HealthStatus with browser health information
        """
        start = time.perf_counter()
        
        try:
            # Check if Edge is installed
            import subprocess
            result = subprocess.run(
                ['which', 'Microsoft Edge'],
                capture_output=True,
                timeout=5
            )
            
            latency = (time.perf_counter() - start) * 1000
            
            if result.returncode == 0:
                return HealthStatus(
                    name='browser',
                    status='healthy',
                    message='Microsoft Edge is installed',
                    latency_ms=latency
                )
            else:
                return HealthStatus(
                    name='browser',
                    status='unhealthy',
                    message='Microsoft Edge not found',
                    latency_ms=latency
                )
                
        except subprocess.TimeoutExpired:
            return HealthStatus(
                name='browser',
                status='unhealthy',
                message='Browser check timed out',
                latency_ms=5000.0
            )
        except Exception as e:
            return HealthStatus(
                name='browser',
                status='unhealthy',
                message=f'Browser check failed: {str(e)}',
                latency_ms=(time.perf_counter() - start) * 1000
            )
    
    def check_disk_space(self, path: Optional[str] = None, min_free_gb: float = 1.0) -> HealthStatus:
        """
        Check available disk space.
        
        Args:
            path: Path to check (default: current directory)
            min_free_gb: Minimum free space required in GB
        
        Returns:
            HealthStatus with disk space information
        """
        start = time.perf_counter()
        
        try:
            if path is None:
                path = os.getcwd()
            
            stat = os.statvfs(path)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
            total_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
            used_percent = ((stat.f_blocks - stat.f_bfree) / stat.f_blocks) * 100
            
            latency = (time.perf_counter() - start) * 1000
            
            if free_gb < min_free_gb:
                return HealthStatus(
                    name='disk_space',
                    status='unhealthy',
                    message=f'Only {free_gb:.2f}GB free (minimum: {min_free_gb}GB)',
                    latency_ms=latency,
                    details={
                        'free_gb': free_gb,
                        'total_gb': total_gb,
                        'used_percent': used_percent,
                        'min_required_gb': min_free_gb
                    }
                )
            elif free_gb < min_free_gb * 2:
                return HealthStatus(
                    name='disk_space',
                    status='degraded',
                    message=f'Low disk space: {free_gb:.2f}GB free',
                    latency_ms=latency,
                    details={
                        'free_gb': free_gb,
                        'total_gb': total_gb,
                        'used_percent': used_percent
                    }
                )
            else:
                return HealthStatus(
                    name='disk_space',
                    status='healthy',
                    message=f'{free_gb:.2f}GB free',
                    latency_ms=latency,
                    details={
                        'free_gb': free_gb,
                        'total_gb': total_gb,
                        'used_percent': used_percent
                    }
                )
                
        except Exception as e:
            return HealthStatus(
                name='disk_space',
                status='unhealthy',
                message=f'Disk check failed: {str(e)}',
                latency_ms=(time.perf_counter() - start) * 1000
            )
    
    def check_memory(self, min_free_gb: float = 0.5) -> HealthStatus:
        """
        Check available memory.
        
        Args:
            min_free_gb: Minimum free memory required in GB
        
        Returns:
            HealthStatus with memory information
        """
        start = time.perf_counter()
        
        try:
            mem = psutil.virtual_memory()
            free_gb = mem.available / (1024 ** 3)
            total_gb = mem.total / (1024 ** 3)
            used_percent = mem.percent
            
            latency = (time.perf_counter() - start) * 1000
            
            if free_gb < min_free_gb:
                return HealthStatus(
                    name='memory',
                    status='unhealthy',
                    message=f'Only {free_gb:.2f}GB free (minimum: {min_free_gb}GB)',
                    latency_ms=latency,
                    details={
                        'free_gb': free_gb,
                        'total_gb': total_gb,
                        'used_percent': used_percent,
                        'min_required_gb': min_free_gb
                    }
                )
            elif used_percent > 90:
                return HealthStatus(
                    name='memory',
                    status='degraded',
                    message=f'High memory usage: {used_percent:.1f}%',
                    latency_ms=latency,
                    details={
                        'free_gb': free_gb,
                        'total_gb': total_gb,
                        'used_percent': used_percent
                    }
                )
            else:
                return HealthStatus(
                    name='memory',
                    status='healthy',
                    message=f'{free_gb:.2f}GB free',
                    latency_ms=latency,
                    details={
                        'free_gb': free_gb,
                        'total_gb': total_gb,
                        'used_percent': used_percent
                    }
                )
                
        except Exception as e:
            return HealthStatus(
                name='memory',
                status='unhealthy',
                message=f'Memory check failed: {str(e)}',
                latency_ms=(time.perf_counter() - start) * 1000
            )
    
    def check_cpu(self, max_usage_percent: float = 90.0) -> HealthStatus:
        """
        Check CPU usage.
        
        Args:
            max_usage_percent: Maximum acceptable CPU usage
        
        Returns:
            HealthStatus with CPU information
        """
        start = time.perf_counter()
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            latency = (time.perf_counter() - start) * 1000
            
            if cpu_percent > max_usage_percent:
                return HealthStatus(
                    name='cpu',
                    status='degraded',
                    message=f'High CPU usage: {cpu_percent:.1f}%',
                    latency_ms=latency,
                    details={
                        'cpu_percent': cpu_percent,
                        'max_allowed': max_usage_percent
                    }
                )
            else:
                return HealthStatus(
                    name='cpu',
                    status='healthy',
                    message=f'{cpu_percent:.1f}% usage',
                    latency_ms=latency,
                    details={
                        'cpu_percent': cpu_percent
                    }
                )
                
        except Exception as e:
            return HealthStatus(
                name='cpu',
                status='unhealthy',
                message=f'CPU check failed: {str(e)}',
                latency_ms=(time.perf_counter() - start) * 1000
            )
    
    # =========================================================================
    # Overall Health Status
    # =========================================================================
    
    def get_overall_status(self) -> HealthStatus:
        """
        Get overall system health status.
        
        Aggregates all individual checks and returns overall status.
        
        Returns:
            HealthStatus with overall health information
        """
        start = time.perf_counter()
        
        # Run all checks
        checks = [
            self.check_disk_space(),
            self.check_memory(),
            self.check_cpu(),
        ]
        
        # Determine overall status
        statuses = [check.status for check in checks]
        
        if 'unhealthy' in statuses:
            overall_status = 'unhealthy'
            message = 'One or more critical checks failed'
        elif 'degraded' in statuses:
            overall_status = 'degraded'
            message = 'Some checks are degraded'
        else:
            overall_status = 'healthy'
            message = 'All checks passed'
        
        latency = (time.perf_counter() - start) * 1000
        
        self._last_check = time.time()
        
        return HealthStatus(
            name='overall',
            status=overall_status,
            message=message,
            latency_ms=latency,
            details={
                'checks': {check.name: check.status for check in checks},
                'check_count': len(checks),
                'unhealthy_count': statuses.count('unhealthy'),
                'degraded_count': statuses.count('degraded')
            }
        )
    
    def get_all_checks(self) -> List[HealthStatus]:
        """
        Get all individual health checks.
        
        Returns:
            List of HealthStatus for all checks
        """
        return [
            self.check_disk_space(),
            self.check_memory(),
            self.check_cpu(),
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert health status to dictionary.
        
        Returns:
            Dictionary representation of health status
        """
        overall = self.get_overall_status()
        checks = self.get_all_checks()
        
        return {
            'status': overall.status,
            'message': overall.message,
            'latency_ms': overall.latency_ms,
            'timestamp': overall.timestamp,
            'checks': [
                {
                    'name': check.name,
                    'status': check.status,
                    'message': check.message,
                    'latency_ms': check.latency_ms,
                    'details': check.details
                }
                for check in checks
            ]
        }


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create global health checker."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
