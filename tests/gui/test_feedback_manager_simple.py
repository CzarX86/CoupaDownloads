"""
Test Feedback Manager Contract

Contract tests for the feedback manager to ensure it meets the interface requirements.
Tests the contract defined in contracts/feedback-manager-contract.md.
"""

import sys
from pathlib import Path

# Set up path before any imports
project_root = Path(__file__).resolve().parents[2]
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest


class TestFeedbackManagerContract:
    """Contract tests for FeedbackManager."""

    def test_basic_import_and_initialization(self):
        """Test that we can import and initialize the feedback manager."""
        from src.ui.data_model import UIFeedbackConfig
        from src.ui.feedback_manager import FeedbackManager
        
        feedback_manager = FeedbackManager()
        config = UIFeedbackConfig()
        
        # Should not raise exception
        feedback_manager.initialize(config)
        assert True