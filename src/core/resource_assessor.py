"""
ResourceAssessor module for evaluating system hardware and suggesting safe worker counts.

This module uses psutil to query system resources and provides calculations
to prevent system overload during parallel processing.
"""

import os
import multiprocessing as mp
import psutil
from typing import Dict, Any, Tuple

class ResourceAssessor:
    """
    Assesses system resources (CPU, RAM) and suggests optimal worker scaling.
    """
    
    # Estimates per worker (Edge/Chrome browser + Python process)
    ESTIMATED_RAM_PER_WORKER_MB = 400  
    ESTIMATED_CPU_LOAD_PER_WORKER = 0.5  # 50% of one core
    
    # Safety thresholds
    CRITICAL_FREE_RAM_GB = 0.5  # Below this, we should be very loud about risks
    MINIMUM_FREE_RAM_GB = 0.3   # Absolute basement
    
    @classmethod
    def get_system_resources(cls) -> Dict[str, Any]:
        """Query current system hardware and resource usage."""
        vm = psutil.virtual_memory()
        return {
            "cpu_count": mp.cpu_count(),
            "cpu_usage_percent": psutil.cpu_percent(interval=0.1),
            "total_ram_gb": round(vm.total / (1024**3), 2),
            "available_ram_gb": round(vm.available / (1024**3), 2),
            "available_ram_mb": round(vm.available / (1024**2), 2),
        }
    
    @classmethod
    def calculate_safe_worker_count(cls, requested_count: int, min_free_ram_gb: float = 0.3) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate if the requested worker count is safe based on available resources.
        
        Args:
            requested_count: Number of workers requested.
            min_free_ram_gb: Minimum free RAM to maintain for the system.
            
        Returns:
            Tuple: (suggested_count, assessment_report)
        """
        resources = cls.get_system_resources()
        available_ram_mb = resources["available_ram_mb"]
        cpu_count = resources["cpu_count"]
        
        # 1. RAM-based limit
        usable_ram_mb = max(0, available_ram_mb - (min_free_ram_gb * 1024))
        ram_limit = int(usable_ram_mb // cls.ESTIMATED_RAM_PER_WORKER_MB)
        
        # 2. CPU-based limit
        cpu_limit = int(cpu_count * 3) 
        
        # Combined limit (Nominally safe)
        safe_limit = max(1, min(ram_limit, cpu_limit))
        
        # Permissiveness Logic:
        # We allow higher counts but upgrade the risk level based on available RAM.
        is_8gb_system = resources["total_ram_gb"] >= 7.5
        is_memory_critically_low = resources["available_ram_gb"] < cls.CRITICAL_FREE_RAM_GB
        
        if requested_count <= safe_limit:
            risk_level = "LOW"
            suggested_count = requested_count
        elif requested_count <= 4 and is_8gb_system and not is_memory_critically_low:
            risk_level = "MEDIUM" # Nominal, but allowed on 8GB machines
            suggested_count = requested_count
        else:
            # If memory is critically low, we are much stricter
            risk_level = "HIGH" if is_memory_critically_low else "MEDIUM"
            # Allow some overflow but cap it more strictly if RAM is low
            overflow_multiplier = 1.5 if is_memory_critically_low else 3.0
            suggested_count = min(requested_count, max(1, int(safe_limit * overflow_multiplier)))

        report = {
            "requested": requested_count,
            "suggested": suggested_count,
            "safe_limit": safe_limit,
            "system": resources,
            "risk_level": risk_level,
            "is_throttled": suggested_count < requested_count,
            "is_memory_critical": is_memory_critically_low,
            "stagger_delay": 2.0 if risk_level != "LOW" else 0.5 # Suggest a delay between browser spawns
        }
        
        return suggested_count, report

    @classmethod
    def get_risk_message(cls, report: Dict[str, Any]) -> str:
        """Generate a human-readable risk message based on the assessment report."""
        if report["risk_level"] == "LOW":
            return f"✅ Resources OK: {report['system']['available_ram_gb']}GB RAM available. Requested {report['requested']} workers is safe."
        
        if report["risk_level"] == "MEDIUM":
            msg = f"🟡 Resource Warning (Moderate): Requested {report['requested']} workers.\n"
            msg += f"  - Available RAM: {report['system']['available_ram_gb']}GB (Safe Limit: {report['safe_limit']})\n"
            msg += f"  - Performance might be slightly reduced."
            if report["is_throttled"]:
                msg += f"\n  - Action: Adjusted to {report['suggested']} workers for stability."
            return msg

        # HIGH / CRITICAL
        msg = f"⚠️ Resource Warning (CRITICAL): Extreme memory pressure detected!\n"
        msg += f"  - Available RAM: {report['system']['available_ram_gb']}GB (Required available for stable run: >0.5GB)\n"
        msg += f"  - Scaling: Requested {report['requested']} -> Using {report['suggested']}\n"
        msg += f"  - CAUTION: System may become unresponsive or swap heavily."
        return msg
