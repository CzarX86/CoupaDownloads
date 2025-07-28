#!/usr/bin/env python3
"""
Test runner script for Coupa Downloads project.
Run this script to execute all tests or specific test categories.
"""

import sys
import subprocess
import argparse


def run_tests(test_type="all", verbose=False):
    """Run tests based on the specified type."""
    
    base_cmd = ["python", "-m", "pytest"]
    
    if verbose:
        base_cmd.append("-v")
    
    if test_type == "all":
        cmd = base_cmd + ["tests/"]
    elif test_type == "unit":
        cmd = base_cmd + ["tests/", "-m", "unit"]
    elif test_type == "integration":
        cmd = base_cmd + ["tests/", "-m", "integration"]
    elif test_type == "fast":
        cmd = base_cmd + ["tests/", "-m", "not slow"]
    else:
        print(f"Unknown test type: {test_type}")
        return False
    
    print(f"Running {test_type} tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, check=True)
        print("-" * 50)
        print("✅ All tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print("-" * 50)
        print(f"❌ Tests failed with exit code: {e.returncode}")
        return False
    except FileNotFoundError:
        print("❌ pytest not found. Please install pytest: pip install pytest")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run tests for Coupa Downloads project")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "fast"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    success = run_tests(args.type, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 