#!/usr/bin/env python3
"""
Comprehensive Analysis Test Runner
Combines DOM analysis and file download analysis for complete Coupa file fetching insights.
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
from tests.test_file_download_analysis import FileDownloadAnalyzer
from tests.po_sampler import POSampler
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions


class ComprehensiveAnalyzer:
    """
    Comprehensive analyzer that combines DOM and file download analysis.
    """
    
    def __init__(self, headless: bool = True, save_screenshots: bool = False):
        self.headless = headless
        self.save_screenshots = save_screenshots
        self.driver = None
        self.dom_analyzer = None
        self.download_analyzer = None
        self.results = {}
    
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
            
            # Initialize analyzers
            self.dom_analyzer = DOMAnalyzer(self.driver)
            self.download_analyzer = FileDownloadAnalyzer(self.driver)
            self.download_analyzer.setup_download_monitoring(download_dir)
            
            print("✅ Edge WebDriver and analyzers setup successful")
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup Edge WebDriver: {e}")
            return False
    
    def analyze_page_comprehensive(self, url: str, page_name: str | None = None) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a page including DOM and download mechanisms.
        """
        if page_name is None:
            page_name = url.split('/')[-1] or 'page'
        
        print(f"\n🔍 Comprehensive analysis of: {page_name}")
        print(f"URL: {url}")
        
        comprehensive_analysis = {
            'page_name': page_name,
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'dom_analysis': {},
            'download_analysis': {},
            'combined_insights': {},
            'recommendations': []
        }
        
        try:
            # Perform DOM analysis
            print("  📊 Performing DOM analysis...")
            if self.dom_analyzer:
                dom_analysis = self.dom_analyzer.analyze_page_structure(url)
                comprehensive_analysis['dom_analysis'] = dom_analysis
            
            # Perform download analysis
            print("  📎 Performing download analysis...")
            if self.download_analyzer:
                download_analysis = self.download_analyzer.analyze_download_mechanisms(url)
                comprehensive_analysis['download_analysis'] = download_analysis
            
            # Generate combined insights
            comprehensive_analysis['combined_insights'] = self._generate_combined_insights(
                comprehensive_analysis['dom_analysis'], comprehensive_analysis['download_analysis']
            )
            
            # Generate comprehensive recommendations
            comprehensive_analysis['recommendations'] = self._generate_comprehensive_recommendations(
                comprehensive_analysis
            )
            
            # Save screenshot if requested
            if self.save_screenshots and self.driver:
                screenshot_path = f"comprehensive_{page_name}.png"
                self.driver.save_screenshot(screenshot_path)
                print(f"  📸 Screenshot saved: {screenshot_path}")
            
            return comprehensive_analysis
            
        except Exception as e:
            print(f"❌ Error in comprehensive analysis: {e}")
            return {
                'page_name': page_name,
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_combined_insights(self, dom_analysis: Dict[str, Any], 
                                  download_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights by combining DOM and download analysis."""
        insights = {
            'best_download_strategy': None,
            'element_interaction_method': None,
            'file_detection_method': None,
            'supplier_detection_method': None,
            'performance_considerations': [],
            'reliability_factors': [],
            'implementation_complexity': 'low'
        }
        
        # Determine best download strategy
        download_mechanisms = download_analysis.get('download_mechanisms', {})
        dom_elements = dom_analysis.get('elements_found', {})
        
        if download_mechanisms.get('direct_links'):
            insights['best_download_strategy'] = 'direct_links'
            insights['element_interaction_method'] = 'href_extraction'
        elif download_mechanisms.get('button_clicks'):
            insights['best_download_strategy'] = 'button_clicks'
            insights['element_interaction_method'] = 'click()'
        elif download_mechanisms.get('form_submissions'):
            insights['best_download_strategy'] = 'form_submission'
            insights['element_interaction_method'] = 'form_submit()'
        else:
            insights['best_download_strategy'] = 'javascript_execution'
            insights['element_interaction_method'] = 'execute_script()'
        
        # Determine file detection method
        file_artifacts = download_analysis.get('file_artifacts', {})
        attachment_selectors = dom_analysis.get('attachment_selectors', {})
        
        if attachment_selectors.get('best_selectors'):
            insights['file_detection_method'] = 'css_selectors'
        elif file_artifacts.get('file_elements'):
            insights['file_detection_method'] = 'element_attributes'
        else:
            insights['file_detection_method'] = 'pattern_matching'
        
        # Determine supplier detection method
        supplier_selectors = dom_analysis.get('supplier_selectors', {})
        if supplier_selectors.get('best_selectors'):
            insights['supplier_detection_method'] = 'css_selectors'
        else:
            insights['supplier_detection_method'] = 'xpath_fallback'
        
        # Performance considerations
        total_elements = dom_elements.get('total_elements', 0)
        if total_elements > 1000:
            insights['performance_considerations'].append('High element count - use specific selectors')
            insights['implementation_complexity'] = 'medium'
        
        if download_mechanisms.get('javascript_triggers'):
            insights['performance_considerations'].append('JavaScript execution required')
            insights['implementation_complexity'] = 'high'
        
        # Reliability factors
        if download_mechanisms.get('direct_links'):
            insights['reliability_factors'].append('Direct links are most reliable')
        elif download_mechanisms.get('button_clicks'):
            insights['reliability_factors'].append('Button clicks may be affected by page state')
        
        if attachment_selectors.get('best_selectors'):
            insights['reliability_factors'].append('CSS selectors provide good reliability')
        
        return insights
    
    def _generate_comprehensive_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate comprehensive recommendations based on combined analysis."""
        recommendations = []
        
        insights = analysis['combined_insights']
        dom_analysis = analysis['dom_analysis']
        download_analysis = analysis['download_analysis']
        
        # Strategy recommendations
        strategy = insights['best_download_strategy']
        if strategy == 'direct_links':
            recommendations.append("🎯 Use direct link extraction for optimal performance")
        elif strategy == 'button_clicks':
            recommendations.append("🖱️ Use button click simulation with proper wait conditions")
        elif strategy == 'form_submission':
            recommendations.append("📝 Use form submission with appropriate data")
        else:
            recommendations.append("⚡ Use JavaScript execution for complex download scenarios")
        
        # Element interaction recommendations
        interaction_method = insights['element_interaction_method']
        if interaction_method == 'href_extraction':
            recommendations.append("🔗 Extract href attributes and use direct HTTP requests")
        elif interaction_method == 'click()':
            recommendations.append("🖱️ Use Selenium click() method with explicit waits")
        elif interaction_method == 'form_submit()':
            recommendations.append("📝 Submit forms with required parameters")
        else:
            recommendations.append("⚡ Execute JavaScript for dynamic interactions")
        
        # File detection recommendations
        file_method = insights['file_detection_method']
        if file_method == 'css_selectors':
            best_selectors = dom_analysis.get('attachment_selectors', {}).get('best_selectors', [])
            if best_selectors:
                top_selector = best_selectors[0]['selector']
                recommendations.append(f"📎 Use CSS selector: {top_selector}")
        elif file_method == 'element_attributes':
            recommendations.append("🔍 Use aria-label and title attributes for file detection")
        else:
            recommendations.append("🔍 Use pattern matching for file identification")
        
        # Supplier detection recommendations
        supplier_method = insights['supplier_detection_method']
        if supplier_method == 'css_selectors':
            best_suppliers = dom_analysis.get('supplier_selectors', {}).get('best_selectors', [])
            if best_suppliers:
                top_supplier = best_suppliers[0]['selector']
                recommendations.append(f"🏢 Use CSS selector: {top_supplier}")
        else:
            recommendations.append("🏢 Use XPath fallback for supplier detection")
        
        # Performance recommendations
        for consideration in insights['performance_considerations']:
            recommendations.append(f"⚡ {consideration}")
        
        # Reliability recommendations
        for factor in insights['reliability_factors']:
            recommendations.append(f"🛡️ {factor}")
        
        # Implementation recommendations
        complexity = insights['implementation_complexity']
        if complexity == 'high':
            recommendations.append("⚠️ High implementation complexity - consider phased approach")
        elif complexity == 'medium':
            recommendations.append("📋 Medium complexity - implement with proper error handling")
        else:
            recommendations.append("✅ Low complexity - straightforward implementation")
        
        # General best practices
        recommendations.extend([
            "🔄 Implement retry logic for failed operations",
            "📁 Monitor download directory for new files",
            "🔍 Add comprehensive logging for debugging",
            "⏱️ Set appropriate timeouts for all operations",
            "🛡️ Handle authentication and session management"
        ])
        
        return recommendations
    
    def analyze_coupa_ecosystem(self, po_numbers: List[str] | None = None) -> Dict[str, Any]:
        """
        Analyze the complete Coupa ecosystem including login, dashboard, and PO pages.
        """
        if po_numbers is None:
            # Use PO sampler to get optimal sample
            sampler = POSampler()
            if sampler.load_po_data():
                po_numbers = sampler.select_optimal_sample()
                sampler.print_sampling_report(po_numbers)
            else:
                po_numbers = ['15826591', '15873456', '15873457']  # Fallback PO numbers
        
        ecosystem_analysis = {
            'timestamp': datetime.now().isoformat(),
            'pages_analyzed': {},
            'ecosystem_insights': {},
            'cross_page_patterns': {},
            'implementation_strategy': {},
            'recommendations': []
        }
        
        # Define pages to analyze
        pages_to_analyze = {
            'login': 'https://unilever.coupahost.com/login',
            'dashboard': 'https://unilever.coupahost.com/dashboard'
        }
        
        # Add PO pages
        for po in po_numbers:
            pages_to_analyze[f'po_{po}'] = f'https://unilever.coupahost.com/order_headers/{po}'
        
        # Analyze each page
        for page_name, url in pages_to_analyze.items():
            print(f"\n🔍 Analyzing Coupa ecosystem page: {page_name}")
            analysis = self.analyze_page_comprehensive(url, page_name)
            ecosystem_analysis['pages_analyzed'][page_name] = analysis
        
        # Generate ecosystem insights
        ecosystem_analysis['ecosystem_insights'] = self._generate_ecosystem_insights(
            ecosystem_analysis['pages_analyzed']
        )
        
        # Generate cross-page patterns
        ecosystem_analysis['cross_page_patterns'] = self._generate_cross_page_patterns(
            ecosystem_analysis['pages_analyzed']
        )
        
        # Generate implementation strategy
        ecosystem_analysis['implementation_strategy'] = self._generate_implementation_strategy(
            ecosystem_analysis
        )
        
        # Generate ecosystem recommendations
        ecosystem_analysis['recommendations'] = self._generate_ecosystem_recommendations(
            ecosystem_analysis
        )
        
        return ecosystem_analysis
    
    def _generate_ecosystem_insights(self, pages_analyzed: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights about the Coupa ecosystem."""
        insights = {
            'authentication_required': False,
            'consistent_patterns': [],
            'page_specific_patterns': {},
            'navigation_patterns': [],
            'common_elements': {}
        }
        
        # Check if authentication is required
        login_analysis = pages_analyzed.get('login', {})
        if login_analysis and 'error' not in login_analysis:
            insights['authentication_required'] = True
        
        # Analyze patterns across pages
        all_selectors = {}
        all_mechanisms = {}
        
        for page_name, analysis in pages_analyzed.items():
            if 'error' not in analysis:
                # Collect selectors
                dom_analysis = analysis.get('dom_analysis', {})
                attachment_selectors = dom_analysis.get('attachment_selectors', {})
                supplier_selectors = dom_analysis.get('supplier_selectors', {})
                
                if attachment_selectors.get('best_selectors'):
                    all_selectors[page_name] = attachment_selectors['best_selectors']
                
                if supplier_selectors.get('best_selectors'):
                    all_selectors[f"{page_name}_supplier"] = supplier_selectors['best_selectors']
                
                # Collect download mechanisms
                download_analysis = analysis.get('download_analysis', {})
                mechanisms = download_analysis.get('download_mechanisms', {})
                all_mechanisms[page_name] = mechanisms
        
        # Find consistent patterns
        if len(all_selectors) > 1:
            insights['consistent_patterns'].append('Multiple pages have similar selector patterns')
        
        if len(all_mechanisms) > 1:
            insights['consistent_patterns'].append('Download mechanisms vary across pages')
        
        insights['common_elements'] = {
            'selectors': all_selectors,
            'mechanisms': all_mechanisms
        }
        
        return insights
    
    def _generate_cross_page_patterns(self, pages_analyzed: Dict[str, Any]) -> Dict[str, Any]:
        """Generate patterns that appear across multiple pages."""
        patterns = {
            'selector_consistency': {},
            'mechanism_consistency': {},
            'element_structure': {},
            'performance_patterns': {}
        }
        
        # Analyze selector consistency
        selector_patterns = {}
        for page_name, analysis in pages_analyzed.items():
            if 'error' not in analysis:
                dom_analysis = analysis.get('dom_analysis', {})
                attachment_selectors = dom_analysis.get('attachment_selectors', {})
                
                if attachment_selectors.get('best_selectors'):
                    for selector_info in attachment_selectors['best_selectors']:
                        selector = selector_info['selector']
                        if selector not in selector_patterns:
                            selector_patterns[selector] = []
                        selector_patterns[selector].append(page_name)
        
        # Find consistent selectors
        for selector, pages in selector_patterns.items():
            if len(pages) > 1:
                patterns['selector_consistency'][selector] = {
                    'pages': pages,
                    'consistency_score': len(pages) / len(pages_analyzed)
                }
        
        return patterns
    
    def _generate_implementation_strategy(self, ecosystem_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate implementation strategy based on ecosystem analysis."""
        strategy = {
            'phase_1': [],
            'phase_2': [],
            'phase_3': [],
            'risk_mitigation': [],
            'success_criteria': []
        }
        
        insights = ecosystem_analysis['ecosystem_insights']
        patterns = ecosystem_analysis['cross_page_patterns']
        
        # Phase 1: Basic implementation
        strategy['phase_1'] = [
            "Implement authentication handling",
            "Set up basic page navigation",
            "Implement consistent selector usage",
            "Add basic error handling"
        ]
        
        # Phase 2: Enhanced functionality
        strategy['phase_2'] = [
            "Implement download mechanism detection",
            "Add file artifact analysis",
            "Implement supplier detection",
            "Add performance monitoring"
        ]
        
        # Phase 3: Optimization
        strategy['phase_3'] = [
            "Optimize selector performance",
            "Implement retry mechanisms",
            "Add comprehensive logging",
            "Implement monitoring and alerting"
        ]
        
        # Risk mitigation
        if insights['authentication_required']:
            strategy['risk_mitigation'].append("Handle session expiration gracefully")
        
        if patterns['selector_consistency']:
            strategy['risk_mitigation'].append("Implement fallback selectors")
        
        strategy['risk_mitigation'].extend([
            "Handle network timeouts",
            "Implement rate limiting",
            "Add data validation"
        ])
        
        # Success criteria
        strategy['success_criteria'] = [
            "Successfully authenticate to Coupa",
            "Navigate to PO pages without errors",
            "Detect file attachments consistently",
            "Download files successfully",
            "Extract supplier information accurately"
        ]
        
        return strategy
    
    def _generate_ecosystem_recommendations(self, ecosystem_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations for the entire Coupa ecosystem."""
        recommendations = []
        
        insights = ecosystem_analysis['ecosystem_insights']
        strategy = ecosystem_analysis['implementation_strategy']
        
        # Authentication recommendations
        if insights['authentication_required']:
            recommendations.append("🔐 Implement robust authentication handling with session management")
        
        # Consistency recommendations
        if insights['consistent_patterns']:
            recommendations.append("🔄 Leverage consistent patterns across pages for reliable implementation")
        
        # Implementation recommendations
        recommendations.append("📋 Follow phased implementation approach for manageable development")
        
        # Risk mitigation recommendations
        for mitigation in strategy['risk_mitigation']:
            recommendations.append(f"🛡️ {mitigation}")
        
        # Performance recommendations
        recommendations.extend([
            "⚡ Use consistent selectors across pages for better performance",
            "🔄 Implement caching for frequently accessed elements",
            "📊 Monitor performance metrics across all pages"
        ])
        
        return recommendations
    
    def save_comprehensive_report(self, report: Dict[str, Any], output_dir: str | None = None) -> str:
        """Save the comprehensive analysis report."""
        if output_dir is None:
            output_dir = tempfile.gettempdir()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"comprehensive_coupa_analysis_{timestamp}.json")
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Comprehensive report saved to: {report_file}")
        return report_file
    
    def print_comprehensive_summary(self, report: Dict[str, Any]):
        """Print a comprehensive summary of the analysis."""
        print("\n" + "="*100)
        print("📊 COMPREHENSIVE COUPA ECOSYSTEM ANALYSIS REPORT")
        print("="*100)
        
        print(f"📅 Analysis Date: {report['timestamp']}")
        print(f"📋 Pages Analyzed: {len(report['pages_analyzed'])}")
        
        # Ecosystem insights
        insights = report['ecosystem_insights']
        print(f"\n🔍 Ecosystem Insights:")
        print(f"  Authentication Required: {insights['authentication_required']}")
        print(f"  Consistent Patterns: {len(insights['consistent_patterns'])}")
        
        # Implementation strategy
        strategy = report['implementation_strategy']
        print(f"\n📋 Implementation Strategy:")
        print(f"  Phase 1 Tasks: {len(strategy['phase_1'])}")
        print(f"  Phase 2 Tasks: {len(strategy['phase_2'])}")
        print(f"  Phase 3 Tasks: {len(strategy['phase_3'])}")
        print(f"  Risk Mitigations: {len(strategy['risk_mitigation'])}")
        
        # Top recommendations
        print(f"\n🎯 Top Recommendations:")
        for i, rec in enumerate(report['recommendations'][:10], 1):
            print(f"  {i}. {rec}")
        
        print("="*100)
    
    def run_comprehensive_analysis(self, po_numbers: List[str] | None = None, output_dir: str | None = None) -> str | None:
        """Run the complete comprehensive analysis."""
        print("🚀 Starting Comprehensive Coupa Ecosystem Analysis")
        print("="*80)
        
        if not self.setup_driver():
            return None
        
        try:
            # Run ecosystem analysis
            print("\n🔍 Running comprehensive ecosystem analysis...")
            report = self.analyze_coupa_ecosystem(po_numbers)
            
            # Save and display results
            report_file = self.save_comprehensive_report(report, output_dir)
            self.print_comprehensive_summary(report)
            
            return report_file
            
        finally:
            if self.driver:
                self.driver.quit()
                print("\n🔚 WebDriver closed")


def main():
    """Main function to run comprehensive analysis."""
    parser = argparse.ArgumentParser(description='Run comprehensive Coupa ecosystem analysis')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run browser in headless mode (default: True)')
    parser.add_argument('--screenshots', action='store_true',
                       help='Save screenshots of analyzed pages')
    parser.add_argument('--po-numbers', nargs='+',
                       help='Specific PO numbers to analyze')
    parser.add_argument('--output-dir', default=None,
                       help='Directory to save analysis report')
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = ComprehensiveAnalyzer(
        headless=args.headless,
        save_screenshots=args.screenshots
    )
    
    # Run analysis
    report_file = analyzer.run_comprehensive_analysis(
        po_numbers=args.po_numbers,
        output_dir=args.output_dir
    )
    
    if report_file:
        print(f"\n✅ Comprehensive analysis completed successfully!")
        print(f"📄 Full report available at: {report_file}")
    else:
        print("\n❌ Analysis failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 