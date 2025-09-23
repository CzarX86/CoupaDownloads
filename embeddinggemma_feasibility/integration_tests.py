"""
EmbeddingGemma Integration Tests
Comprehensive testing suite for EmbeddingGemma integration with MyScript
"""

import os
import sys
import time
import json
import pytest
import tempfile
from typing import List, Dict, Any, Optional
from pathlib import Path
from unittest.mock import Mock, patch

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_config, get_assessment_config
from capability_assessment import EmbeddingGemmaCapabilityAssessment
from use_case_examples import CoupaDownloadsUseCases


class TestEmbeddingGemmaIntegration:
    """Test suite for EmbeddingGemma integration."""
    
    @pytest.fixture
    def config(self):
        """Get configuration for tests."""
        return get_config()
    
    @pytest.fixture
    def assessment_config(self):
        """Get assessment configuration for tests."""
        return get_assessment_config()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_config_loading(self, config):
        """Test configuration loading."""
        assert config.model_name == "google/embeddinggemma-300m"
        assert config.max_sequence_length == 512
        assert config.batch_size == 32
        assert config.enable_embedding_cache is True
    
    def test_assessment_config(self, assessment_config):
        """Test assessment configuration."""
        assert assessment_config.sample_documents_count == 100
        assert len(assessment_config.test_batch_sizes) > 0
        assert assessment_config.performance_test_duration > 0
    
    def test_directory_creation(self, config):
        """Test that required directories are created."""
        assert os.path.exists(config.model_cache_dir)
        assert os.path.exists(config.cache_dir)
        assert os.path.exists(config.output_dir)
    
    def test_dependencies_available(self):
        """Test that required dependencies are available."""
        pytest.importorskip(
            "sentence_transformers",
            reason="Instale as dependências de ML com `poetry install`."
        )
        pytest.importorskip(
            "torch",
            reason="Pacotes de ML ausentes; utilize `poetry install`."
        )
        pytest.importorskip(
            "numpy",
            reason="NumPy é obrigatório; execute `poetry install`."
        )
        pytest.importorskip(
            "sklearn",
            reason="scikit-learn é obrigatório; execute `poetry install`."
        )

        assert True
    
    def test_capability_assessment_initialization(self):
        """Test capability assessment initialization."""
        assessment = EmbeddingGemmaCapabilityAssessment()
        assert assessment.config is not None
        assert assessment.assessment_config is not None
        assert len(assessment.test_documents) > 0
    
    def test_use_cases_initialization(self):
        """Test use cases initialization."""
        use_cases = CoupaDownloadsUseCases()
        assert len(use_cases.sample_pos) > 0
        assert len(use_cases.sample_attachments) > 0
    
    def test_model_loading_simulation(self):
        """Test model loading simulation (without actually loading)."""
        pytest.importorskip(
            "sentence_transformers",
            reason="Instale as dependências de ML com `poetry install`."
        )

        assessment = EmbeddingGemmaCapabilityAssessment()
        
        # Mock the model loading
        with patch('sentence_transformers.SentenceTransformer') as mock_model:
            mock_model.return_value = Mock()
            result = assessment._test_model_loading()
            
            assert result.test_name == "model_loading"
            assert result.success is True
            assert result.duration > 0
    
    def test_memory_usage_simulation(self):
        """Test memory usage simulation."""
        assessment = EmbeddingGemmaCapabilityAssessment()
        
        # Mock the model
        assessment.model = Mock()
        assessment.model.encode.return_value = [[0.1] * 384]  # Mock embedding
        
        result = assessment._test_memory_usage()
        
        assert result.test_name == "memory_usage"
        assert result.success is True
        assert "initial_memory_mb" in result.metrics
        assert "final_memory_mb" in result.metrics
    
    def test_embedding_generation_simulation(self):
        """Test embedding generation simulation."""
        assessment = EmbeddingGemmaCapabilityAssessment()
        
        # Mock the model
        assessment.model = Mock()
        assessment.model.encode.return_value = [[0.1] * 384]  # Mock embedding
        
        result = assessment._test_embedding_generation()
        
        assert result.test_name == "embedding_generation"
        assert result.success is True
        assert "single_doc_time" in result.metrics
        assert "docs_per_second" in result.metrics
    
    def test_batch_processing_simulation(self):
        """Test batch processing simulation."""
        assessment = EmbeddingGemmaCapabilityAssessment()
        
        # Mock the model
        assessment.model = Mock()
        assessment.model.encode.return_value = [[0.1] * 384]  # Mock embedding
        
        result = assessment._test_batch_processing()
        
        assert result.test_name == "batch_processing"
        assert result.success is True
        assert len(result.metrics) > 0
    
    def test_accuracy_simulation(self):
        """Test accuracy simulation."""
        assessment = EmbeddingGemmaCapabilityAssessment()
        
        # Mock the model and sklearn
        assessment.model = Mock()
        assessment.model.encode.return_value = [[0.1] * 384]  # Mock embedding
        
        with patch('sklearn.metrics.pairwise.cosine_similarity') as mock_similarity:
            mock_similarity.return_value = [[0.9, 0.3, 0.2, 0.1]]  # Mock similarity
            
            result = assessment._test_accuracy()
            
            assert result.test_name == "accuracy"
            assert result.success is True
            assert "accuracy_score" in result.metrics
    
    def test_integration_compatibility(self):
        """Test integration compatibility."""
        assessment = EmbeddingGemmaCapabilityAssessment()
        
        result = assessment._test_integration_compatibility()
        
        assert result.test_name == "integration_compatibility"
        assert result.success is True
        assert "library_compatibility" in result.metrics
        assert "myscript_compatibility" in result.metrics
    
    def test_feasibility_score_calculation(self):
        """Test feasibility score calculation."""
        assessment = EmbeddingGemmaCapabilityAssessment()
        
        # Set some mock metrics
        assessment.metrics.model_load_time = 1.0
        assessment.metrics.memory_usage_mb = 150.0
        assessment.metrics.embedding_speed_per_doc = 0.5
        assessment.metrics.accuracy_score = 0.85
        
        score = assessment._calculate_feasibility_score()
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be high with good metrics
    
    def test_recommendations_generation(self):
        """Test recommendations generation."""
        assessment = EmbeddingGemmaCapabilityAssessment()
        
        # Set some mock metrics
        assessment.metrics.feasibility_score = 0.8
        assessment.metrics.memory_usage_mb = 150.0
        assessment.metrics.embedding_speed_per_doc = 0.5
        assessment.metrics.accuracy_score = 0.85
        
        recommendations = assessment._generate_recommendations()
        
        assert len(recommendations) > 0
        assert any("High feasibility" in rec for rec in recommendations)
    
    def test_use_case_duplicate_detection_simulation(self):
        """Test duplicate detection use case simulation."""
        use_cases = CoupaDownloadsUseCases()
        
        # Mock the model
        use_cases.model = Mock()
        use_cases.model.encode.return_value = [[0.1] * 384]  # Mock embedding
        
        with patch('sklearn.metrics.pairwise.cosine_similarity') as mock_similarity:
            # Mock similarity matrix with some high similarities
            mock_similarity.return_value = [[1.0, 0.2, 0.1, 0.3, 0.1],
                                          [0.2, 1.0, 0.1, 0.2, 0.1],
                                          [0.1, 0.1, 1.0, 0.1, 0.2],
                                          [0.3, 0.2, 0.1, 1.0, 0.1],
                                          [0.1, 0.1, 0.2, 0.1, 1.0]]
            
            result = use_cases.use_case_duplicate_detection()
            
            assert result.use_case == "duplicate_detection"
            assert result.success is True
            assert "duplicate_candidates_found" in result.performance_metrics
    
    def test_use_case_semantic_search_simulation(self):
        """Test semantic search use case simulation."""
        use_cases = CoupaDownloadsUseCases()
        
        # Mock the model
        use_cases.model = Mock()
        use_cases.model.encode.return_value = [[0.1] * 384]  # Mock embedding
        
        with patch('sklearn.metrics.pairwise.cosine_similarity') as mock_similarity:
            # Mock similarity results
            mock_similarity.return_value = [[0.8, 0.3, 0.2, 0.1, 0.4],
                                          [0.2, 0.9, 0.1, 0.3, 0.2],
                                          [0.1, 0.2, 0.8, 0.1, 0.3],
                                          [0.3, 0.1, 0.2, 0.9, 0.1]]
            
            result = use_cases.use_case_semantic_search()
            
            assert result.use_case == "semantic_search"
            assert result.success is True
            assert "queries_processed" in result.performance_metrics
    
    def test_use_case_content_classification_simulation(self):
        """Test content classification use case simulation."""
        use_cases = CoupaDownloadsUseCases()
        
        # Mock the model
        use_cases.model = Mock()
        use_cases.model.encode.return_value = [[0.1] * 384]  # Mock embedding
        
        with patch('sklearn.metrics.pairwise.cosine_similarity') as mock_similarity:
            # Mock similarity results
            mock_similarity.return_value = [[0.8, 0.2, 0.1, 0.3],
                                          [0.1, 0.9, 0.2, 0.1],
                                          [0.2, 0.1, 0.8, 0.2],
                                          [0.1, 0.3, 0.1, 0.9],
                                          [0.3, 0.1, 0.2, 0.8]]
            
            result = use_cases.use_case_content_classification()
            
            assert result.use_case == "content_classification"
            assert result.success is True
            assert "documents_classified" in result.performance_metrics
    
    def test_report_generation(self, temp_dir):
        """Test report generation."""
        use_cases = CoupaDownloadsUseCases()
        
        # Create mock results
        mock_results = [
            Mock(use_case="test_case", success=True, performance_metrics={"test": 1}),
            Mock(use_case="test_case_2", success=False, performance_metrics={})
        ]
        
        report = use_cases.generate_use_case_report(mock_results)
        
        assert "# EmbeddingGemma Use Cases for CoupaDownloads" in report
        assert "Total Use Cases: 2" in report
        assert "Successful Demonstrations: 1" in report
    
    def test_error_handling(self):
        """Test error handling in assessments."""
        assessment = EmbeddingGemmaCapabilityAssessment()
        
        # Test with no model
        assessment.model = None
        
        result = assessment._test_embedding_generation()
        assert result.success is False
        assert "Model not loaded" in result.error_message
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        config = get_config()
        
        # Test required attributes
        assert hasattr(config, 'model_name')
        assert hasattr(config, 'batch_size')
        assert hasattr(config, 'max_sequence_length')
        assert hasattr(config, 'enable_embedding_cache')
        
        # Test path creation
        assert os.path.exists(config.model_cache_dir)
        assert os.path.exists(config.cache_dir)
        assert os.path.exists(config.output_dir)


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    def test_memory_profiling_simulation(self):
        """Test memory profiling simulation."""
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Simulate some memory usage
        test_data = [f"test document {i}" for i in range(1000)]
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        assert memory_increase >= 0
        assert final_memory > initial_memory
    
    def test_processing_speed_simulation(self):
        """Test processing speed simulation."""
        start_time = time.time()
        
        # Simulate processing
        test_data = [f"test document {i}" for i in range(100)]
        processed = [doc.upper() for doc in test_data]
        
        duration = time.time() - start_time
        docs_per_second = len(test_data) / duration
        
        assert duration > 0
        assert docs_per_second > 0
        assert len(processed) == len(test_data)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
