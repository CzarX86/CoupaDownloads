#!/usr/bin/env python3
"""
Demo Analysis Script
Demonstrates how to use the comprehensive analysis tools for Coupa file fetching.
"""

import os
import sys
import json
import tempfile
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def demo_po_sampling():
    """Demo PO sampling functionality."""
    print("🎯 PO Sampling Demo")
    print("=" * 50)
    
    try:
        from tests.po_sampler import POSampler
        
        # Create sampler
        sampler = POSampler()
        
        # Load and analyze data
        if sampler.load_po_data():
            analysis = sampler.analyze_po_distribution()
            
            print(f"✅ Loaded {analysis['total_pos']} POs from input.csv")
            
            # Show distribution
            print(f"\n📊 Status Distribution:")
            for status, count in analysis['status_distribution'].items():
                percentage = (count / analysis['total_pos']) * 100
                print(f"  {status}: {count} ({percentage:.1f}%)")
            
            # Select optimal sample
            selected_pos = sampler.select_optimal_sample()
            
            print(f"\n✅ Selected {len(selected_pos)} POs for analysis:")
            for i, po in enumerate(selected_pos, 1):
                print(f"  {i:2d}. {po}")
            
            return selected_pos
        else:
            print("❌ Failed to load PO data")
            return []
            
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return []

def demo_dom_analysis():
    """Demo DOM analysis functionality."""
    print("🧪 DOM Analysis Demo")
    print("=" * 50)
    
    try:
        from tests.test_dom_analysis import DOMAnalyzer
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options as EdgeOptions
        
        # Setup driver
        options = EdgeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Edge(options=options)
        driver.set_page_load_timeout(30)
        
        # Create analyzer
        analyzer = DOMAnalyzer(driver)
        
        # Analyze a test page
        test_url = "https://httpbin.org/html"
        print(f"Analyzing: {test_url}")
        
        analysis = analyzer.analyze_page_structure(test_url)
        
        print(f"✅ Analysis completed!")
        print(f"Page title: {analysis['page_title']}")
        print(f"Total elements: {analysis['elements_found']['total_elements']}")
        
        # Show attachment selectors
        attachment_selectors = analysis['attachment_selectors']['best_selectors']
        if attachment_selectors:
            print(f"Best attachment selector: {attachment_selectors[0]['selector']}")
        
        # Show recommendations
        print(f"\nRecommendations:")
        for i, rec in enumerate(analysis['recommendations'][:3], 1):
            print(f"  {i}. {rec}")
        
        driver.quit()
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Note: This demo requires Edge WebDriver to be installed")

def demo_file_download_analysis():
    """Demo file download analysis functionality."""
    print("\n🧪 File Download Analysis Demo")
    print("=" * 50)
    
    try:
        from tests.test_file_download_analysis import FileDownloadAnalyzer
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options as EdgeOptions
        
        # Setup driver
        options = EdgeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Set download preferences
        download_dir = tempfile.mkdtemp()
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
        }
        options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Edge(options=options)
        driver.set_page_load_timeout(30)
        
        # Create analyzer
        analyzer = FileDownloadAnalyzer(driver)
        analyzer.setup_download_monitoring(download_dir)
        
        # Analyze a test page
        test_url = "https://httpbin.org/forms/post"
        print(f"Analyzing: {test_url}")
        
        analysis = analyzer.analyze_download_mechanisms(test_url)
        
        print(f"✅ Analysis completed!")
        
        # Show download mechanisms
        mechanisms = analysis['download_mechanisms']
        print(f"Direct links: {len(mechanisms['direct_links'])}")
        print(f"Button clicks: {len(mechanisms['button_clicks'])}")
        print(f"Form submissions: {len(mechanisms['form_submissions'])}")
        
        # Show file artifacts
        artifacts = analysis['file_artifacts']
        print(f"File elements: {len(artifacts['file_elements'])}")
        print(f"Attachment containers: {len(artifacts['attachment_containers'])}")
        
        # Show recommendations
        print(f"\nRecommendations:")
        for i, rec in enumerate(analysis['recommendations'][:3], 1):
            print(f"  {i}. {rec}")
        
        driver.quit()
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Note: This demo requires Edge WebDriver to be installed")

def demo_comprehensive_analysis():
    """Demo comprehensive analysis functionality."""
    print("\n🧪 Comprehensive Analysis Demo")
    print("=" * 50)
    
    try:
        from tests.run_comprehensive_analysis import ComprehensiveAnalyzer
        
        # Create analyzer
        analyzer = ComprehensiveAnalyzer(headless=True, save_screenshots=False)
        
        # Run analysis on test pages
        print("Running comprehensive analysis on test pages...")
        
        test_pages = {
            'httpbin_html': 'https://httpbin.org/html',
            'httpbin_forms': 'https://httpbin.org/forms/post'
        }
        
        results = {}
        for page_name, url in test_pages.items():
            print(f"  Analyzing {page_name}...")
            analysis = analyzer.analyze_page_comprehensive(url, page_name)
            results[page_name] = analysis
        
        print(f"✅ Comprehensive analysis completed!")
        print(f"Pages analyzed: {len(results)}")
        
        # Show insights
        for page_name, analysis in results.items():
            if 'error' not in analysis:
                insights = analysis['combined_insights']
                print(f"\n{page_name}:")
                print(f"  Best download strategy: {insights['best_download_strategy']}")
                print(f"  File detection method: {insights['file_detection_method']}")
                print(f"  Implementation complexity: {insights['implementation_complexity']}")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Note: This demo requires Edge WebDriver to be installed")

def demo_coupa_specific_analysis():
    """Demo Coupa-specific analysis with sampled POs."""
    print("\n🧪 Coupa-Specific Analysis Demo")
    print("=" * 50)
    
    try:
        from tests.run_comprehensive_analysis import ComprehensiveAnalyzer
        
        # First, get sampled POs
        selected_pos = demo_po_sampling()
        
        if not selected_pos:
            print("❌ No POs selected for analysis")
            return
        
        # Create analyzer
        analyzer = ComprehensiveAnalyzer(headless=True, save_screenshots=False)
        
        # Analyze Coupa pages with sampled POs
        print(f"\n🔍 Analyzing {len(selected_pos)} sampled PO pages...")
        print("Note: This may fail without proper authentication")
        
        # Extract PO numbers (remove 'PO' prefix if present)
        po_numbers = []
        for po in selected_pos[:5]:  # Limit to first 5 for demo
            po_num = po.replace('PO', '') if po.startswith('PO') else po
            po_numbers.append(po_num)
        
        # Run comprehensive analysis
        try:
            report = analyzer.analyze_coupa_ecosystem(po_numbers)
            
            print(f"\n✅ Coupa analysis completed!")
            print(f"📊 Pages analyzed: {len(report['pages_analyzed'])}")
            
            # Show insights
            insights = report['ecosystem_insights']
            print(f"🔍 Authentication required: {insights['authentication_required']}")
            print(f"🔄 Consistent patterns: {len(insights['consistent_patterns'])}")
            
            # Show recommendations
            print(f"\n🎯 Top Recommendations:")
            for i, rec in enumerate(report['recommendations'][:5], 1):
                print(f"  {i}. {rec}")
                
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Note: This demo requires Edge WebDriver to be installed")

def generate_sample_report():
    """Generate a sample analysis report."""
    print("\n📄 Sample Analysis Report Generation")
    print("=" * 50)
    
    # Create sample report structure
    sample_report = {
        'timestamp': datetime.now().isoformat(),
        'analysis_type': 'comprehensive_coupa_analysis',
        'summary': {
            'total_pages_analyzed': 3,
            'success_rate': '66.67%',
            'top_attachment_selector': 'span[aria-label*="file attachment"]',
            'top_supplier_selector': 'span[class*="supplier-name"]',
            'key_findings': [
                '✅ High success rate in page analysis',
                '📎 Found effective attachment selector',
                '🏢 Found effective supplier selector'
            ],
            'next_steps': [
                'Implement the recommended selectors in the downloader',
                'Add comprehensive error handling for failed page loads',
                'Test the selectors with real Coupa credentials'
            ]
        },
        'best_practices': {
            'attachment_selectors': [
                {
                    'selector': 'span[aria-label*="file attachment"]',
                    'success_rate': 0.85,
                    'recommendation': 'Use aria-label attributes for attachment detection'
                }
            ],
            'supplier_selectors': [
                {
                    'selector': 'span[class*="supplier-name"]',
                    'success_rate': 0.72,
                    'recommendation': 'Use CSS class selectors for supplier detection'
                }
            ]
        },
        'recommendations': [
            '🎯 Use span[aria-label*="file attachment"] for attachment detection',
            '🏢 Use span[class*="supplier-name"] for supplier detection',
            '⚡ Use CSS selectors instead of XPath for better performance',
            '🔄 Implement retry logic for failed page loads',
            '📱 Test on different screen sizes to ensure selector robustness'
        ],
        'implementation_strategy': {
            'phase_1': [
                'Implement authentication handling',
                'Set up basic page navigation',
                'Implement consistent selector usage'
            ],
            'phase_2': [
                'Implement download mechanism detection',
                'Add file artifact analysis',
                'Implement supplier detection'
            ],
            'phase_3': [
                'Optimize selector performance',
                'Implement retry mechanisms',
                'Add comprehensive logging'
            ]
        }
    }
    
    # Save sample report
    report_file = os.path.join(tempfile.gettempdir(), 'sample_coupa_analysis_report.json')
    with open(report_file, 'w') as f:
        json.dump(sample_report, f, indent=2)
    
    print(f"✅ Sample report generated: {report_file}")
    print(f"📊 Report contains:")
    print(f"  - Analysis summary")
    print(f"  - Best practices")
    print(f"  - Recommendations")
    print(f"  - Implementation strategy")
    
    return report_file

def main():
    """Main demo function."""
    print("🚀 Coupa Downloads Analysis Demo")
    print("=" * 60)
    print("This demo shows how to analyze Coupa pages to determine")
    print("the best approach for fetching files.")
    print("=" * 60)
    
    # Run demos
    demo_po_sampling()
    demo_dom_analysis()
    demo_file_download_analysis()
    demo_comprehensive_analysis()
    demo_coupa_specific_analysis()
    
    # Generate sample report
    sample_report = generate_sample_report()
    
    print("\n" + "=" * 60)
    print("✅ Demo completed!")
    print("=" * 60)
    print("To run actual analysis with your Coupa credentials:")
    print("1. Ensure Edge WebDriver is installed")
    print("2. Run: python tests/run_comprehensive_analysis.py")
    print("3. Check the generated report for recommendations")
    print("=" * 60)

if __name__ == "__main__":
    main() 