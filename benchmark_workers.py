#!/usr/bin/env python3
"""
Benchmark script for CoupaDownloads worker performance testing.
Tests different worker counts (1-6) for 300 seconds each, measuring:
- POs processed
- MB downloaded

Creates separate input.csv copies for each test configuration.
"""

import os
import sys
import time
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Dict, List
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BenchmarkRunner:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.original_input = project_root / "data" / "input" / "input.csv"
        self.download_root = project_root / "download"
        self.results = []

    def get_directory_size_mb(self, path: Path) -> float:
        """Calculate directory size in MB."""
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size / (1024 * 1024)

    def count_processed_pos(self, log_content: str) -> int:
        """Count processed POs from log content."""
        # Look for various completion patterns
        completed_patterns = [
            "COMPLETED",  # Status code
            "completed_tasks",  # Progress messages
            "_COMPLETED",  # File suffixes
            "success': True",  # JSON success indicators
        ]
        
        total_completed = 0
        for pattern in completed_patterns:
            total_completed += log_content.count(pattern)
        
        # Also look for progress messages like "Progress: X/Y completed"
        import re
        progress_matches = re.findall(r'Progress:\s*(\d+)/\d+\s*completed', log_content)
        if progress_matches:
            # Take the highest progress number found
            max_progress = max(int(match) for match in progress_matches)
            total_completed = max(total_completed, max_progress)
        
        return total_completed

    def run_single_test(self, worker_count: int) -> Dict:
        """Run a single benchmark test with specified worker count."""
        logger.info(f"Starting benchmark test with {worker_count} workers")

        # Create input copy or use existing
        test_input = self.project_root / "data" / "input" / f"input_worker_{worker_count}.csv"
        if not test_input.exists():
            shutil.copy2(self.original_input, test_input)
            logger.info(f"Created input copy: {test_input}")
        else:
            logger.info(f"Using existing input file: {test_input}")

        # Clean download directory for this test
        test_download_dir = self.download_root / f"benchmark_worker_{worker_count}"
        if test_download_dir.exists():
            shutil.rmtree(test_download_dir)
        test_download_dir.mkdir(parents=True, exist_ok=True)

        # Record initial state
        initial_size = self.get_directory_size_mb(test_download_dir)

        # Prepare environment variables for the test
        env = os.environ.copy()
        env.update({
            "MAX_PARALLEL_WORKERS": str(worker_count),
            "COUPA_DOWNLOAD_ROOT": str(test_download_dir),
            "COUPA_INPUT_FILE": str(test_input),
            "COUPA_LOG_LEVEL": "INFO",
            "ENABLE_INTERACTIVE_UI": "False"  # Disable interactive mode for benchmark
        })

        # Start the process
        cmd = [sys.executable, "-m", "EXPERIMENTAL.core.main"]
        process = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Collect output
        output_lines = []
        start_time = time.time()

        def read_output():
            if process.stdout:
                for line in process.stdout:
                    output_lines.append(line.strip())
                    # Log progress every 10 seconds
                    if int(time.time() - start_time) % 10 == 0:
                        logger.info(f"Test running with {worker_count} workers, elapsed: {int(time.time() - start_time)}s")

        # Start output reader thread
        output_thread = threading.Thread(target=read_output, daemon=True)
        output_thread.start()

        # Wait for 300 seconds
        time.sleep(300)

        # Terminate the process
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

        # Calculate metrics
        end_time = time.time()
        final_size = self.get_directory_size_mb(test_download_dir)
        downloaded_mb = final_size - initial_size

        # Analyze logs
        full_output = "\n".join(output_lines)
        processed_pos = self.count_processed_pos(full_output)

        result = {
            "worker_count": worker_count,
            "duration_seconds": end_time - start_time,
            "processed_pos": processed_pos,
            "downloaded_mb": downloaded_mb,
            "input_file": str(test_input),
            "download_dir": str(test_download_dir),
            "log_sample": full_output[-2000:]  # Last 2000 chars for debugging
        }

        logger.info(f"Benchmark test completed: {result}")
        return result

    def run_all_tests(self) -> List[Dict]:
        """Run benchmark tests for worker counts 1 through 6."""
        logger.info("Starting benchmark suite")

        for worker_count in range(1, 7):  # 1 to 6 workers
            try:
                result = self.run_single_test(worker_count)
                self.results.append(result)

                # Brief pause between tests
                time.sleep(2)

            except Exception as e:
                logger.error(f"Test failed for {worker_count} workers: {str(e)}")
                self.results.append({
                    "worker_count": worker_count,
                    "error": str(e)
                })

        return self.results

    def save_results(self, results: List[Dict], output_file: Path):
        """Save benchmark results to file."""
        import json

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to: {output_file}")

def main():
    project_root = Path(__file__).parent

    # Ensure we're in the right directory
    if not (project_root / "pyproject.toml").exists():
        logger.error("Not in project root directory")
        sys.exit(1)

    # Create benchmark runner
    runner = BenchmarkRunner(project_root)

    # Run all tests
    results = runner.run_all_tests()

    # Save results
    results_file = project_root / "benchmark_results.json"
    runner.save_results(results, results_file)

    # Print summary
    print("\n=== BENCHMARK RESULTS SUMMARY ===")
    print(f"{'Workers':<8} {'POs':<8} {'MB':<8}")
    print("-" * 30)

    for result in results:
        if "error" in result:
            print(f"{result['worker_count']:<8} ERROR: {result['error']}")
        else:
            print(f"{result['worker_count']:<8} {result['processed_pos']:<8} {result['downloaded_mb']:<8.2f}")

    print(f"\nDetailed results saved to: {results_file}")

if __name__ == "__main__":
    main()