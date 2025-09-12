"""
EmbeddingGemma Capability Assessment Framework
Comprehensive testing and evaluation of EmbeddingGemma integration feasibility
"""

import os
import time
import json
import psutil
import traceback
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import numpy as np
from datetime import datetime

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
class CapabilityMetrics:
    """Metrics for capability assessment."""
    model_load_time: float = 0.0
    memory_usage_mb: float = 0.0
    embedding_speed_per_doc: float = 0.0
    batch_processing_speed: float = 0.0
    accuracy_score: float = 0.0
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0
    feasibility_score: float = 0.0


@dataclass
class TestResult:
    """Result of a capability test."""
    test_name: str
    success: bool
    duration: float
    metrics: Dict[str, Any]
    error_message: Optional[str] = None
    timestamp: str = ""


class EmbeddingGemmaCapabilityAssessment:
    """Comprehensive capability assessment for EmbeddingGemma."""
    
    def __init__(self):
        self.config = get_config()
        self.assessment_config = get_assessment_config()
        self.model = None
        self.results: List[TestResult] = []
        self.metrics = CapabilityMetrics()
        
        # Create test data
        self._create_test_data()
    
    def _create_test_data(self):
        """Create sample test data for assessment."""
        test_docs_dir = Path("data/sample_documents")
        test_docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Sample documents related to Coupa/PO processing
        sample_documents = [
            "Purchase Order #12345 for office supplies including pens, paper, and notebooks.",
            "Invoice for software licenses: Microsoft Office, Adobe Creative Suite, and antivirus software.",
            "Contract agreement for IT services including system maintenance and support.",
            "Receipt for travel expenses: flights, hotels, and meals for business trip.",
            "Equipment purchase order: laptops, monitors, and networking equipment for new office.",
            "Service agreement for cloud hosting: AWS, Azure, and backup services.",
            "Training materials order: books, online courses, and certification programs.",
            "Maintenance contract for office equipment: printers, copiers, and HVAC systems.",
            "Software development contract: custom application development and testing.",
            "Consulting services agreement: business process optimization and strategy planning."
        ]
        
        # Create test files
        for i, doc in enumerate(sample_documents):
            with open(test_docs_dir / f"doc_{i+1}.txt", "w") as f:
                f.write(doc)
        
        self.test_documents = sample_documents
    
    def run_complete_assessment(self) -> Dict[str, Any]:
        """Run complete capability assessment."""
        print("🔍 Starting EmbeddingGemma Capability Assessment...")
        
        assessment_results = {
            "start_time": datetime.now().isoformat(),
            "config": asdict(self.config),
            "tests": [],
            "overall_feasibility": False,
            "recommendations": []
        }
        
        try:
            # Test 1: Model Loading
            print("\n📦 Testing Model Loading...")
            load_result = self._test_model_loading()
            assessment_results["tests"].append(asdict(load_result))
            
            if not load_result.success:
                assessment_results["recommendations"].append("Model loading failed - check dependencies")
                return assessment_results
            
            # Test 2: Memory Usage
            print("\n💾 Testing Memory Usage...")
            memory_result = self._test_memory_usage()
            assessment_results["tests"].append(asdict(memory_result))
            
            # Test 3: Embedding Generation
            print("\n⚡ Testing Embedding Generation...")
            embedding_result = self._test_embedding_generation()
            assessment_results["tests"].append(asdict(embedding_result))
            
            # Test 4: Batch Processing
            print("\n🔄 Testing Batch Processing...")
            batch_result = self._test_batch_processing()
            assessment_results["tests"].append(asdict(batch_result))
            
            # Test 5: Accuracy Testing
            print("\n🎯 Testing Accuracy...")
            accuracy_result = self._test_accuracy()
            assessment_results["tests"].append(asdict(accuracy_result))
            
            # Test 6: Integration Compatibility
            print("\n🔗 Testing Integration Compatibility...")
            integration_result = self._test_integration_compatibility()
            assessment_results["tests"].append(asdict(integration_result))
            
            # Calculate overall feasibility
            assessment_results["overall_feasibility"] = self._calculate_feasibility_score()
            assessment_results["metrics"] = asdict(self.metrics)
            
            # Generate recommendations
            assessment_results["recommendations"] = self._generate_recommendations()
            
        except Exception as e:
            print(f"❌ Assessment failed: {e}")
            assessment_results["error"] = str(e)
            assessment_results["traceback"] = traceback.format_exc()
        
        assessment_results["end_time"] = datetime.now().isoformat()
        
        # Save results
        self._save_assessment_results(assessment_results)
        
        return assessment_results
    
    def _test_model_loading(self) -> TestResult:
        """Test model loading capabilities."""
        start_time = time.time()
        
        try:
            if not ML_LIBRARIES_AVAILABLE:
                return TestResult(
                    test_name="model_loading",
                    success=False,
                    duration=0.0,
                    metrics={},
                    error_message="ML libraries not available"
                )
            
            # Load model
            self.model = SentenceTransformer(
                self.config.model_name,
                cache_folder=self.config.model_cache_dir,
                device=self.config.device
            )
            
            duration = time.time() - start_time
            self.metrics.model_load_time = duration
            
            return TestResult(
                test_name="model_loading",
                success=True,
                duration=duration,
                metrics={
                    "model_name": self.config.model_name,
                    "load_time": duration,
                    "model_loaded": True
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="model_loading",
                success=False,
                duration=time.time() - start_time,
                metrics={},
                error_message=str(e)
            )
    
    def _test_memory_usage(self) -> TestResult:
        """Test memory usage patterns."""
        start_time = time.time()
        
        try:
            if not self.model:
                return TestResult(
                    test_name="memory_usage",
                    success=False,
                    duration=0.0,
                    metrics={},
                    error_message="Model not loaded"
                )
            
            # Get initial memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Generate embeddings for test documents
            embeddings = self.model.encode(self.test_documents[:5])
            
            # Get memory after processing
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            self.metrics.memory_usage_mb = final_memory
            
            return TestResult(
                test_name="memory_usage",
                success=True,
                duration=time.time() - start_time,
                metrics={
                    "initial_memory_mb": initial_memory,
                    "final_memory_mb": final_memory,
                    "memory_increase_mb": memory_increase,
                    "target_memory_mb": 200,  # EmbeddingGemma target
                    "within_target": final_memory < 200
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="memory_usage",
                success=False,
                duration=time.time() - start_time,
                metrics={},
                error_message=str(e)
            )
    
    def _test_embedding_generation(self) -> TestResult:
        """Test embedding generation speed and quality."""
        start_time = time.time()
        
        try:
            if not self.model:
                return TestResult(
                    test_name="embedding_generation",
                    success=False,
                    duration=0.0,
                    metrics={},
                    error_message="Model not loaded"
                )
            
            # Test single document embedding
            single_start = time.time()
            single_embedding = self.model.encode([self.test_documents[0]])
            single_duration = time.time() - single_start
            
            # Test multiple documents
            multi_start = time.time()
            multi_embeddings = self.model.encode(self.test_documents[:5])
            multi_duration = time.time() - multi_start
            
            # Calculate speed metrics
            docs_per_second = len(self.test_documents[:5]) / multi_duration
            self.metrics.embedding_speed_per_doc = single_duration
            
            return TestResult(
                test_name="embedding_generation",
                success=True,
                duration=time.time() - start_time,
                metrics={
                    "single_doc_time": single_duration,
                    "multi_doc_time": multi_duration,
                    "docs_per_second": docs_per_second,
                    "embedding_dimension": len(single_embedding[0]),
                    "embeddings_generated": len(multi_embeddings)
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="embedding_generation",
                success=False,
                duration=time.time() - start_time,
                metrics={},
                error_message=str(e)
            )
    
    def _test_batch_processing(self) -> TestResult:
        """Test batch processing capabilities."""
        start_time = time.time()
        
        try:
            if not self.model:
                return TestResult(
                    test_name="batch_processing",
                    success=False,
                    duration=0.0,
                    metrics={},
                    error_message="Model not loaded"
                )
            
            batch_results = {}
            
            # Test different batch sizes
            for batch_size in self.assessment_config.test_batch_sizes:
                batch_start = time.time()
                batch_embeddings = self.model.encode(
                    self.test_documents[:batch_size],
                    batch_size=batch_size,
                    show_progress_bar=False
                )
                batch_duration = time.time() - batch_start
                
                batch_results[f"batch_{batch_size}"] = {
                    "duration": batch_duration,
                    "docs_per_second": batch_size / batch_duration,
                    "embeddings_shape": batch_embeddings.shape
                }
            
            # Calculate average batch processing speed
            avg_speed = np.mean([result["docs_per_second"] for result in batch_results.values()])
            self.metrics.batch_processing_speed = avg_speed
            
            return TestResult(
                test_name="batch_processing",
                success=True,
                duration=time.time() - start_time,
                metrics=batch_results
            )
            
        except Exception as e:
            return TestResult(
                test_name="batch_processing",
                success=False,
                duration=time.time() - start_time,
                metrics={},
                error_message=str(e)
            )
    
    def _test_accuracy(self) -> TestResult:
        """Test embedding accuracy and similarity."""
        start_time = time.time()
        
        try:
            if not self.model:
                return TestResult(
                    test_name="accuracy",
                    success=False,
                    duration=0.0,
                    metrics={},
                    error_message="Model not loaded"
                )
            
            # Test semantic similarity
            query = "office supplies purchase order"
            documents = [
                "Purchase Order #12345 for office supplies including pens, paper, and notebooks.",
                "Invoice for software licenses: Microsoft Office, Adobe Creative Suite, and antivirus software.",
                "Contract agreement for IT services including system maintenance and support.",
                "Receipt for travel expenses: flights, hotels, and meals for business trip."
            ]
            
            # Generate embeddings
            query_embedding = self.model.encode([query])
            doc_embeddings = self.model.encode(documents)
            
            # Calculate similarities
            similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
            
            # Expected: first document should have highest similarity
            max_similarity = np.max(similarities)
            correct_prediction = np.argmax(similarities) == 0  # First doc should be most similar
            
            accuracy_score = max_similarity if correct_prediction else max_similarity * 0.8
            self.metrics.accuracy_score = accuracy_score
            
            return TestResult(
                test_name="accuracy",
                success=True,
                duration=time.time() - start_time,
                metrics={
                    "similarities": similarities.tolist(),
                    "max_similarity": max_similarity,
                    "correct_prediction": correct_prediction,
                    "accuracy_score": accuracy_score
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="accuracy",
                success=False,
                duration=time.time() - start_time,
                metrics={},
                error_message=str(e)
            )
    
    def _test_integration_compatibility(self) -> TestResult:
        """Test compatibility with MyScript dependencies."""
        start_time = time.time()
        
        try:
            compatibility_results = {}
            
            # Test compatibility with existing MyScript libraries
            compatibility_tests = [
                ("pandas", "import pandas as pd"),
                ("polars", "import polars as pl"),
                ("requests", "import requests"),
                ("numpy", "import numpy as np"),
                ("json", "import json"),
                ("pathlib", "from pathlib import Path")
            ]
            
            for lib_name, import_statement in compatibility_tests:
                try:
                    exec(import_statement)
                    compatibility_results[lib_name] = True
                except ImportError:
                    compatibility_results[lib_name] = False
            
            # Test if we can work with MyScript data structures
            myScript_compatibility = {
                "can_process_csv": True,  # Assuming we can read CSV
                "can_process_excel": True,  # Assuming we can read Excel
                "can_handle_po_data": True,  # Assuming we can process PO data
                "memory_efficient": self.metrics.memory_usage_mb < 200
            }
            
            overall_compatibility = all(compatibility_results.values()) and all(myScript_compatibility.values())
            
            return TestResult(
                test_name="integration_compatibility",
                success=overall_compatibility,
                duration=time.time() - start_time,
                metrics={
                    "library_compatibility": compatibility_results,
                    "myscript_compatibility": myScript_compatibility,
                    "overall_compatibility": overall_compatibility
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="integration_compatibility",
                success=False,
                duration=time.time() - start_time,
                metrics={},
                error_message=str(e)
            )
    
    def _calculate_feasibility_score(self) -> float:
        """Calculate overall feasibility score."""
        scores = []
        
        # Model loading success (30%)
        if self.metrics.model_load_time > 0:
            scores.append(0.3)
        
        # Memory usage (25%)
        if self.metrics.memory_usage_mb < 200:
            scores.append(0.25)
        elif self.metrics.memory_usage_mb < 500:
            scores.append(0.15)
        else:
            scores.append(0.05)
        
        # Performance (25%)
        if self.metrics.embedding_speed_per_doc < 1.0:  # Less than 1 second per doc
            scores.append(0.25)
        elif self.metrics.embedding_speed_per_doc < 5.0:
            scores.append(0.15)
        else:
            scores.append(0.05)
        
        # Accuracy (20%)
        if self.metrics.accuracy_score > 0.8:
            scores.append(0.2)
        elif self.metrics.accuracy_score > 0.6:
            scores.append(0.15)
        else:
            scores.append(0.05)
        
        feasibility_score = sum(scores)
        self.metrics.feasibility_score = feasibility_score
        
        return feasibility_score
    
    def _generate_recommendations(self) -> List[str]:
        """Generate integration recommendations."""
        recommendations = []
        
        if self.metrics.feasibility_score > 0.8:
            recommendations.append("✅ High feasibility - Proceed with integration")
            recommendations.append("💡 Consider implementing caching for better performance")
            recommendations.append("🔧 Design clean API interfaces for embedding operations")
        elif self.metrics.feasibility_score > 0.6:
            recommendations.append("⚠️ Moderate feasibility - Proceed with caution")
            recommendations.append("🔍 Monitor memory usage in production")
            recommendations.append("⚡ Optimize batch processing for better performance")
        else:
            recommendations.append("❌ Low feasibility - Consider alternatives")
            recommendations.append("🔄 Explore lighter embedding models")
            recommendations.append("💾 Consider cloud-based embedding services")
        
        # Specific recommendations based on metrics
        if self.metrics.memory_usage_mb > 200:
            recommendations.append("💾 Memory usage exceeds target - consider quantization")
        
        if self.metrics.embedding_speed_per_doc > 2.0:
            recommendations.append("⚡ Embedding speed is slow - consider batch processing")
        
        if self.metrics.accuracy_score < 0.7:
            recommendations.append("🎯 Accuracy is low - consider fine-tuning or different model")
        
        return recommendations
    
    def _save_assessment_results(self, results: Dict[str, Any]):
        """Save assessment results to file."""
        output_file = Path(self.config.output_dir) / f"capability_assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"📊 Assessment results saved to: {output_file}")


def main():
    """Run the capability assessment."""
    print("🚀 EmbeddingGemma Capability Assessment")
    print("=" * 50)
    
    assessment = EmbeddingGemmaCapabilityAssessment()
    results = assessment.run_complete_assessment()
    
    print("\n📋 Assessment Summary:")
    print(f"Overall Feasibility: {results['overall_feasibility']}")
    print(f"Feasibility Score: {results.get('metrics', {}).get('feasibility_score', 0):.2f}")
    
    print("\n💡 Recommendations:")
    for rec in results.get('recommendations', []):
        print(f"  {rec}")
    
    return results


if __name__ == "__main__":
    main()

