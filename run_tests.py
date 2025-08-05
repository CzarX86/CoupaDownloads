#!/usr/bin/env python3
"""
Test Runner for Coupa Downloads automation.
Provides various options for running tests with different configurations.
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path


def run_tests_with_options(options):
    """Run tests with specified options"""
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add test path
    cmd.append("tests/")
    
    # Add options
    if options.verbose:
        cmd.extend(["-v", "--tb=long"])
    else:
        cmd.extend(["--tb=short"])
    
    if options.coverage:
        cmd.extend(["--cov=.", "--cov-report=html:htmlcov", "--cov-report=term-missing"])
    
    if options.parallel:
        cmd.extend(["-n", "auto"])
    
    if options.timeout:
        cmd.extend(["--timeout=60"])
    
    if options.markers:
        cmd.extend(["-m", options.markers])
    
    if options.k:
        cmd.extend(["-k", options.k])
    
    if options.failed:
        cmd.append("--lf")
    
    if options.new:
        cmd.append("--nf")
    
    if options.html:
        cmd.extend(["--html=test_report.html", "--self-contained-html"])
    
    if options.junit:
        cmd.extend(["--junitxml=test_results.xml"])
    
    if options.quiet:
        cmd.append("-q")
    
    if options.stop_on_failure:
        cmd.append("-x")
    
    if options.max_fail:
        cmd.extend(["--maxfail", str(options.max_fail)])
    
    print(f"Running tests with command: {' '.join(cmd)}")
    print("=" * 80)
    
    start_time = time.time()
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    end_time = time.time()
    
    print("=" * 80)
    print(f"Tests completed in {end_time - start_time:.2f} seconds")
    print(f"Exit code: {result.returncode}")
    
    return result.returncode


def run_specific_test_suite(suite_name):
    """Run a specific test suite"""
    suites = {
        "unit": "tests/ -m unit",
        "integration": "tests/ -m integration",
        "csv": "tests/ -m csv_processing",
        "excel": "tests/ -m excel_processing",
        "downloader": "tests/test_downloader.py",
        "utils": "tests/test_utils.py",
        "csv_processing": "tests/test_csv_processing.py",
        "file_operations": "tests/test_file_operations.py",
        "selenium": "tests/ -m selenium",
        "performance": "tests/ -m performance",
        "regression": "tests/ -m regression",
        "fast": "tests/ -m 'not slow'",
        "slow": "tests/ -m slow"
    }
    
    if suite_name not in suites:
        print(f"Unknown test suite: {suite_name}")
        print(f"Available suites: {', '.join(suites.keys())}")
        return 1
    
    cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short"]
    cmd.extend(suites[suite_name].split())
    
    print(f"Running {suite_name} test suite...")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 80)
    
    start_time = time.time()
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    end_time = time.time()
    
    print("=" * 80)
    print(f"{suite_name} tests completed in {end_time - start_time:.2f} seconds")
    print(f"Exit code: {result.returncode}")
    
    return result.returncode


def install_dependencies():
    """Install test dependencies"""
    print("Installing test dependencies...")
    
    requirements_file = "requirements.txt"
    if not os.path.exists(requirements_file):
        print(f"Requirements file {requirements_file} not found!")
        return 1
    
    cmd = [sys.executable, "-m", "pip", "install", "-r", requirements_file]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    
    if result.returncode == 0:
        print("Dependencies installed successfully!")
    else:
        print("Failed to install dependencies!")
    
    return result.returncode


def show_test_info():
    """Show information about available tests"""
    print("Coupa Downloads Test Suite")
    print("=" * 50)
    
    # Count test files
    test_dir = Path("tests")
    if test_dir.exists():
        test_files = list(test_dir.glob("test_*.py"))
        print(f"Found {len(test_files)} test files:")
        for test_file in sorted(test_files):
            print(f"  - {test_file.name}")
    
    print("\nAvailable test markers:")
    markers = [
        "unit", "integration", "selenium", "file_operations",
        "csv_processing", "excel_processing", "download_methods",
        "browser", "mock", "performance", "regression", "slow"
    ]
    for marker in markers:
        print(f"  - {marker}")
    
    print("\nExample commands:")
    print("  python run_tests.py --unit")
    print("  python run_tests.py --integration --coverage")
    print("  python run_tests.py --csv --verbose")
    print("  python run_tests.py --performance --parallel")
    print("  python run_tests.py --fast --coverage --html")


def main():
    parser = argparse.ArgumentParser(
        description="Test runner for Coupa Downloads automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py --unit                    # Run unit tests only
  python run_tests.py --integration --coverage  # Run integration tests with coverage
  python run_tests.py --csv --verbose           # Run CSV tests with verbose output
  python run_tests.py --performance --parallel  # Run performance tests in parallel
  python run_tests.py --fast --coverage --html  # Run fast tests with coverage and HTML report
        """
    )
    
    # Test suite options
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--csv", action="store_true", help="Run CSV processing tests only")
    parser.add_argument("--excel", action="store_true", help="Run Excel processing tests only")
    parser.add_argument("--downloader", action="store_true", help="Run downloader tests only")
    parser.add_argument("--utils", action="store_true", help="Run utility tests only")
    parser.add_argument("--file-ops", action="store_true", help="Run file operations tests only")
    parser.add_argument("--selenium", action="store_true", help="Run Selenium tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--regression", action="store_true", help="Run regression tests only")
    parser.add_argument("--fast", action="store_true", help="Run fast tests (exclude slow)")
    parser.add_argument("--slow", action="store_true", help="Run slow tests only")
    
    # Test execution options
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet output")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--timeout", action="store_true", help="Enable test timeouts")
    parser.add_argument("--html", action="store_true", help="Generate HTML test report")
    parser.add_argument("--junit", action="store_true", help="Generate JUnit XML report")
    parser.add_argument("--failed", action="store_true", help="Run only failed tests")
    parser.add_argument("--new", action="store_true", help="Run only new tests")
    parser.add_argument("-x", "--stop-on-failure", action="store_true", help="Stop on first failure")
    parser.add_argument("--max-fail", type=int, help="Stop after N failures")
    parser.add_argument("-m", "--markers", help="Run tests with specific markers")
    parser.add_argument("-k", help="Run tests matching expression")
    
    # Utility options
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies")
    parser.add_argument("--info", action="store_true", help="Show test information")
    
    args = parser.parse_args()
    
    # Handle utility options
    if args.install_deps:
        return install_dependencies()
    
    if args.info:
        show_test_info()
        return 0
    
    # Determine which test suite to run
    suite_to_run = None
    if args.unit:
        suite_to_run = "unit"
    elif args.integration:
        suite_to_run = "integration"
    elif args.csv:
        suite_to_run = "csv"
    elif args.excel:
        suite_to_run = "excel"
    elif args.downloader:
        suite_to_run = "downloader"
    elif args.utils:
        suite_to_run = "utils"
    elif args.file_ops:
        suite_to_run = "file_operations"
    elif args.selenium:
        suite_to_run = "selenium"
    elif args.performance:
        suite_to_run = "performance"
    elif args.regression:
        suite_to_run = "regression"
    elif args.fast:
        suite_to_run = "fast"
    elif args.slow:
        suite_to_run = "slow"
    
    # Run tests
    if suite_to_run:
        return run_specific_test_suite(suite_to_run)
    else:
        return run_tests_with_options(args)


if __name__ == "__main__":
    sys.exit(main()) 