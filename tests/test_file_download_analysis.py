"""
File Download Analysis Tests
Specialized tests that analyze actual file download mechanisms and artifacts from Coupa pages.
"""

import os
import json
import time
import tempfile
import pytest
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock, patch
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class FileDownloadAnalyzer:
    """
    Analyzes file download mechanisms and artifacts from Coupa pages.
    """
    
    def __init__(self, driver: webdriver.Edge):
        self.driver = driver
        self.download_dir = None
        self.analysis_results = {}
    
    def setup_download_monitoring(self, download_dir: str = None):
        """Setup download directory monitoring."""
        if download_dir is None:
            self.download_dir = tempfile.mkdtemp()
        else:
            self.download_dir = download_dir
            os.makedirs(download_dir, exist_ok=True)
        
        print(f"📁 Monitoring downloads in: {self.download_dir}")
    
    def analyze_download_mechanisms(self, url: str) -> Dict[str, Any]:
        """
        Analyze the download mechanisms available on a page.
        """
        print(f"\n🔍 Analyzing download mechanisms for: {url}")
        
        try:
            self.driver.get(url)
            time.sleep(3)  # Allow page to load
            
            analysis = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'page_title': self.driver.title,
                'download_mechanisms': {},
                'file_artifacts': {},
                'network_requests': {},
                'recommendations': []
            }
            
            # Analyze different download mechanisms
            analysis['download_mechanisms'] = self._analyze_download_mechanisms()
            analysis['file_artifacts'] = self._analyze_file_artifacts()
            analysis['network_requests'] = self._analyze_network_requests()
            analysis['recommendations'] = self._generate_download_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error analyzing download mechanisms for {url}: {e}")
            return {
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _analyze_download_mechanisms(self) -> Dict[str, Any]:
        """Analyze different types of download mechanisms."""
        mechanisms = {
            'direct_links': [],
            'button_clicks': [],
            'form_submissions': [],
            'api_endpoints': [],
            'javascript_triggers': []
        }
        
        try:
            # Find direct download links
            download_links = self.driver.find_elements(By.CSS_SELECTOR, 
                "a[href*='download'], a[href*='.pdf'], a[href*='.docx'], a[href*='.msg']")
            
            for link in download_links:
                link_info = {
                    'href': link.get_attribute('href'),
                    'text': link.text,
                    'title': link.get_attribute('title'),
                    'aria_label': link.get_attribute('aria-label'),
                    'download': link.get_attribute('download'),
                    'target': link.get_attribute('target')
                }
                mechanisms['direct_links'].append(link_info)
            
            # Find download buttons
            download_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                "button[aria-label*='download'], button[title*='download'], button:contains('Download')")
            
            for button in download_buttons:
                button_info = {
                    'text': button.text,
                    'aria_label': button.get_attribute('aria-label'),
                    'title': button.get_attribute('title'),
                    'onclick': button.get_attribute('onclick'),
                    'data_attributes': self._extract_data_attributes(button)
                }
                mechanisms['button_clicks'].append(button_info)
            
            # Find form submissions
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            for form in forms:
                form_info = {
                    'action': form.get_attribute('action'),
                    'method': form.get_attribute('method'),
                    'enctype': form.get_attribute('enctype'),
                    'inputs': self._extract_form_inputs(form)
                }
                if 'download' in str(form_info).lower():
                    mechanisms['form_submissions'].append(form_info)
            
            # Look for JavaScript download triggers
            scripts = self.driver.find_elements(By.TAG_NAME, "script")
            for script in scripts:
                script_content = script.get_attribute('innerHTML')
                if script_content and any(keyword in script_content.lower() for keyword in 
                                        ['download', 'file', 'attachment', 'blob']):
                    mechanisms['javascript_triggers'].append({
                        'type': script.get_attribute('type'),
                        'src': script.get_attribute('src'),
                        'content_preview': script_content[:200] + "..." if len(script_content) > 200 else script_content
                    })
            
        except Exception as e:
            print(f"❌ Error analyzing download mechanisms: {e}")
        
        return mechanisms
    
    def _analyze_file_artifacts(self) -> Dict[str, Any]:
        """Analyze file artifacts and metadata on the page."""
        artifacts = {
            'file_elements': [],
            'file_metadata': [],
            'attachment_containers': [],
            'file_previews': []
        }
        
        try:
            # Find file-related elements
            file_elements = self.driver.find_elements(By.CSS_SELECTOR,
                "span[aria-label*='file'], span[title*='.pdf'], span[title*='.docx'], span[title*='.msg'], " +
                "div[class*='file'], div[class*='attachment'], span[class*='file'], span[class*='attachment']")
            
            for element in file_elements:
                element_info = {
                    'tag_name': element.tag_name,
                    'class': element.get_attribute('class'),
                    'aria_label': element.get_attribute('aria-label'),
                    'title': element.get_attribute('title'),
                    'text_content': element.text,
                    'data_attributes': self._extract_data_attributes(element),
                    'location': element.location,
                    'size': element.size,
                    'is_displayed': element.is_displayed(),
                    'is_enabled': element.is_enabled()
                }
                artifacts['file_elements'].append(element_info)
            
            # Look for file metadata
            metadata_elements = self.driver.find_elements(By.CSS_SELECTOR,
                "span[data-file-size], span[data-file-type], span[data-file-name], " +
                "div[data-file-size], div[data-file-type], div[data-file-name]")
            
            for element in metadata_elements:
                metadata_info = {
                    'tag_name': element.tag_name,
                    'text_content': element.text,
                    'data_attributes': self._extract_data_attributes(element),
                    'parent_info': self._extract_parent_info(element)
                }
                artifacts['file_metadata'].append(metadata_info)
            
            # Find attachment containers
            containers = self.driver.find_elements(By.CSS_SELECTOR,
                "div[class*='attachment'], section[class*='attachment'], " +
                "div[class*='file'], section[class*='file']")
            
            for container in containers:
                container_info = {
                    'tag_name': container.tag_name,
                    'class': container.get_attribute('class'),
                    'id': container.get_attribute('id'),
                    'child_elements': len(container.find_elements(By.XPATH, ".//*")),
                    'file_children': len(container.find_elements(By.CSS_SELECTOR, 
                        "span[aria-label*='file'], span[title*='.pdf'], span[title*='.docx'], span[title*='.msg']"))
                }
                artifacts['attachment_containers'].append(container_info)
            
            # Look for file previews
            previews = self.driver.find_elements(By.CSS_SELECTOR,
                "img[src*='preview'], iframe[src*='preview'], embed[src*='preview']")
            
            for preview in previews:
                preview_info = {
                    'tag_name': preview.tag_name,
                    'src': preview.get_attribute('src'),
                    'alt': preview.get_attribute('alt'),
                    'title': preview.get_attribute('title'),
                    'width': preview.get_attribute('width'),
                    'height': preview.get_attribute('height')
                }
                artifacts['file_previews'].append(preview_info)
            
        except Exception as e:
            print(f"❌ Error analyzing file artifacts: {e}")
        
        return artifacts
    
    def _analyze_network_requests(self) -> Dict[str, Any]:
        """Analyze network requests that might be related to file downloads."""
        requests_info = {
            'xhr_requests': [],
            'fetch_requests': [],
            'download_urls': [],
            'api_calls': []
        }
        
        try:
            # Get page source and look for download-related URLs
            page_source = self.driver.page_source
            
            # Look for common download URL patterns
            import re
            
            # Find download URLs in page source
            download_patterns = [
                r'https?://[^\s"\']*download[^\s"\']*',
                r'https?://[^\s"\']*\.pdf[^\s"\']*',
                r'https?://[^\s"\']*\.docx[^\s"\']*',
                r'https?://[^\s"\']*\.msg[^\s"\']*',
                r'https?://[^\s"\']*attachment[^\s"\']*',
                r'https?://[^\s"\']*file[^\s"\']*'
            ]
            
            for pattern in download_patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                for match in matches:
                    requests_info['download_urls'].append({
                        'url': match,
                        'pattern': pattern,
                        'context': self._extract_context(page_source, match)
                    })
            
            # Look for API endpoints
            api_patterns = [
                r'https?://[^\s"\']*api[^\s"\']*',
                r'https?://[^\s"\']*rest[^\s"\']*',
                r'https?://[^\s"\']*v1[^\s"\']*',
                r'https?://[^\s"\']*v2[^\s"\']*'
            ]
            
            for pattern in api_patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                for match in matches:
                    requests_info['api_calls'].append({
                        'url': match,
                        'pattern': pattern,
                        'context': self._extract_context(page_source, match)
                    })
            
        except Exception as e:
            print(f"❌ Error analyzing network requests: {e}")
        
        return requests_info
    
    def _extract_data_attributes(self, element) -> Dict[str, str]:
        """Extract all data attributes from an element."""
        data_attrs = {}
        try:
            attributes = element.get_property('attributes')
            for attr in attributes:
                if attr['name'].startswith('data-'):
                    data_attrs[attr['name']] = attr['value']
        except:
            pass
        return data_attrs
    
    def _extract_form_inputs(self, form) -> List[Dict[str, str]]:
        """Extract form input information."""
        inputs = []
        try:
            form_inputs = form.find_elements(By.TAG_NAME, "input")
            for inp in form_inputs:
                input_info = {
                    'type': inp.get_attribute('type'),
                    'name': inp.get_attribute('name'),
                    'value': inp.get_attribute('value'),
                    'id': inp.get_attribute('id')
                }
                inputs.append(input_info)
        except:
            pass
        return inputs
    
    def _extract_parent_info(self, element) -> Dict[str, str]:
        """Extract information about the parent element."""
        try:
            parent = element.find_element(By.XPATH, "..")
            return {
                'tag_name': parent.tag_name,
                'class': parent.get_attribute('class'),
                'id': parent.get_attribute('id')
            }
        except:
            return {}
    
    def _extract_context(self, text: str, match: str, context_length: int = 100) -> str:
        """Extract context around a match in text."""
        try:
            index = text.find(match)
            if index != -1:
                start = max(0, index - context_length)
                end = min(len(text), index + len(match) + context_length)
                return text[start:end].replace('\n', ' ').strip()
        except:
            pass
        return ""
    
    def _generate_download_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations for file downloading."""
        recommendations = []
        
        mechanisms = analysis['download_mechanisms']
        artifacts = analysis['file_artifacts']
        requests = analysis['network_requests']
        
        # Analyze direct links
        if mechanisms['direct_links']:
            recommendations.append(f"🎯 Found {len(mechanisms['direct_links'])} direct download links - use href attributes")
        
        # Analyze button clicks
        if mechanisms['button_clicks']:
            recommendations.append(f"🖱️ Found {len(mechanisms['button_clicks'])} download buttons - use click() method")
        
        # Analyze form submissions
        if mechanisms['form_submissions']:
            recommendations.append(f"📝 Found {len(mechanisms['form_submissions'])} download forms - use form submission")
        
        # Analyze file elements
        if artifacts['file_elements']:
            recommendations.append(f"📎 Found {len(artifacts['file_elements'])} file elements - use aria-label or title attributes")
        
        # Analyze download URLs
        if requests['download_urls']:
            recommendations.append(f"🔗 Found {len(requests['download_urls'])} download URLs - use direct HTTP requests")
        
        # Analyze API calls
        if requests['api_calls']:
            recommendations.append(f"🔌 Found {len(requests['api_calls'])} API endpoints - use API calls for downloads")
        
        # General recommendations
        if not any([mechanisms['direct_links'], mechanisms['button_clicks'], 
                   mechanisms['form_submissions'], requests['download_urls']]):
            recommendations.append("⚠️ No obvious download mechanisms found - may need JavaScript execution")
        
        recommendations.extend([
            "⚡ Prefer direct links over button clicks for better performance",
            "🔄 Implement retry logic for failed downloads",
            "📁 Monitor download directory for new files",
            "🔍 Log download attempts for debugging",
            "⏱️ Set appropriate timeouts for download operations"
        ])
        
        return recommendations
    
    def test_download_interaction(self, url: str, element_selector: str = None) -> Dict[str, Any]:
        """
        Test actual download interaction with a specific element.
        """
        print(f"\n🧪 Testing download interaction for: {url}")
        
        try:
            self.driver.get(url)
            time.sleep(3)
            
            # Get initial file count
            initial_files = set(os.listdir(self.download_dir)) if os.path.exists(self.download_dir) else set()
            
            test_results = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'element_selector': element_selector,
                'initial_files': list(initial_files),
                'download_attempted': False,
                'download_successful': False,
                'new_files': [],
                'error': None
            }
            
            if element_selector:
                try:
                    # Find and click the element
                    element = self.driver.find_element(By.CSS_SELECTOR, element_selector)
                    
                    if element.is_displayed() and element.is_enabled():
                        print(f"🖱️ Clicking element: {element_selector}")
                        element.click()
                        test_results['download_attempted'] = True
                        
                        # Wait for download
                        time.sleep(5)
                        
                        # Check for new files
                        current_files = set(os.listdir(self.download_dir)) if os.path.exists(self.download_dir) else set()
                        new_files = current_files - initial_files
                        
                        if new_files:
                            test_results['download_successful'] = True
                            test_results['new_files'] = list(new_files)
                            print(f"✅ Download successful! New files: {new_files}")
                        else:
                            print("❌ No new files detected after download attempt")
                    else:
                        test_results['error'] = "Element not clickable"
                        print("❌ Element not clickable")
                        
                except Exception as e:
                    test_results['error'] = str(e)
                    print(f"❌ Error during download test: {e}")
            
            return test_results
            
        except Exception as e:
            print(f"❌ Error testing download interaction: {e}")
            return {
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


class TestFileDownloadAnalysis:
    """Test file download analysis functionality."""
    
    @pytest.fixture
    def download_analyzer(self):
        """Create file download analyzer for testing."""
        try:
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
            
            analyzer = FileDownloadAnalyzer(driver)
            analyzer.setup_download_monitoring(download_dir)
            
            yield analyzer
            
        except Exception as e:
            pytest.skip(f"Edge WebDriver not available: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()
    
    def test_download_mechanism_analysis(self, download_analyzer):
        """Test analysis of download mechanisms."""
        test_url = "https://httpbin.org/forms/post"
        analysis = download_analyzer.analyze_download_mechanisms(test_url)
        
        assert 'url' in analysis
        assert 'download_mechanisms' in analysis
        assert 'file_artifacts' in analysis
        assert 'network_requests' in analysis
        assert 'recommendations' in analysis
        
        mechanisms = analysis['download_mechanisms']
        assert 'direct_links' in mechanisms
        assert 'button_clicks' in mechanisms
        assert 'form_submissions' in mechanisms
        assert 'api_endpoints' in mechanisms
        assert 'javascript_triggers' in mechanisms
        
        print(f"\n📊 Download Mechanism Analysis:")
        print(f"Direct links: {len(mechanisms['direct_links'])}")
        print(f"Button clicks: {len(mechanisms['button_clicks'])}")
        print(f"Form submissions: {len(mechanisms['form_submissions'])}")
        print(f"JavaScript triggers: {len(mechanisms['javascript_triggers'])}")
    
    def test_file_artifact_analysis(self, download_analyzer):
        """Test analysis of file artifacts."""
        test_url = "https://httpbin.org/html"
        analysis = download_analyzer.analyze_download_mechanisms(test_url)
        
        artifacts = analysis['file_artifacts']
        assert 'file_elements' in artifacts
        assert 'file_metadata' in artifacts
        assert 'attachment_containers' in artifacts
        assert 'file_previews' in artifacts
        
        print(f"\n📎 File Artifact Analysis:")
        print(f"File elements: {len(artifacts['file_elements'])}")
        print(f"File metadata: {len(artifacts['file_metadata'])}")
        print(f"Attachment containers: {len(artifacts['attachment_containers'])}")
        print(f"File previews: {len(artifacts['file_previews'])}")
    
    def test_network_request_analysis(self, download_analyzer):
        """Test analysis of network requests."""
        test_url = "https://httpbin.org/json"
        analysis = download_analyzer.analyze_download_mechanisms(test_url)
        
        requests = analysis['network_requests']
        assert 'xhr_requests' in requests
        assert 'fetch_requests' in requests
        assert 'download_urls' in requests
        assert 'api_calls' in requests
        
        print(f"\n🌐 Network Request Analysis:")
        print(f"Download URLs: {len(requests['download_urls'])}")
        print(f"API calls: {len(requests['api_calls'])}")
    
    def test_coupa_download_analysis(self, download_analyzer):
        """Test analysis of Coupa download mechanisms."""
        # Test with Coupa login page first
        login_url = "https://unilever.coupahost.com/login"
        analysis = download_analyzer.analyze_download_mechanisms(login_url)
        
        print(f"\n🔐 Coupa Login Page Download Analysis:")
        print(f"Page title: {analysis['page_title']}")
        
        mechanisms = analysis['download_mechanisms']
        print(f"Direct links: {len(mechanisms['direct_links'])}")
        print(f"Button clicks: {len(mechanisms['button_clicks'])}")
        print(f"Form submissions: {len(mechanisms['form_submissions'])}")
        
        artifacts = analysis['file_artifacts']
        print(f"File elements: {len(artifacts['file_elements'])}")
        print(f"Attachment containers: {len(artifacts['attachment_containers'])}")
        
        # Test with a PO page
        po_url = "https://unilever.coupahost.com/order_headers/15826591"
        po_analysis = download_analyzer.analyze_download_mechanisms(po_url)
        
        print(f"\n📋 Coupa PO Page Download Analysis:")
        print(f"Page title: {po_analysis['page_title']}")
        
        po_mechanisms = po_analysis['download_mechanisms']
        print(f"Direct links: {len(po_mechanisms['direct_links'])}")
        print(f"Button clicks: {len(po_mechanisms['button_clicks'])}")
        
        po_artifacts = po_analysis['file_artifacts']
        print(f"File elements: {len(po_artifacts['file_elements'])}")
        print(f"Attachment containers: {len(po_artifacts['attachment_containers'])}")
        
        # Generate recommendations
        print(f"\n🎯 Recommendations:")
        for i, rec in enumerate(po_analysis['recommendations'][:5], 1):
            print(f"  {i}. {rec}")


class TestDownloadStrategyComparison:
    """Test comparison of different download strategies."""
    
    def test_direct_link_vs_button_click(self, download_analyzer):
        """Compare direct link vs button click download strategies."""
        test_url = "https://httpbin.org/forms/post"
        analysis = download_analyzer.analyze_download_mechanisms(test_url)
        
        mechanisms = analysis['download_mechanisms']
        
        print(f"\n⚖️ Download Strategy Comparison:")
        print(f"Direct links available: {len(mechanisms['direct_links'])}")
        print(f"Button clicks available: {len(mechanisms['button_clicks'])}")
        
        if mechanisms['direct_links']:
            print("✅ Direct links preferred - faster and more reliable")
        elif mechanisms['button_clicks']:
            print("🖱️ Button clicks available - may require JavaScript execution")
        else:
            print("⚠️ No obvious download mechanisms found")
    
    def test_file_artifact_strategies(self, download_analyzer):
        """Test different strategies for finding file artifacts."""
        test_url = "https://httpbin.org/html"
        analysis = download_analyzer.analyze_download_mechanisms(test_url)
        
        artifacts = analysis['file_artifacts']
        
        print(f"\n🔍 File Artifact Detection Strategies:")
        print(f"File elements found: {len(artifacts['file_elements'])}")
        print(f"File metadata found: {len(artifacts['file_metadata'])}")
        print(f"Attachment containers found: {len(artifacts['attachment_containers'])}")
        
        # Analyze element attributes
        if artifacts['file_elements']:
            element = artifacts['file_elements'][0]
            print(f"\n📋 Sample file element attributes:")
            print(f"  Tag: {element['tag_name']}")
            print(f"  Class: {element['class']}")
            print(f"  Aria-label: {element['aria_label']}")
            print(f"  Title: {element['title']}")
            print(f"  Data attributes: {element['data_attributes']}")


if __name__ == "__main__":
    # Run specific tests for manual exploration
    print("🧪 File Download Analysis Testing")
    print("=" * 50)
    
    # This would require a real browser setup
    print("Note: These tests require a real browser and may need login credentials")
    print("Run with pytest to execute the full test suite") 