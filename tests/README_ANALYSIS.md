# Coupa Downloads Analysis Tools

This directory contains comprehensive analysis tools designed to analyze Coupa pages and determine the best approach for fetching files. These tools download the DOM, analyze page structure, and provide data-driven recommendations for file downloading strategies.

## Overview

The analysis tools consist of four main components:

1. **PO Sampling** (`po_sampler.py`) - Intelligently samples PO numbers for analysis
2. **DOM Analysis** (`test_dom_analysis.py`) - Analyzes page structure and element selectors
3. **File Download Analysis** (`test_file_download_analysis.py`) - Analyzes download mechanisms and file artifacts
4. **Comprehensive Analysis** (`run_comprehensive_analysis.py`) - Combines all analyses for complete insights

## Quick Start

### 1. Run the Demo

To see the tools in action without requiring Coupa credentials:

```bash
cd CoupaDownloads/tests
python demo_analysis.py
```

This will demonstrate the analysis capabilities using public test pages.

### 2. PO Sampling Demo

To see how the system intelligently samples PO numbers:

```bash
cd CoupaDownloads/tests
python po_sampler.py
```

This will analyze your `input.csv` file and show the optimal sampling strategy.

### 3. Run Comprehensive Analysis

To analyze actual Coupa pages with smart PO sampling:

```bash
cd CoupaDownloads/tests
# Let the system automatically select optimal PO sample
python run_comprehensive_analysis.py

# Or specify specific PO numbers
python run_comprehensive_analysis.py --po-numbers 15826591 15873456
```

### 4. Run Individual Analysis

To run specific analysis types:

```bash
# PO sampling tests
python -m pytest test_po_sampling.py -v

# DOM analysis only
python -m pytest test_dom_analysis.py -v

# File download analysis only
python -m pytest test_file_download_analysis.py -v
```

## Analysis Tools

### PO Sampler (`po_sampler.py`)

The PO Sampler intelligently selects PO numbers for analysis using statistical sampling principles.

**Key Features:**
- Analyzes PO distribution in input.csv
- Calculates optimal sample size using statistical formulas
- Performs stratified sampling by status
- Provides detailed sampling reports
- Exports selected samples to CSV

**Usage:**
```python
from tests.po_sampler import POSampler

sampler = POSampler()
sampler.load_po_data()
selected_pos = sampler.select_optimal_sample()
sampler.print_sampling_report(selected_pos)
```

### DOM Analyzer (`test_dom_analysis.py`)

The DOM Analyzer examines page structure and identifies the best selectors for finding elements.

**Key Features:**
- Analyzes page elements and structure
- Tests multiple selector strategies
- Identifies best attachment and supplier selectors
- Provides performance recommendations

**Usage:**
```python
from tests.test_dom_analysis import DOMAnalyzer

analyzer = DOMAnalyzer(driver)
analysis = analyzer.analyze_page_structure(url)
```

### File Download Analyzer (`test_file_download_analysis.py`)

The File Download Analyzer examines download mechanisms and file artifacts on pages.

**Key Features:**
- Identifies download mechanisms (direct links, button clicks, forms)
- Analyzes file artifacts and metadata
- Tests actual download interactions
- Monitors download directory for new files

**Usage:**
```python
from tests.test_file_download_analysis import FileDownloadAnalyzer

analyzer = FileDownloadAnalyzer(driver)
analyzer.setup_download_monitoring(download_dir)
analysis = analyzer.analyze_download_mechanisms(url)
```

### Comprehensive Analyzer (`run_comprehensive_analysis.py`)

The Comprehensive Analyzer combines DOM and download analysis for complete insights.

**Key Features:**
- Combines multiple analysis types
- Generates implementation strategies
- Provides ecosystem-wide insights
- Creates detailed reports

**Usage:**
```python
from tests.run_comprehensive_analysis import ComprehensiveAnalyzer

analyzer = ComprehensiveAnalyzer(headless=True)
report = analyzer.analyze_coupa_ecosystem(po_numbers)
```

## Analysis Output

### Sample Report Structure

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "summary": {
    "total_pages_analyzed": 5,
    "success_rate": "80.00%",
    "top_attachment_selector": "span[aria-label*='file attachment']",
    "top_supplier_selector": "span[class*='supplier-name']"
  },
  "best_practices": {
    "attachment_selectors": [
      {
        "selector": "span[aria-label*='file attachment']",
        "success_rate": 0.85,
        "recommendation": "Use aria-label attributes for attachment detection"
      }
    ]
  },
  "recommendations": [
    "🎯 Use span[aria-label*='file attachment'] for attachment detection",
    "⚡ Use CSS selectors instead of XPath for better performance",
    "🔄 Implement retry logic for failed page loads"
  ],
  "implementation_strategy": {
    "phase_1": ["Implement authentication handling", "Set up basic navigation"],
    "phase_2": ["Implement download detection", "Add file analysis"],
    "phase_3": ["Optimize performance", "Add comprehensive logging"]
  }
}
```

## Key Insights

### Download Strategy Recommendations

The analysis tools identify the best download strategy based on page structure:

1. **Direct Links** - When `href` attributes point directly to files
2. **Button Clicks** - When download buttons trigger file downloads
3. **Form Submissions** - When forms handle file downloads
4. **JavaScript Execution** - When complex JavaScript is required

### Selector Recommendations

The tools test multiple selector strategies and recommend the most effective:

- **CSS Selectors** - Preferred for performance and readability
- **XPath** - Fallback for complex element selection
- **Aria Labels** - Best for accessibility and reliability
- **Data Attributes** - Most robust for dynamic content

### Implementation Complexity

The analysis provides complexity assessments:

- **Low** - Straightforward implementation
- **Medium** - Requires proper error handling
- **High** - Complex implementation with multiple phases

## Command Line Options

### Comprehensive Analysis

```bash
python run_comprehensive_analysis.py [OPTIONS]

Options:
  --headless              Run browser in headless mode (default: True)
  --screenshots           Save screenshots of analyzed pages
  --po-numbers PO_NUMBERS Specific PO numbers to analyze
  --output-dir OUTPUT_DIR Directory to save analysis report
```

### Examples

```bash
# Analyze specific PO numbers
python run_comprehensive_analysis.py --po-numbers 15826591 15873456

# Save screenshots and specify output directory
python run_comprehensive_analysis.py --screenshots --output-dir ./reports

# Run with visible browser (for debugging)
python run_comprehensive_analysis.py --headless=false
```

## Integration with Existing Code

### Using Analysis Results

The analysis results can be integrated into the existing downloader:

```python
# Example: Update config with best selectors
from tests.run_comprehensive_analysis import ComprehensiveAnalyzer

analyzer = ComprehensiveAnalyzer()
report = analyzer.analyze_coupa_ecosystem(['15826591'])

# Extract best selectors
best_attachment_selector = report['best_practices']['attachment_selectors'][0]['selector']
best_supplier_selector = report['best_practices']['supplier_selectors'][0]['selector']

# Update config
config.ATTACHMENT_SELECTOR = best_attachment_selector
config.SUPPLIER_NAME_CSS_SELECTORS = [best_supplier_selector]
```

### Automated Analysis

Run analysis as part of your development workflow:

```python
# In your main script
def update_selectors_from_analysis():
    """Update selectors based on latest analysis."""
    analyzer = ComprehensiveAnalyzer()
    report = analyzer.analyze_coupa_ecosystem()
    
    # Update configuration with best practices
    update_config_from_report(report)
    
    return report
```

## Troubleshooting

### Common Issues

1. **WebDriver Not Found**
   ```
   Error: Edge WebDriver not available
   Solution: Install Edge WebDriver and ensure it's in PATH
   ```

2. **Authentication Required**
   ```
   Error: Many Coupa pages failed to load
   Solution: Ensure you're logged into Coupa in Edge browser
   ```

3. **Page Load Timeouts**
   ```
   Error: Page load timeout
   Solution: Increase timeout or check network connectivity
   ```

### Debug Mode

Run with visible browser for debugging:

```bash
python run_comprehensive_analysis.py --headless=false
```

### Save Screenshots

Save screenshots for visual analysis:

```bash
python run_comprehensive_analysis.py --screenshots
```

## Best Practices

### Running Analysis

1. **Use Real Credentials** - Analysis is most accurate with authenticated sessions
2. **Test Multiple POs** - Different POs may have different structures
3. **Monitor Performance** - Large pages may take time to analyze
4. **Review Screenshots** - Visual verification helps validate results

### Interpreting Results

1. **Success Rate** - Higher is better, but consider authentication requirements
2. **Selector Consistency** - Consistent selectors across pages are more reliable
3. **Implementation Complexity** - Start with low complexity strategies
4. **Performance Impact** - Consider selector performance for large datasets

### Updating Selectors

1. **Test Incrementally** - Update one selector at a time
2. **Monitor Results** - Track success rates after updates
3. **Fallback Strategies** - Always have backup selectors
4. **Document Changes** - Keep track of selector updates

## Future Enhancements

### Planned Features

1. **Machine Learning** - Automatically optimize selectors based on success rates
2. **Real-time Monitoring** - Continuously monitor selector effectiveness
3. **A/B Testing** - Test different selector strategies
4. **Performance Profiling** - Detailed performance analysis of selectors

### Contributing

To contribute to the analysis tools:

1. Add new selector strategies to the analyzers
2. Improve error handling and reporting
3. Add support for new file types
4. Enhance performance monitoring

## Support

For issues or questions about the analysis tools:

1. Check the troubleshooting section
2. Review the demo output for examples
3. Examine the generated reports for insights
4. Run with debug mode for detailed error information

---

**Note**: These analysis tools are designed to help determine the best approach for fetching files from Coupa pages. They provide data-driven recommendations but should be used in conjunction with manual testing and validation. 