"""
EmbeddingGemma Configuration - Isolated from Main MyScript Project
"""

import os
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class EmbeddingGemmaConfig:
    """Configuration for EmbeddingGemma integration."""
    
    # Model Configuration
    model_name: str = "google/embeddinggemma-300m"
    model_cache_dir: str = "data/model_cache"
    max_sequence_length: int = 512
    batch_size: int = 32
    
    # Performance Settings
    device: str = "auto"  # auto, cpu, cuda
    use_fp16: bool = False
    normalize_embeddings: bool = True
    
    # Caching Configuration
    enable_embedding_cache: bool = True
    cache_dir: str = "data/embeddings_cache"
    cache_expiry_hours: int = 24
    
    # Processing Settings
    max_workers: int = 4
    chunk_size: int = 1000
    timeout_seconds: int = 300
    
    # Output Settings
    output_dir: str = "reports"
    enable_logging: bool = True
    log_level: str = "INFO"
    
    # Integration Settings
    integration_mode: str = "isolated"  # isolated, hybrid, full
    fallback_enabled: bool = True
    
    def __post_init__(self):
        """Initialize paths and create directories."""
        # Convert relative paths to absolute
        base_dir = Path(__file__).parent
        self.model_cache_dir = str(base_dir / self.model_cache_dir)
        self.cache_dir = str(base_dir / self.cache_dir)
        self.output_dir = str(base_dir / self.output_dir)
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories."""
        directories = [
            self.model_cache_dir,
            self.cache_dir,
            self.output_dir,
            "data/sample_documents",
            "data/test_results"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model-specific configuration."""
        return {
            "model_name": self.model_name,
            "cache_folder": self.model_cache_dir,
            "device": self.device,
            "trust_remote_code": True
        }
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration."""
        return {
            "batch_size": self.batch_size,
            "max_sequence_length": self.max_sequence_length,
            "normalize_embeddings": self.normalize_embeddings,
            "show_progress_bar": True
        }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Get caching configuration."""
        return {
            "enabled": self.enable_embedding_cache,
            "cache_dir": self.cache_dir,
            "expiry_hours": self.cache_expiry_hours,
            "max_cache_size_mb": 1000
        }


@dataclass
class AssessmentConfig:
    """Configuration for feasibility assessment."""
    
    # Test Data
    sample_documents_count: int = 100
    test_batch_sizes: List[int] = None
    test_sequence_lengths: List[int] = None
    
    # Performance Testing
    performance_test_duration: int = 300  # seconds
    memory_profiling_enabled: bool = True
    cpu_profiling_enabled: bool = True
    
    # Benchmarking
    benchmark_iterations: int = 10
    warmup_iterations: int = 3
    
    # Reporting
    generate_detailed_reports: bool = True
    include_visualizations: bool = True
    save_embeddings: bool = False
    
    def __post_init__(self):
        if self.test_batch_sizes is None:
            self.test_batch_sizes = [1, 8, 16, 32, 64]
        if self.test_sequence_lengths is None:
            self.test_sequence_lengths = [128, 256, 512, 1024]


# Global configuration instances
embedding_config = EmbeddingGemmaConfig()
assessment_config = AssessmentConfig()


def get_config() -> EmbeddingGemmaConfig:
    """Get the global EmbeddingGemma configuration."""
    return embedding_config


def get_assessment_config() -> AssessmentConfig:
    """Get the global assessment configuration."""
    return assessment_config


def update_config(**kwargs) -> None:
    """Update configuration with new values."""
    global embedding_config
    for key, value in kwargs.items():
        if hasattr(embedding_config, key):
            setattr(embedding_config, key, value)


if __name__ == "__main__":
    # Test configuration
    config = get_config()
    print("EmbeddingGemma Configuration:")
    print(f"Model: {config.model_name}")
    print(f"Cache Dir: {config.cache_dir}")
    print(f"Output Dir: {config.output_dir}")
    print(f"Integration Mode: {config.integration_mode}")
    
    assessment = get_assessment_config()
    print("\nAssessment Configuration:")
    print(f"Sample Documents: {assessment.sample_documents_count}")
    print(f"Test Batch Sizes: {assessment.test_batch_sizes}")
    print(f"Performance Test Duration: {assessment.performance_test_duration}s")

