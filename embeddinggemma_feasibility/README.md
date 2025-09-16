# EmbeddingGemma Feasibility Assessment

## Overview

This subproject provides a comprehensive feasibility and capability assessment for integrating Google's EmbeddingGemma model into the MyScript CoupaDownloads system.

## Project Structure

```
src/MyScript/embeddinggemma_feasibility/
├── README.md                           # This file
├── requirements.txt                    # Isolated dependencies
├── config.py                          # Configuration for EmbeddingGemma
├── capability_assessment.py           # Main assessment framework
├── integration_tests.py               # Integration tests
├── performance_benchmarks.py          # Performance testing
├── use_case_examples.py               # Practical use cases
├── data/                              # Test data and samples
│   ├── sample_documents/              # Sample documents for testing
│   ├── embeddings_cache/              # Cached embeddings
│   └── test_results/                  # Test results and reports
└── reports/                           # Generated assessment reports
    ├── feasibility_report.md          # Main feasibility report
    ├── performance_analysis.md        # Performance analysis
    └── integration_recommendations.md # Integration recommendations
```

## Key Assessment Areas

### 1. Technical Feasibility

- **Model Loading**: Test EmbeddingGemma model loading and initialization
- **Memory Usage**: Assess RAM requirements (<200MB target)
- **Performance**: Measure embedding generation speed
- **Compatibility**: Test with existing Python dependencies

### 2. Use Case Analysis

- **Document Similarity**: Compare Coupa documents for duplicates
- **Semantic Search**: Enhanced search capabilities for PO data
- **Content Classification**: Automatic categorization of attachments
- **RAG Integration**: Retrieval Augmented Generation for document Q&A

### 3. Integration Assessment

- **Isolation**: Ensure no impact on main MyScript project
- **API Design**: Design clean interfaces for embedding operations
- **Error Handling**: Robust error handling and fallbacks
- **Configuration**: Flexible configuration management

### 4. Performance Benchmarks

- **Speed Tests**: Embedding generation time per document
- **Memory Profiling**: RAM usage patterns
- **Batch Processing**: Efficiency with multiple documents
- **Caching**: Embedding caching strategies

## Quick Start

1. Install (Poetry with ML/RAG extras):

   ```bash
   poetry install --with ml
   ```

2. Run the interactive RAG CLI:

   ```bash
   poetry run rag-cli
   # or
   poetry run python -m embeddinggemma_feasibility.interactive_cli
   ```

3. Legacy direct usage (pip-only):

   ```bash
   pip install -r embeddinggemma_feasibility/requirements.txt
   python -m embeddinggemma_feasibility.interactive_cli
   ```

4. Assessment utilities:

   ```bash
   poetry run python embeddinggemma_feasibility/capability_assessment.py
   poetry run python embeddinggemma_feasibility/integration_tests.py
   poetry run python embeddinggemma_feasibility/performance_benchmarks.py --generate-report
   ```

## Expected Outcomes

- **Feasibility Score**: Quantitative assessment of integration viability
- **Performance Metrics**: Detailed performance characteristics
- **Integration Plan**: Step-by-step integration roadmap
- **Risk Assessment**: Identified risks and mitigation strategies
- **Resource Requirements**: Hardware and software requirements

## Safety Measures

- **Complete Isolation**: No modifications to main MyScript codebase
- **Virtual Environment**: Optional isolated Python environment
- **Rollback Plan**: Easy removal if integration proves unfeasible
- **Testing Only**: No production impact during assessment

## Next Steps

After completing the assessment:

1. Review generated reports in `reports/` directory
2. Evaluate feasibility score and recommendations
3. Decide on integration approach or alternative solutions
4. Clean up assessment files if not proceeding with integration

## HITL Feedback (Review → Ingest → Evaluate → Train)

This repository includes a lightweight Human-in-the-Loop feedback loop to improve extraction quality without changing defaults:

- Prepare a review CSV with triplets per field:

  ```bash
  python tools/feedback_cli.py prepare \
    --pred-csv reports/advanced_coupa_fields_extraction_*.csv \
    --out reports/feedback/review.csv \
    --fields contract_name,contract_type,sow_value_eur,pwo_number,managed_by \
    --sample 30
  ```

- Ingest, build datasets and analysis:

  ```bash
  python tools/feedback_cli.py ingest --review-csv reports/feedback/review.csv --out-dir datasets/
  ```

- Evaluate metrics:

  ```bash
  python tools/feedback_cli.py eval --review-csv reports/feedback/review.csv --report-dir reports/feedback/
  ```

- Optional: fine-tune Sentence Transformers from pairs:

  ```bash
  python tools/feedback_cli.py train-st --dataset datasets/st_pairs.jsonl --output embeddinggemma_feasibility/models/st_custom_v1
  ```

See also: `docs/HITL_FEEDBACK_WORKFLOW.md`.
