#!/usr/bin/env python3
"""
Test script for WorkerPoolAdapter integration.

This script validates the basic functionality of the integration adapter
without requiring external dependencies.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_imports():
    """Test that all modules can be imported."""
    try:
        # Test basic imports without dependencies
        print("Testing basic imports...")

        # Mock structlog if not available
        try:
            import structlog
        except ImportError:
            print("structlog not available, creating mock...")
            import types
            structlog = types.ModuleType('structlog')
            structlog.get_logger = lambda name: MockLogger()
            sys.modules['structlog'] = structlog

        # Mock pandas if not available
        try:
            import pandas as pd
        except ImportError:
            print("pandas not available, creating mock...")
            pd = types.ModuleType('pandas')
            pd.read_csv = lambda *args, **kwargs: MockDataFrame()
            pd.read_excel = lambda *args, **kwargs: MockDataFrame()
            sys.modules['pandas'] = pd

        # Now try importing our modules
        from EXPERIMENTAL.integration.csv_adapter import CSVAdapter
        from EXPERIMENTAL.integration.result_collector import ResultCollector
        from EXPERIMENTAL.integration.progress_tracker import ProgressTracker

        print("✓ Integration modules imported successfully")

        # Test that classes can be instantiated
        csv_adapter = CSVAdapter()
        result_collector = ResultCollector()
        progress_tracker = ProgressTracker()

        print("✓ Integration classes instantiated successfully")

        return True

    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False

class MockLogger:
    """Mock logger for testing."""
    def debug(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass

class MockDataFrame:
    """Mock DataFrame for testing."""
    def __init__(self):
        self.columns = ['po_number', 'priority']

    def __getitem__(self, key):
        return ['PO001', 'PO002']

    def __len__(self):
        return 2

def test_csv_adapter():
    """Test CSV adapter functionality."""
    try:
        print("\nTesting CSV adapter...")

        # Mock dependencies
        import types
        try:
            import structlog
        except ImportError:
            structlog = types.ModuleType('structlog')
            structlog.get_logger = lambda name: MockLogger()
            sys.modules['structlog'] = structlog

        try:
            import pandas as pd
        except ImportError:
            pd = types.ModuleType('pandas')
            pd.read_csv = lambda *args, **kwargs: MockDataFrame()
            sys.modules['pandas'] = pd

        from EXPERIMENTAL.integration.csv_adapter import CSVAdapter

        adapter = CSVAdapter()

        # Test basic functionality
        stats = adapter.get_stats()
        print(f"✓ CSV adapter stats: {stats}")

        return True

    except Exception as e:
        print(f"✗ CSV adapter test failed: {e}")
        return False

def test_result_collector():
    """Test result collector functionality."""
    try:
        print("\nTesting result collector...")

        # Mock dependencies
        import types
        try:
            import structlog
        except ImportError:
            structlog = types.ModuleType('structlog')
            structlog.get_logger = lambda name: MockLogger()
            sys.modules['structlog'] = structlog

        from EXPERIMENTAL.integration.result_collector import ResultCollector

        collector = ResultCollector()

        # Test basic functionality
        stats = collector.get_stats()
        print(f"✓ Result collector stats: {stats}")

        return True

    except Exception as e:
        print(f"✗ Result collector test failed: {e}")
        return False

def test_progress_tracker():
    """Test progress tracker functionality."""
    try:
        print("\nTesting progress tracker...")

        # Mock dependencies
        import types
        try:
            import structlog
        except ImportError:
            structlog = types.ModuleType('structlog')
            structlog.get_logger = lambda name: MockLogger()
            sys.modules['structlog'] = structlog

        from EXPERIMENTAL.integration.progress_tracker import ProgressTracker

        tracker = ProgressTracker()

        # Test basic functionality
        stats = tracker.get_stats()
        print(f"✓ Progress tracker stats: {stats}")

        return True

    except Exception as e:
        print(f"✗ Progress tracker test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== WorkerPoolAdapter Integration Test ===\n")

    tests = [
        test_imports,
        test_csv_adapter,
        test_result_collector,
        test_progress_tracker
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n=== Test Results: {passed}/{total} passed ===")

    if passed == total:
        print("✓ All integration adapter tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())