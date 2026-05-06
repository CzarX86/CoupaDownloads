"""
Core interfaces and utilities for CoupaPilot.
"""

from .status import StatusLevel, StatusMessage
from .telemetry import TelemetryProvider
from .communication_manager import CommunicationManager
from .resource_assessor import ResourceAssessor

__version__ = "0.2.0"
__all__ = [
    "StatusLevel",
    "StatusMessage",
    "TelemetryProvider",
    "CommunicationManager",
    "ResourceAssessor",
]