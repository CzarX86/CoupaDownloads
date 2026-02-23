"""
Orchestrators package.

Contains orchestrator classes that manage specific aspects of the CoupaDownloads workflow.
These classes were extracted from MainApp to improve separation of concerns and reduce complexity.

Modules:
- browser_orchestrator: Manages browser lifecycle and WebDriver operations
- result_aggregator: Handles result collection and persistence
"""

from .browser_orchestrator import BrowserOrchestrator
from .result_aggregator import ResultAggregator

__all__ = [
    'BrowserOrchestrator',
    'ResultAggregator',
]
