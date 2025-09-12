"""
EmbeddingGemma Performance Benchmarks
Comprehensive performance testing and benchmarking for EmbeddingGemma integration
"""

import os
import time
import json
import psutil
import traceback
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np

# Optional imports for advanced profiling
try:
    import memory_profiler
    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False

try:
    import line_profiler
    LINE_PROFILER_AVAILABLE = True
except ImportError:
    LINE_PROFILER_AVAILABLE = False

# Core ML libraries
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import torch
    ML_LIBRARIES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ML libraries not available: {e}")
    ML_LIBRARIES_AVAILABLE = False

# Configuration
from config import get_config, get_assessment_config


@dataclass
class BenchmarkResult:
    """Result of a performance benchmark."""
    benchmark_name: str
    duration: float
    memory_usage_mb: float
    cpu_usage_percent: float
    throughput: float
    error_rate: float
    metadata: Dict[str, Any]
    timestamp: str = ""


@dataclass
class PerformanceProfile:
    """Comprehensive performance profile."""
    model_load_time: float
    memory_peak_mb: float
    memory_average_mb: float
    cpu_peak_percent: float
    cpu_average_percent: float
    embedding_speed_docs_per_second: float
    batch_efficiency: float
    cache_hit_rate: float
    error_rate: float
    scalability_score: float


class EmbeddingGemmaPerformanceBenchmark:
    """Comprehensive performance benchmarking for EmbeddingGemma."""
    
    def __init__(self):
        self.config = get_config()
        self.assessment_config = get_assessment_config()
        self.model = None
        self.results: List[BenchmarkResult] = []
        self.performance_profile = PerformanceProfile(
            model_load_time=0.0,
            memory_peak_mb=0.0,
            memory_average_mb=0.0,
            cpu_peak_percent=0.0,
            cpu_average_percent=0.0,
            embedding_speed_docs_per_second=0.0,
            batch_efficiency=0.0,
            cache_hit_rate=0.0,
            error_rate=0.0,
            scalability_score=0.0
        )
        
        # Create test data
        self._create_test_data()
    
    def _create_test_data(self):
        """Create comprehensive test data for benchmarking."""
        # Create test documents of varying sizes
        self.test_documents = {
            "short": [f"Short document {i}" for i in range(100)],
            "medium": [f"This is a medium length document {i} with more content to test embedding performance." for i in range(100)],
            "long": [f"This is a longer document {i} with significantly more content to test how EmbeddingGemma handles longer texts and whether it maintains performance with increased document length." for i in range(100)],
            "mixed": [f"Mixed length document {i}" + (" with additional content" * (i % 3)) for i in range(100)]
        }
        
        # Create batch sizes for testing
        self.batch_sizes = [1, 4, 8, 16, 32, 64, 128]
        
        # Create sequence lengths for testing
        self.sequence_lengths = [64, 128, 256, 512, 1024]
    
    def run_complete_benchmark_suite(self) -> Dict[str, Any]:
        """Run complete performance benchmark suite."""
        print("🚀 Starting EmbeddingGemma Performance Benchmark Suite")
        print("=" * 70)
        
        benchmark_results = {
            "start_time": datetime.now().isoformat(),
            "config": asdict(self.config),
            "benchmarks": [],
            "performance_profile": {},
            "recommendations": []
        }
        
        try:
            # Benchmark 1: Model Loading Performance
            print("\n📦 Benchmarking Model Loading...")
            load_result = self._benchmark_model_loading()
            benchmark_results["benchmarks"].append(asdict(load_result))
            
            if not load_result.error_rate == 0:
                benchmark_results["recommendations"].append("Model loading failed - check dependencies")
                return benchmark_results
            
            # Benchmark 2: Memory Usage Patterns
            print("\n💾 Benchmarking Memory Usage...")
            memory_result = self._benchmark_memory_usage()
            benchmark_results["benchmarks"].append(asdict(memory_result))
            
            # Benchmark 3: CPU Usage Patterns
            print("\n🖥️ Benchmarking CPU Usage...")
            cpu_result = self._benchmark_cpu_usage()
            benchmark_results["benchmarks"].append(asdict(cpu_result))
            
            # Benchmark 4: Embedding Speed
            print("\n⚡ Benchmarking Embedding Speed...")
            speed_result = self._benchmark_embedding_speed()
            benchmark_results["benchmarks"].append(asdict(speed_result))
            
            # Benchmark 5: Batch Processing Efficiency
            print("\n🔄 Benchmarking Batch Processing...")
            batch_result = self._benchmark_batch_processing()
            benchmark_results["benchmarks"].append(asdict(batch_result))
            
            # Benchmark 6: Scalability Testing
            print("\n📈 Benchmarking Scalability...")
            scalability_result = self._benchmark_scalability()
            benchmark_results["benchmarks"].append(asdict(scalability_result))
            
            # Benchmark 7: Memory Profiling
            if MEMORY_PROFILER_AVAILABLE:
                print("\n🔍 Running Memory Profiling...")
                memory_profile_result = self._benchmark_memory_profiling()
                benchmark_results["benchmarks"].append(asdict(memory_profile_result))
            
            # Calculate performance profile
            benchmark_results["performance_profile"] = asdict(self._calculate_performance_profile())
            
            # Generate recommendations
            benchmark_results["recommendations"] = self._generate_performance_recommendations()
            
        except Exception as e:
            print(f"❌ Benchmark suite failed: {e}")
            benchmark_results["error"] = str(e)
            benchmark_results["traceback"] = traceback.format_exc()
        
        benchmark_results["end_time"] = datetime.now().isoformat()
        
        # Save results
        self._save_benchmark_results(benchmark_results)
        
        return benchmark_results
    
    def _benchmark_model_loading(self) -> BenchmarkResult:
        """Benchmark model loading performance."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            if not ML_LIBRARIES_AVAILABLE:
                return BenchmarkResult(
                    benchmark_name="model_loading",
                    duration=0.0,
                    memory_usage_mb=0.0,
                    cpu_usage_percent=0.0,
                    throughput=0.0,
                    error_rate=1.0,
                    metadata={"error": "ML libraries not available"}
                )
            
            # Load model
            self.model = SentenceTransformer(
                self.config.model_name,
                cache_folder=self.config.model_cache_dir,
                device=self.config.device
            )
            
            duration = time.time() - start_time
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_usage = end_memory - start_memory
            
            self.performance_profile.model_load_time = duration
            self.performance_profile.memory_peak_mb = end_memory
            
            return BenchmarkResult(
                benchmark_name="model_loading",
                duration=duration,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=0.0,  # Model loading is mostly I/O
                throughput=1.0 / duration if duration > 0 else 0.0,
                error_rate=0.0,
                metadata={
                    "model_name": self.config.model_name,
                    "model_loaded": True,
                    "memory_after_load": end_memory
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name="model_loading",
                duration=time.time() - start_time,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                throughput=0.0,
                error_rate=1.0,
                metadata={"error": str(e)}
            )
    
    def _benchmark_memory_usage(self) -> BenchmarkResult:
        """Benchmark memory usage patterns."""
        start_time = time.time()
        
        try:
            if not self.model:
                return BenchmarkResult(
                    benchmark_name="memory_usage",
                    duration=0.0,
                    memory_usage_mb=0.0,
                    cpu_usage_percent=0.0,
                    throughput=0.0,
                    error_rate=1.0,
                    metadata={"error": "Model not loaded"}
                )
            
            memory_samples = []
            process = psutil.Process()
            
            # Test memory usage with different document sizes
            for doc_type, documents in self.test_documents.items():
                initial_memory = process.memory_info().rss / 1024 / 1024
                
                # Process documents
                embeddings = self.model.encode(documents[:10])  # Process 10 docs
                
                final_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append({
                    "doc_type": doc_type,
                    "initial_memory": initial_memory,
                    "final_memory": final_memory,
                    "memory_increase": final_memory - initial_memory
                })
            
            duration = time.time() - start_time
            
            # Calculate average memory usage
            avg_memory_increase = np.mean([sample["memory_increase"] for sample in memory_samples])
            peak_memory = max([sample["final_memory"] for sample in memory_samples])
            
            self.performance_profile.memory_average_mb = avg_memory_increase
            self.performance_profile.memory_peak_mb = peak_memory
            
            return BenchmarkResult(
                benchmark_name="memory_usage",
                duration=duration,
                memory_usage_mb=avg_memory_increase,
                cpu_usage_percent=0.0,
                throughput=len(memory_samples) / duration,
                error_rate=0.0,
                metadata={
                    "memory_samples": memory_samples,
                    "peak_memory": peak_memory,
                    "average_increase": avg_memory_increase
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name="memory_usage",
                duration=time.time() - start_time,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                throughput=0.0,
                error_rate=1.0,
                metadata={"error": str(e)}
            )
    
    def _benchmark_cpu_usage(self) -> BenchmarkResult:
        """Benchmark CPU usage patterns."""
        start_time = time.time()
        
        try:
            if not self.model:
                return BenchmarkResult(
                    benchmark_name="cpu_usage",
                    duration=0.0,
                    memory_usage_mb=0.0,
                    cpu_usage_percent=0.0,
                    throughput=0.0,
                    error_rate=1.0,
                    metadata={"error": "Model not loaded"}
                )
            
            cpu_samples = []
            process = psutil.Process()
            
            # Test CPU usage with different batch sizes
            for batch_size in [1, 8, 16, 32]:
                # Start CPU monitoring
                cpu_percent = process.cpu_percent()
                
                # Process documents
                documents = self.test_documents["medium"][:batch_size]
                embeddings = self.model.encode(documents)
                
                # Get CPU usage after processing
                cpu_after = process.cpu_percent()
                
                cpu_samples.append({
                    "batch_size": batch_size,
                    "cpu_before": cpu_percent,
                    "cpu_after": cpu_after,
                    "cpu_increase": cpu_after - cpu_percent
                })
            
            duration = time.time() - start_time
            
            # Calculate average CPU usage
            avg_cpu_increase = np.mean([sample["cpu_increase"] for sample in cpu_samples])
            peak_cpu = max([sample["cpu_after"] for sample in cpu_samples])
            
            self.performance_profile.cpu_average_percent = avg_cpu_increase
            self.performance_profile.cpu_peak_percent = peak_cpu
            
            return BenchmarkResult(
                benchmark_name="cpu_usage",
                duration=duration,
                memory_usage_mb=0.0,
                cpu_usage_percent=avg_cpu_increase,
                throughput=len(cpu_samples) / duration,
                error_rate=0.0,
                metadata={
                    "cpu_samples": cpu_samples,
                    "peak_cpu": peak_cpu,
                    "average_increase": avg_cpu_increase
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name="cpu_usage",
                duration=time.time() - start_time,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                throughput=0.0,
                error_rate=1.0,
                metadata={"error": str(e)}
            )
    
    def _benchmark_embedding_speed(self) -> BenchmarkResult:
        """Benchmark embedding generation speed."""
        start_time = time.time()
        
        try:
            if not self.model:
                return BenchmarkResult(
                    benchmark_name="embedding_speed",
                    duration=0.0,
                    memory_usage_mb=0.0,
                    cpu_usage_percent=0.0,
                    throughput=0.0,
                    error_rate=1.0,
                    metadata={"error": "Model not loaded"}
                )
            
            speed_results = []
            
            # Test speed with different document types
            for doc_type, documents in self.test_documents.items():
                test_docs = documents[:20]  # Test with 20 documents
                
                doc_start = time.time()
                embeddings = self.model.encode(test_docs)
                doc_duration = time.time() - doc_start
                
                docs_per_second = len(test_docs) / doc_duration
                
                speed_results.append({
                    "doc_type": doc_type,
                    "documents": len(test_docs),
                    "duration": doc_duration,
                    "docs_per_second": docs_per_second,
                    "avg_time_per_doc": doc_duration / len(test_docs)
                })
            
            duration = time.time() - start_time
            
            # Calculate average speed
            avg_docs_per_second = np.mean([result["docs_per_second"] for result in speed_results])
            self.performance_profile.embedding_speed_docs_per_second = avg_docs_per_second
            
            return BenchmarkResult(
                benchmark_name="embedding_speed",
                duration=duration,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                throughput=avg_docs_per_second,
                error_rate=0.0,
                metadata={
                    "speed_results": speed_results,
                    "average_docs_per_second": avg_docs_per_second
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name="embedding_speed",
                duration=time.time() - start_time,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                throughput=0.0,
                error_rate=1.0,
                metadata={"error": str(e)}
            )
    
    def _benchmark_batch_processing(self) -> BenchmarkResult:
        """Benchmark batch processing efficiency."""
        start_time = time.time()
        
        try:
            if not self.model:
                return BenchmarkResult(
                    benchmark_name="batch_processing",
                    duration=0.0,
                    memory_usage_mb=0.0,
                    cpu_usage_percent=0.0,
                    throughput=0.0,
                    error_rate=1.0,
                    metadata={"error": "Model not loaded"}
                )
            
            batch_results = []
            test_documents = self.test_documents["medium"][:50]  # Use 50 documents
            
            # Test different batch sizes
            for batch_size in self.batch_sizes:
                if batch_size > len(test_documents):
                    continue
                
                batch_start = time.time()
                batch_embeddings = self.model.encode(
                    test_documents[:batch_size],
                    batch_size=batch_size,
                    show_progress_bar=False
                )
                batch_duration = time.time() - batch_start
                
                docs_per_second = batch_size / batch_duration
                efficiency = docs_per_second / batch_size  # Efficiency per document
                
                batch_results.append({
                    "batch_size": batch_size,
                    "duration": batch_duration,
                    "docs_per_second": docs_per_second,
                    "efficiency": efficiency
                })
            
            duration = time.time() - start_time
            
            # Calculate batch efficiency
            max_efficiency = max([result["efficiency"] for result in batch_results])
            optimal_batch_size = max(batch_results, key=lambda x: x["efficiency"])["batch_size"]
            
            self.performance_profile.batch_efficiency = max_efficiency
            
            return BenchmarkResult(
                benchmark_name="batch_processing",
                duration=duration,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                throughput=max_efficiency,
                error_rate=0.0,
                metadata={
                    "batch_results": batch_results,
                    "optimal_batch_size": optimal_batch_size,
                    "max_efficiency": max_efficiency
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name="batch_processing",
                duration=time.time() - start_time,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                throughput=0.0,
                error_rate=1.0,
                metadata={"error": str(e)}
            )
    
    def _benchmark_scalability(self) -> BenchmarkResult:
        """Benchmark scalability with increasing document counts."""
        start_time = time.time()
        
        try:
            if not self.model:
                return BenchmarkResult(
                    benchmark_name="scalability",
                    duration=0.0,
                    memory_usage_mb=0.0,
                    cpu_usage_percent=0.0,
                    throughput=0.0,
                    error_rate=1.0,
                    metadata={"error": "Model not loaded"}
                )
            
            scalability_results = []
            document_counts = [10, 25, 50, 100, 200]
            
            for doc_count in document_counts:
                if doc_count > len(self.test_documents["medium"]):
                    continue
                
                test_docs = self.test_documents["medium"][:doc_count]
                
                scale_start = time.time()
                embeddings = self.model.encode(test_docs)
                scale_duration = time.time() - scale_start
                
                docs_per_second = doc_count / scale_duration
                
                scalability_results.append({
                    "document_count": doc_count,
                    "duration": scale_duration,
                    "docs_per_second": docs_per_second,
                    "time_per_doc": scale_duration / doc_count
                })
            
            duration = time.time() - start_time
            
            # Calculate scalability score (how well performance scales)
            if len(scalability_results) >= 2:
                # Compare performance at different scales
                small_scale = scalability_results[0]["docs_per_second"]
                large_scale = scalability_results[-1]["docs_per_second"]
                scalability_score = large_scale / small_scale if small_scale > 0 else 0
            else:
                scalability_score = 1.0
            
            self.performance_profile.scalability_score = scalability_score
            
            return BenchmarkResult(
                benchmark_name="scalability",
                duration=duration,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                throughput=scalability_score,
                error_rate=0.0,
                metadata={
                    "scalability_results": scalability_results,
                    "scalability_score": scalability_score
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name="scalability",
                duration=time.time() - start_time,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                throughput=0.0,
                error_rate=1.0,
                metadata={"error": str(e)}
            )
    
    def _benchmark_memory_profiling(self) -> BenchmarkResult:
        """Benchmark with detailed memory profiling."""
        start_time = time.time()
        
        try:
            if not MEMORY_PROFILER_AVAILABLE:
                return BenchmarkResult(
                    benchmark_name="memory_profiling",
                    duration=0.0,
                    memory_usage_mb=0.0,
                    cpu_usage_percent=0.0,
                    throughput=0.0,
                    error_rate=1.0,
                    metadata={"error": "Memory profiler not available"}
                )
            
            if not self.model:
                return BenchmarkResult(
                    benchmark_name="memory_profiling",
                    duration=0.0,
                    memory_usage_mb=0.0,
                    cpu_usage_percent=0.0,
                    throughput=0.0,
                    error_rate=1.0,
                    metadata={"error": "Model not loaded"}
                )
            
            # Use memory_profiler to profile embedding generation
            @memory_profiler.profile
            def profile_embedding_generation():
                test_docs = self.test_documents["medium"][:20]
                return self.model.encode(test_docs)
            
            embeddings = profile_embedding_generation()
            
            duration = time.time() - start_time
            
            return BenchmarkResult(
                benchmark_name="memory_profiling",
                duration=duration,
                memory_usage_mb=0.0,  # Memory usage is tracked by profiler
                cpu_usage_percent=0.0,
                throughput=20 / duration,
                error_rate=0.0,
                metadata={
                    "profiled_function": "embedding_generation",
                    "documents_profiled": 20,
                    "profiler_available": True
                }
            )
            
        except Exception as e:
            return BenchmarkResult(
                benchmark_name="memory_profiling",
                duration=time.time() - start_time,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                throughput=0.0,
                error_rate=1.0,
                metadata={"error": str(e)}
            )
    
    def _calculate_performance_profile(self) -> PerformanceProfile:
        """Calculate comprehensive performance profile."""
        # Update profile with benchmark results
        profile = self.performance_profile
        
        # Calculate error rate from all benchmarks
        total_benchmarks = len(self.results)
        failed_benchmarks = sum(1 for r in self.results if r.error_rate > 0)
        profile.error_rate = failed_benchmarks / total_benchmarks if total_benchmarks > 0 else 0
        
        return profile
    
    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance recommendations based on benchmarks."""
        recommendations = []
        
        # Memory recommendations
        if self.performance_profile.memory_peak_mb > 200:
            recommendations.append("💾 Memory usage exceeds target - consider quantization or model optimization")
        elif self.performance_profile.memory_peak_mb < 100:
            recommendations.append("✅ Memory usage is excellent - well within target range")
        
        # Speed recommendations
        if self.performance_profile.embedding_speed_docs_per_second < 10:
            recommendations.append("⚡ Embedding speed is slow - consider batch processing optimization")
        elif self.performance_profile.embedding_speed_docs_per_second > 50:
            recommendations.append("🚀 Embedding speed is excellent - suitable for high-throughput applications")
        
        # Batch efficiency recommendations
        if self.performance_profile.batch_efficiency < 0.5:
            recommendations.append("🔄 Batch processing efficiency is low - optimize batch sizes")
        elif self.performance_profile.batch_efficiency > 1.0:
            recommendations.append("✅ Batch processing is highly efficient")
        
        # Scalability recommendations
        if self.performance_profile.scalability_score < 0.8:
            recommendations.append("📈 Scalability is poor - performance degrades with scale")
        elif self.performance_profile.scalability_score > 1.2:
            recommendations.append("📈 Excellent scalability - performance improves with scale")
        
        # Error rate recommendations
        if self.performance_profile.error_rate > 0.1:
            recommendations.append("❌ High error rate - investigate stability issues")
        elif self.performance_profile.error_rate == 0:
            recommendations.append("✅ No errors detected - system is stable")
        
        return recommendations
    
    def _save_benchmark_results(self, results: Dict[str, Any]):
        """Save benchmark results to file."""
        output_file = Path(self.config.output_dir) / f"performance_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"📊 Benchmark results saved to: {output_file}")


def main():
    """Run the performance benchmark suite."""
    print("🚀 EmbeddingGemma Performance Benchmark Suite")
    print("=" * 70)
    
    benchmark = EmbeddingGemmaPerformanceBenchmark()
    results = benchmark.run_complete_benchmark_suite()
    
    print("\n📋 Performance Summary:")
    profile = results.get('performance_profile', {})
    print(f"Model Load Time: {profile.get('model_load_time', 0):.2f}s")
    print(f"Memory Peak: {profile.get('memory_peak_mb', 0):.1f} MB")
    print(f"Embedding Speed: {profile.get('embedding_speed_docs_per_second', 0):.1f} docs/sec")
    print(f"Batch Efficiency: {profile.get('batch_efficiency', 0):.2f}")
    print(f"Scalability Score: {profile.get('scalability_score', 0):.2f}")
    print(f"Error Rate: {profile.get('error_rate', 0):.1%}")
    
    print("\n💡 Performance Recommendations:")
    for rec in results.get('recommendations', []):
        print(f"  {rec}")
    
    return results


if __name__ == "__main__":
    main()

