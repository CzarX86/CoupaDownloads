#!/usr/bin/env python3
"""
DOM Analysis Test Runner
Executes comprehensive DOM analysis tests and generates recommendations for Coupa file fetching.
"""

import os
import sys
import json
import time
import tempfile
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_dom_analysis import DOMAnalyzer
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions


class DOMAnalysisRunner:
    """
    Runner for DOM analysis tests with comprehensive reporting.
    """
    
    def __init__(self, headless: bool = True, save_screenshots: bool = False):
        self.headless = headless
        self.save_screenshots = save_screenshots
        self.results = {}
        self.driver = None
        self.analyzer = None
    
    def setup_driver(self) -> bool:
        """Setup Edge WebDriver for analysis."""
        try:
            options = EdgeOptions()
            
            if self.headless:
                options.add_argument('--headless')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            # Set download preferences
            download_dir = tempfile.mkdtemp()
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
            }
            options.add_experimental_option("prefs", prefs)
            
            # Try to use existing profile for authentication
            edge_profile_dir = os.path.expanduser("~/Library/Application Support/Microsoft Edge")
            if os.path.exists(edge_profile_dir):
                options.add_argument(f"--user-data-dir={edge_profile_dir}")
                options.add_argument("--profile-directory=Default")
            
            self.driver = webdriver.Edge(options=options)
            self.driver.set_page_load_timeout(30)
            self.analyzer = DOMAnalyzer(self.driver)
            
            print("✅ Edge WebDriver setup successful")
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup Edge WebDriver: {e}")
            return False
    
    def analyze_test_pages(self) -> Dict[str, Any]:
        """Analyze various test pages to understand DOM patterns."""
        test_pages = {
            'httpbin_html': 'https://httpbin.org/html',
            'httpbin_forms': 'https://httpbin.org/forms/post',
            'httpbin_json': 'https://httpbin.org/json',
            'example_com': 'https://example.com'
        }
        
        results = {}
        
        for name, url in test_pages.items():
            print(f"\n🔍 Analyzing test page: {name}")
            try:
                analysis = self.analyzer.analyze_page_structure(url)
                results[name] = analysis
                
                if self.save_screenshots:
                    screenshot_path = f"test_page_{name}.png"
                    self.driver.save_screenshot(screenshot_path)
                    print(f"📸 Screenshot saved: {screenshot_path}")
                    
            except Exception as e:
                print(f"❌ Error analyzing {name}: {e}")
                results[name] = {'error': str(e)}
        
        return results
    
    def analyze_coupa_pages(self, po_numbers: List[str] = None) -> Dict[str, Any]:
        """Analyze actual Coupa pages."""
        if po_numbers is None:
            po_numbers = ['15826591', '15873456', '15873457']  # Sample PO numbers
        
        coupa_pages = {
            'login': 'https://unilever.coupahost.com/login',
            'dashboard': 'https://unilever.coupahost.com/dashboard'
        }
        
        # Add PO pages
        for po in po_numbers:
            coupa_pages[f'po_{po}'] = f'https://unilever.coupahost.com/order_headers/{po}'
        
        results = {}
        
        for name, url in coupa_pages.items():
            print(f"\n🔍 Analyzing Coupa page: {name}")
            try:
                analysis = self.analyzer.analyze_page_structure(url)
                results[name] = analysis
                
                if self.save_screenshots:
                    screenshot_path = f"coupa_page_{name}.png"
                    self.driver.save_screenshot(screenshot_path)
                    print(f"📸 Screenshot saved: {screenshot_path}")
                    
            except Exception as e:
                print(f"❌ Error analyzing {name}: {e}")
                results[name] = {'error': str(e)}
        
        return results
    
    def generate_comprehensive_report(self, test_results: Dict[str, Any], 
                                    coupa_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {},
            'best_practices': {},
            'recommendations': [],
            'selector_analysis': {},
            'performance_metrics': {},
            'detailed_results': {
                'test_pages': test_results,
                'coupa_pages': coupa_results
            }
        }
        
        # Analyze selector effectiveness
        selector_analysis = self._analyze_selector_effectiveness(test_results, coupa_results)
        report['selector_analysis'] = selector_analysis
        
        # Generate best practices
        report['best_practices'] = self._generate_best_practices(selector_analysis)
        
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(selector_analysis, coupa_results)
        
        # Calculate performance metrics
        report['performance_metrics'] = self._calculate_performance_metrics(test_results, coupa_results)
        
        # Generate summary
        report['summary'] = self._generate_summary(report)
        
        return report
    
    def _analyze_selector_effectiveness(self, test_results: Dict[str, Any], 
                                      coupa_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the effectiveness of different selectors."""
        selector_stats = {
            'attachment_selectors': {},
            'supplier_selectors': {},
            'overall_effectiveness': {}
        }
        
        # Collect all attachment selector data
        attachment_data = []
        supplier_data = []
        
        for results in [test_results, coupa_results]:
            for page_name, analysis in results.items():
                if 'attachment_selectors' in analysis:
                    attachment_data.append(analysis['attachment_selectors'])
                if 'supplier_selectors' in analysis:
                    supplier_data.append(analysis['supplier_selectors'])
        
        # Analyze attachment selectors
        attachment_stats = {}
        for data in attachment_data:
            for selector, info in data.get('current_selectors', {}).items():
                if selector not in attachment_stats:
                    attachment_stats[selector] = {'count': 0, 'success_rate': 0, 'pages_tested': 0}
                
                if isinstance(info, dict) and 'count' in info:
                    attachment_stats[selector]['count'] += info['count']
                    attachment_stats[selector]['pages_tested'] += 1
        
        # Calculate success rates
        for selector, stats in attachment_stats.items():
            if stats['pages_tested'] > 0:
                stats['success_rate'] = stats['count'] / stats['pages_tested']
        
        selector_stats['attachment_selectors'] = attachment_stats
        
        # Analyze supplier selectors (similar logic)
        supplier_stats = {}
        for data in supplier_data:
            for selector, info in data.get('current_selectors', {}).items():
                if selector not in supplier_stats:
                    supplier_stats[selector] = {'count': 0, 'success_rate': 0, 'pages_tested': 0}
                
                if isinstance(info, dict) and 'count' in info:
                    supplier_stats[selector]['count'] += info['count']
                    supplier_stats[selector]['pages_tested'] += 1
        
        for selector, stats in supplier_stats.items():
            if stats['pages_tested'] > 0:
                stats['success_rate'] = stats['count'] / stats['pages_tested']
        
        selector_stats['supplier_selectors'] = supplier_stats
        
        return selector_stats
    
    def _generate_best_practices(self, selector_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate best practices based on analysis."""
        best_practices = {
            'attachment_selectors': [],
            'supplier_selectors': [],
            'general_guidelines': []
        }
        
        # Attachment selector best practices
        attachment_stats = selector_analysis['attachment_selectors']
        if attachment_stats:
            # Sort by success rate
            sorted_attachments = sorted(attachment_stats.items(), 
                                      key=lambda x: x[1]['success_rate'], reverse=True)
            
            for selector, stats in sorted_attachments[:3]:
                best_practices['attachment_selectors'].append({
                    'selector': selector,
                    'success_rate': stats['success_rate'],
                    'total_found': stats['count'],
                    'recommendation': f"Use '{selector}' for attachment detection (success rate: {stats['success_rate']:.2%})"
                })
        
        # Supplier selector best practices
        supplier_stats = selector_analysis['supplier_selectors']
        if supplier_stats:
            sorted_suppliers = sorted(supplier_stats.items(), 
                                    key=lambda x: x[1]['success_rate'], reverse=True)
            
            for selector, stats in sorted_suppliers[:3]:
                best_practices['supplier_selectors'].append({
                    'selector': selector,
                    'success_rate': stats['success_rate'],
                    'total_found': stats['count'],
                    'recommendation': f"Use '{selector}' for supplier detection (success rate: {stats['success_rate']:.2%})"
                })
        
        # General guidelines
        best_practices['general_guidelines'] = [
            "Always use aria-label attributes when available for accessibility",
            "Prefer CSS selectors over XPath for better performance",
            "Use data-testid attributes when available for robust selection",
            "Implement fallback selectors for critical elements",
            "Test selectors on multiple pages to ensure consistency",
            "Consider page loading states when designing selectors",
            "Use semantic HTML elements when possible"
        ]
        
        return best_practices
    
    def _generate_recommendations(self, selector_analysis: Dict[str, Any], 
                                coupa_results: Dict[str, Any]) -> List[str]:
        """Generate specific recommendations for Coupa file fetching."""
        recommendations = []
        
        # Analyze Coupa-specific patterns
        coupa_success_count = 0
        coupa_error_count = 0
        
        for page_name, analysis in coupa_results.items():
            if 'error' in analysis:
                coupa_error_count += 1
            else:
                coupa_success_count += 1
        
        if coupa_error_count > coupa_success_count:
            recommendations.append("⚠️ Many Coupa pages failed to load - check authentication and network connectivity")
        
        # Attachment selector recommendations
        attachment_stats = selector_analysis['attachment_selectors']
        if attachment_stats:
            best_attachment = max(attachment_stats.items(), key=lambda x: x[1]['success_rate'])
            recommendations.append(f"🎯 Best attachment selector: {best_attachment[0]} (success rate: {best_attachment[1]['success_rate']:.2%})")
        
        # Supplier selector recommendations
        supplier_stats = selector_analysis['supplier_selectors']
        if supplier_stats:
            best_supplier = max(supplier_stats.items(), key=lambda x: x[1]['success_rate'])
            recommendations.append(f"🏢 Best supplier selector: {best_supplier[0]} (success rate: {best_supplier[1]['success_rate']:.2%})")
        
        # Performance recommendations
        recommendations.extend([
            "⚡ Use CSS selectors instead of XPath for better performance",
            "🔄 Implement retry logic for failed page loads",
            "📱 Test on different screen sizes to ensure selector robustness",
            "🔍 Add logging for selector failures to improve debugging",
            "⏱️ Implement appropriate wait times for dynamic content"
        ])
        
        return recommendations
    
    def _calculate_performance_metrics(self, test_results: Dict[str, Any], 
                                     coupa_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance metrics from analysis."""
        metrics = {
            'total_pages_analyzed': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'average_elements_per_page': 0,
            'selector_success_rates': {}
        }
        
        all_results = {**test_results, **coupa_results}
        total_elements = 0
        
        for page_name, analysis in all_results.items():
            metrics['total_pages_analyzed'] += 1
            
            if 'error' in analysis:
                metrics['failed_analyses'] += 1
            else:
                metrics['successful_analyses'] += 1
                if 'elements_found' in analysis:
                    total_elements += analysis['elements_found'].get('total_elements', 0)
        
        if metrics['successful_analyses'] > 0:
            metrics['average_elements_per_page'] = total_elements / metrics['successful_analyses']
        
        metrics['success_rate'] = metrics['successful_analyses'] / metrics['total_pages_analyzed'] if metrics['total_pages_analyzed'] > 0 else 0
        
        return metrics
    
    def _generate_summary(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary of the analysis."""
        summary = {
            'analysis_date': report['timestamp'],
            'total_pages_analyzed': report['performance_metrics']['total_pages_analyzed'],
            'success_rate': f"{report['performance_metrics']['success_rate']:.2%}",
            'top_attachment_selector': None,
            'top_supplier_selector': None,
            'key_findings': [],
            'next_steps': []
        }
        
        # Get top selectors
        attachment_practices = report['best_practices']['attachment_selectors']
        if attachment_practices:
            summary['top_attachment_selector'] = attachment_practices[0]['selector']
        
        supplier_practices = report['best_practices']['supplier_selectors']
        if supplier_practices:
            summary['top_supplier_selector'] = supplier_practices[0]['selector']
        
        # Key findings
        if report['performance_metrics']['success_rate'] > 0.8:
            summary['key_findings'].append("✅ High success rate in page analysis")
        else:
            summary['key_findings'].append("⚠️ Low success rate - may need authentication or different approach")
        
        if summary['top_attachment_selector']:
            summary['key_findings'].append(f"📎 Found effective attachment selector: {summary['top_attachment_selector']}")
        
        if summary['top_supplier_selector']:
            summary['key_findings'].append(f"🏢 Found effective supplier selector: {summary['top_supplier_selector']}")
        
        # Next steps
        summary['next_steps'] = [
            "Implement the recommended selectors in the downloader",
            "Add comprehensive error handling for failed page loads",
            "Test the selectors with real Coupa credentials",
            "Monitor selector effectiveness over time",
            "Consider implementing selector fallback strategies"
        ]
        
        return summary
    
    def save_report(self, report: Dict[str, Any], output_dir: str = None) -> str:
        """Save the analysis report to file."""
        if output_dir is None:
            output_dir = tempfile.gettempdir()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"dom_analysis_report_{timestamp}.json")
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Report saved to: {report_file}")
        return report_file
    
    def print_summary(self, report: Dict[str, Any]):
        """Print a human-readable summary of the analysis."""
        summary = report['summary']
        
        print("\n" + "="*80)
        print("📊 DOM ANALYSIS SUMMARY REPORT")
        print("="*80)
        
        print(f"📅 Analysis Date: {summary['analysis_date']}")
        print(f"📋 Total Pages Analyzed: {summary['total_pages_analyzed']}")
        print(f"✅ Success Rate: {summary['success_rate']}")
        
        if summary['top_attachment_selector']:
            print(f"📎 Top Attachment Selector: {summary['top_attachment_selector']}")
        
        if summary['top_supplier_selector']:
            print(f"🏢 Top Supplier Selector: {summary['top_supplier_selector']}")
        
        print(f"\n🔍 Key Findings:")
        for finding in summary['key_findings']:
            print(f"  {finding}")
        
        print(f"\n🎯 Recommendations:")
        for i, rec in enumerate(report['recommendations'][:5], 1):
            print(f"  {i}. {rec}")
        
        print(f"\n📋 Next Steps:")
        for i, step in enumerate(summary['next_steps'], 1):
            print(f"  {i}. {step}")
        
        print("="*80)
    
    def run_analysis(self, po_numbers: List[str] = None, output_dir: str = None) -> str:
        """Run the complete DOM analysis."""
        print("🚀 Starting DOM Analysis for Coupa Downloads")
        print("="*60)
        
        if not self.setup_driver():
            return None
        
        try:
            # Analyze test pages
            print("\n🔍 Phase 1: Analyzing test pages...")
            test_results = self.analyze_test_pages()
            
            # Analyze Coupa pages
            print("\n🔍 Phase 2: Analyzing Coupa pages...")
            coupa_results = self.analyze_coupa_pages(po_numbers)
            
            # Generate comprehensive report
            print("\n📊 Phase 3: Generating comprehensive report...")
            report = self.generate_comprehensive_report(test_results, coupa_results)
            
            # Save and display results
            report_file = self.save_report(report, output_dir)
            self.print_summary(report)
            
            return report_file
            
        finally:
            if self.driver:
                self.driver.quit()
                print("\n🔚 WebDriver closed")


def main():
    """Main function to run DOM analysis."""
    parser = argparse.ArgumentParser(description='Run DOM analysis for Coupa Downloads')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run browser in headless mode (default: True)')
    parser.add_argument('--screenshots', action='store_true',
                       help='Save screenshots of analyzed pages')
    parser.add_argument('--po-numbers', nargs='+',
                       help='Specific PO numbers to analyze')
    parser.add_argument('--output-dir', default=None,
                       help='Directory to save analysis report')
    
    args = parser.parse_args()
    
    # Create runner
    runner = DOMAnalysisRunner(
        headless=args.headless,
        save_screenshots=args.screenshots
    )
    
    # Run analysis
    report_file = runner.run_analysis(
        po_numbers=args.po_numbers,
        output_dir=args.output_dir
    )
    
    if report_file:
        print(f"\n✅ Analysis completed successfully!")
        print(f"📄 Full report available at: {report_file}")
    else:
        print("\n❌ Analysis failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 