# EmbeddingGemma Feasibility Assessment - Quick Start Guide

## 🚀 Quick Start

This subproject provides a comprehensive feasibility assessment for integrating Google's EmbeddingGemma model into your MyScript CoupaDownloads system. The assessment is completely isolated and will not affect your main project.

### Prerequisites

- Python 3.12+ (compatible with your MyScript project)
- Internet connection for downloading the EmbeddingGemma model
- At least 2GB RAM available for testing

### Installation

1. **Navigate to the assessment directory**:

   ```bash
   cd src/MyScript/embeddinggemma_feasibility
   ```

2. **Install dependencies** (isolated from main project):

   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python config.py
   ```

### Running the Assessment

#### Option 1: Complete Assessment (Recommended)

```bash
python capability_assessment.py
```

This will run all capability tests and generate a comprehensive report.

#### Option 2: Use Case Demonstrations

```bash
python use_case_examples.py
```

This will demonstrate practical use cases for EmbeddingGemma in CoupaDownloads.

#### Option 3: Performance Benchmarks

```bash
python performance_benchmarks.py
```

This will run detailed performance tests and memory profiling.

#### Option 4: Integration Tests

```bash
python integration_tests.py
```

#### Option 5: PDF Information Extraction

```bash
python extract_pdf_info.py
```

This will extract information from PDFs in the P2 folder using EmbeddingGemma.

#### Option 6: Coupa Specific Fields Extraction

```bash
python extract_coupa_fields.py
```

This will extract the 22 specific Coupa fields from PDFs and generate a CSV file.

#### Option 7: Advanced NLP Fields Extraction

```bash
python extract_advanced_coupa_fields.py
```

This uses multiple NLP libraries (spaCy, BERT, Sentence Transformers, LangChain, Ollama) for advanced field extraction.

### Understanding the Results

#### Feasibility Score

- **0.8-1.0**: High feasibility - Proceed with integration
- **0.6-0.8**: Moderate feasibility - Proceed with caution
- **0.0-0.6**: Low feasibility - Consider alternatives

#### Key Metrics

- **Memory Usage**: Target <200MB (EmbeddingGemma's claim)
- **Embedding Speed**: Documents per second
- **Batch Efficiency**: How well batch processing scales
- **Error Rate**: System stability

### Sample Output

```
🔍 Starting EmbeddingGemma Capability Assessment...

📦 Testing Model Loading...
✅ Model loaded successfully in 2.3s

💾 Testing Memory Usage...
✅ Memory usage: 156MB (within target)

⚡ Testing Embedding Generation...
✅ Speed: 45 docs/sec

📋 Assessment Summary:
Overall Feasibility: True
Feasibility Score: 0.85

💡 Recommendations:
  ✅ High feasibility - Proceed with integration
  💡 Consider implementing caching for better performance
  🔧 Design clean API interfaces for embedding operations
```

### Use Cases Demonstrated

1. **Duplicate Detection**: Find similar purchase orders
2. **Semantic Search**: Natural language search for POs
3. **Content Classification**: Automatic categorization
4. **Vendor Similarity**: Optimize vendor selection
5. **Attachment Analysis**: Process document content
6. **RAG System**: Question-answering over documents

### Files Generated

- `reports/capability_assessment_*.json` - Detailed assessment results
- `reports/use_cases_report_*.md` - Use case analysis
- `reports/performance_benchmark_*.json` - Performance metrics
- `data/embeddings_cache/` - Cached embeddings (if enabled)

### Safety Features

- **Complete Isolation**: No modifications to main MyScript codebase
- **No Production Impact**: All testing is local and isolated
- **Easy Cleanup**: Simply delete the `embeddinggemma_feasibility` folder
- **Rollback Safe**: No changes to existing functionality

### Troubleshooting

#### Common Issues

1. **"ML libraries not available"**

   ```bash
   pip install sentence-transformers torch numpy scikit-learn
   ```

2. **"Model loading failed"**

   - Check internet connection
   - Verify sufficient disk space (~1GB for model)
   - Try running with `--offline` flag if model is cached

3. **"Memory usage exceeds target"**
   - Close other applications
   - Try reducing batch sizes in config
   - Consider using CPU instead of GPU

#### Getting Help

- Check the generated reports in `reports/` directory
- Review error messages in the console output
- Examine the detailed JSON results for specific metrics

### Next Steps

After running the assessment:

1. **Review the feasibility score** and recommendations
2. **Examine the use case demonstrations** to see practical applications
3. **Check performance metrics** against your requirements
4. **Decide on integration approach** based on results

### Cleanup

If you decide not to proceed with integration:

```bash
# Remove the entire assessment directory
rm -rf src/MyScript/embeddinggemma_feasibility

# Or just remove generated files
rm -rf src/MyScript/embeddinggemma_feasibility/reports/*
rm -rf src/MyScript/embeddinggemma_feasibility/data/*
```

### Integration Decision Matrix

| Feasibility Score | Memory Usage | Speed        | Recommendation               |
| ----------------- | ------------ | ------------ | ---------------------------- |
| >0.8              | <200MB       | >20 docs/sec | ✅ Proceed with integration  |
| 0.6-0.8           | <300MB       | >10 docs/sec | ⚠️ Proceed with optimization |
| <0.6              | >300MB       | <10 docs/sec | ❌ Consider alternatives     |

---

**Note**: This assessment is designed to be completely safe and isolated. It will not affect your main MyScript project in any way.
