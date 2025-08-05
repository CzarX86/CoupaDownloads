"""
DOM Analysis Tests for Coupa Downloads
Tests that actually download and analyze the DOM to determine the best approach for fetching files.
"""

import os
import json
import time
import tempfile
import pytest
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock, patch
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class DOMAnalyzer:
    """
    Analyzes the DOM structure of Coupa pages to determine the best approach for fetching files.
    """
    
    def __init__(self, driver: webdriver.Edge):
        self.driver = driver
        self.analysis_results = {}
    
    def analyze_page_structure(self, url: str) -> Dict[str, Any]:
        """
        Comprehensive analysis of a Coupa page structure.
        """
        print(f"\n🔍 Analyzing page: {url}")
        
        try:
            self.driver.get(url)
            time.sleep(3)  # Allow page to load
            
            analysis = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'page_title': self.driver.title,
                'current_url': self.driver.current_url,
                'page_source_length': len(self.driver.page_source),
                'elements_found': {},
                'attachment_selectors': {},
                'supplier_selectors': {},
                'page_structure': {},
                'recommendations': []
            }
            
            # Analyze different aspects
            analysis['elements_found'] = self._analyze_page_elements()
            analysis['attachment_selectors'] = self._analyze_attachment_selectors()
            analysis['supplier_selectors'] = self._analyze_supplier_selectors()
            analysis['page_structure'] = self._analyze_page_structure()
            analysis['recommendations'] = self._generate_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error analyzing page {url}: {e}")
            return {
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _analyze_page_elements(self) -> Dict[str, Any]:
        """Analyze all elements on the page that might be relevant."""
        elements = {
            'total_elements': 0,
            'attachment_like_elements': [],
            'download_like_elements': [],
            'file_like_elements': [],
            'button_elements': [],
            'link_elements': [],
            'span_elements': []
        }
        
        try:
            # Count total elements
            all_elements = self.driver.find_elements(By.XPATH, "//*")
            elements['total_elements'] = len(all_elements)
            
            # Find attachment-like elements
            attachment_patterns = [
                "//span[contains(@aria-label, 'file attachment')]",
                "//span[contains(@title, '.pdf')]",
                "//span[contains(@title, '.docx')]",
                "//span[contains(@title, '.msg')]",
                "//a[contains(@href, 'download')]",
                "//button[contains(@aria-label, 'download')]",
                "//span[contains(@class, 'attachment')]",
                "//div[contains(@class, 'attachment')]",
                "//span[contains(@role, 'button')]"
            ]
            
            for pattern in attachment_patterns:
                found_elements = self.driver.find_elements(By.XPATH, pattern)
                for elem in found_elements:
                    element_info = self._extract_element_info(elem)
                    elements['attachment_like_elements'].append(element_info)
            
            # Find download-like elements
            download_patterns = [
                "//a[contains(@href, 'download')]",
                "//button[contains(text(), 'Download')]",
                "//span[contains(text(), 'Download')]",
                "//div[contains(@class, 'download')]"
            ]
            
            for pattern in download_patterns:
                found_elements = self.driver.find_elements(By.XPATH, pattern)
                for elem in found_elements:
                    element_info = self._extract_element_info(elem)
                    elements['download_like_elements'].append(element_info)
            
            # Find file-like elements
            file_patterns = [
                "//span[contains(@title, '.')]",
                "//a[contains(@href, '.pdf')]",
                "//a[contains(@href, '.docx')]",
                "//a[contains(@href, '.msg')]"
            ]
            
            for pattern in file_patterns:
                found_elements = self.driver.find_elements(By.XPATH, pattern)
                for elem in found_elements:
                    element_info = self._extract_element_info(elem)
                    elements['file_like_elements'].append(element_info)
            
            # Count button and link elements
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            links = self.driver.find_elements(By.TAG_NAME, "a")
            spans = self.driver.find_elements(By.TAG_NAME, "span")
            
            elements['button_elements'] = len(buttons)
            elements['link_elements'] = len(links)
            elements['span_elements'] = len(spans)
            
        except Exception as e:
            print(f"❌ Error analyzing elements: {e}")
        
        return elements
    
    def _analyze_attachment_selectors(self) -> Dict[str, Any]:
        """Analyze different attachment selector strategies."""
        selectors = {
            'current_selectors': {},
            'alternative_selectors': {},
            'best_selectors': []
        }
        
        # Test current selectors from config
        current_selectors = [
            "span[aria-label*='file attachment']",
            "span[role='button'][aria-label*='file attachment']",
            "span[title*='.pdf']",
            "span[title*='.docx']",
            "span[title*='.msg']"
        ]
        
        for selector in current_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                selectors['current_selectors'][selector] = {
                    'count': len(elements),
                    'elements': [self._extract_element_info(elem) for elem in elements]
                }
            except Exception as e:
                selectors['current_selectors'][selector] = {'error': str(e)}
        
        # Test alternative selectors
        alternative_selectors = [
            "span[aria-label*='download']",
            "span[aria-label*='attachment']",
            "button[aria-label*='file']",
            "a[href*='download']",
            "span[class*='attachment']",
            "div[class*='attachment']",
            "span[data-testid*='attachment']",
            "span[data-testid*='download']",
            "button[data-testid*='download']",
            "span[title*='file']",
            "span[title*='document']"
        ]
        
        for selector in alternative_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                selectors['alternative_selectors'][selector] = {
                    'count': len(elements),
                    'elements': [self._extract_element_info(elem) for elem in elements]
                }
            except Exception as e:
                selectors['alternative_selectors'][selector] = {'error': str(e)}
        
        # Find best selectors (those that return elements)
        for selector, data in selectors['current_selectors'].items():
            if isinstance(data, dict) and data.get('count', 0) > 0:
                selectors['best_selectors'].append({
                    'selector': selector,
                    'count': data['count'],
                    'type': 'current'
                })
        
        for selector, data in selectors['alternative_selectors'].items():
            if isinstance(data, dict) and data.get('count', 0) > 0:
                selectors['best_selectors'].append({
                    'selector': selector,
                    'count': data['count'],
                    'type': 'alternative'
                })
        
        # Sort by count
        selectors['best_selectors'].sort(key=lambda x: x['count'], reverse=True)
        
        return selectors
    
    def _analyze_supplier_selectors(self) -> Dict[str, Any]:
        """Analyze supplier name selector strategies."""
        selectors = {
            'current_selectors': {},
            'alternative_selectors': {},
            'best_selectors': []
        }
        
        # Test current CSS selectors
        current_css_selectors = [
            "span[data-supplier-name]",
            "span[class*='supplier-name']",
            ".supplier-info span",
            "[data-testid*='supplier'] span",
            "section:nth-of-type(2) div:nth-of-type(2) span:nth-of-type(3)",
            "section div[class*='supplier'] span",
            "div[class*='po-detail'] span:nth-child(3)"
        ]
        
        for selector in current_css_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                selectors['current_selectors'][selector] = {
                    'count': len(elements),
                    'elements': [self._extract_element_info(elem) for elem in elements]
                }
            except Exception as e:
                selectors['current_selectors'][selector] = {'error': str(e)}
        
        # Test alternative selectors
        alternative_selectors = [
            "span[class*='supplier']",
            "div[class*='supplier']",
            "span[data-testid*='vendor']",
            "span[data-testid*='company']",
            "div[class*='vendor']",
            "div[class*='company']",
            "span[title*='supplier']",
            "span[title*='vendor']",
            "section span:nth-child(3)",
            "section span:nth-child(4)",
            "div[class*='header'] span",
            "div[class*='info'] span"
        ]
        
        for selector in alternative_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                selectors['alternative_selectors'][selector] = {
                    'count': len(elements),
                    'elements': [self._extract_element_info(elem) for elem in elements]
                }
            except Exception as e:
                selectors['alternative_selectors'][selector] = {'error': str(e)}
        
        # Test XPath selectors
        xpath_selectors = [
            "/html/body/div[1]/div[5]/div/div/div[4]/div/div[3]/section[2]/div[2]/div[1]/div/span[3]",
            "//section[2]//span[3]",
            "//div[contains(@class, 'supplier')]//span",
            "//span[contains(@class, 'supplier')]",
            "//div[contains(@class, 'vendor')]//span",
            "//span[contains(@class, 'vendor')]"
        ]
        
        for xpath in xpath_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                selectors['alternative_selectors'][f"xpath: {xpath}"] = {
                    'count': len(elements),
                    'elements': [self._extract_element_info(elem) for elem in elements]
                }
            except Exception as e:
                selectors['alternative_selectors'][f"xpath: {xpath}"] = {'error': str(e)}
        
        # Find best selectors
        for selector, data in selectors['current_selectors'].items():
            if isinstance(data, dict) and data.get('count', 0) > 0:
                selectors['best_selectors'].append({
                    'selector': selector,
                    'count': data['count'],
                    'type': 'current_css'
                })
        
        for selector, data in selectors['alternative_selectors'].items():
            if isinstance(data, dict) and data.get('count', 0) > 0:
                selectors['best_selectors'].append({
                    'selector': selector,
                    'count': data['count'],
                    'type': 'alternative'
                })
        
        # Sort by count
        selectors['best_selectors'].sort(key=lambda x: x['count'], reverse=True)
        
        return selectors
    
    def _analyze_page_structure(self) -> Dict[str, Any]:
        """Analyze the overall page structure."""
        structure = {
            'sections': [],
            'main_content_areas': [],
            'navigation_elements': [],
            'form_elements': [],
            'iframe_elements': []
        }
        
        try:
            # Find sections
            sections = self.driver.find_elements(By.TAG_NAME, "section")
            for i, section in enumerate(sections):
                section_info = {
                    'index': i,
                    'id': section.get_attribute('id'),
                    'class': section.get_attribute('class'),
                    'text_content': section.text[:100] + "..." if len(section.text) > 100 else section.text,
                    'child_elements': len(section.find_elements(By.XPATH, ".//*"))
                }
                structure['sections'].append(section_info)
            
            # Find main content areas
            main_areas = self.driver.find_elements(By.CSS_SELECTOR, "main, [role='main'], .main, #main")
            for area in main_areas:
                area_info = {
                    'tag': area.tag_name,
                    'id': area.get_attribute('id'),
                    'class': area.get_attribute('class'),
                    'text_content': area.text[:100] + "..." if len(area.text) > 100 else area.text
                }
                structure['main_content_areas'].append(area_info)
            
            # Find navigation elements
            nav_elements = self.driver.find_elements(By.CSS_SELECTOR, "nav, [role='navigation'], .nav, #nav")
            for nav in nav_elements:
                nav_info = {
                    'tag': nav.tag_name,
                    'id': nav.get_attribute('id'),
                    'class': nav.get_attribute('class')
                }
                structure['navigation_elements'].append(nav_info)
            
            # Find form elements
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            for form in forms:
                form_info = {
                    'id': form.get_attribute('id'),
                    'class': form.get_attribute('class'),
                    'action': form.get_attribute('action'),
                    'method': form.get_attribute('method')
                }
                structure['form_elements'].append(form_info)
            
            # Find iframe elements
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                iframe_info = {
                    'id': iframe.get_attribute('id'),
                    'class': iframe.get_attribute('class'),
                    'src': iframe.get_attribute('src'),
                    'name': iframe.get_attribute('name')
                }
                structure['iframe_elements'].append(iframe_info)
                
        except Exception as e:
            print(f"❌ Error analyzing page structure: {e}")
        
        return structure
    
    def _extract_element_info(self, element) -> Dict[str, Any]:
        """Extract comprehensive information about an element."""
        try:
            return {
                'tag_name': element.tag_name,
                'id': element.get_attribute('id'),
                'class': element.get_attribute('class'),
                'aria_label': element.get_attribute('aria-label'),
                'title': element.get_attribute('title'),
                'href': element.get_attribute('href'),
                'text_content': element.text[:50] + "..." if len(element.text) > 50 else element.text,
                'role': element.get_attribute('role'),
                'data_testid': element.get_attribute('data-testid'),
                'is_displayed': element.is_displayed(),
                'is_enabled': element.is_enabled(),
                'location': element.location,
                'size': element.size
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # Attachment selector recommendations
        best_attachment_selectors = analysis['attachment_selectors']['best_selectors']
        if best_attachment_selectors:
            top_selector = best_attachment_selectors[0]
            recommendations.append(f"Best attachment selector: {top_selector['selector']} (found {top_selector['count']} elements)")
        else:
            recommendations.append("No attachment selectors found - may need to update selectors")
        
        # Supplier selector recommendations
        best_supplier_selectors = analysis['supplier_selectors']['best_selectors']
        if best_supplier_selectors:
            top_supplier_selector = best_supplier_selectors[0]
            recommendations.append(f"Best supplier selector: {top_supplier_selector['selector']} (found {top_supplier_selector['count']} elements)")
        else:
            recommendations.append("No supplier selectors found - may need to update selectors")
        
        # Page structure recommendations
        if analysis['page_structure']['sections']:
            recommendations.append(f"Page has {len(analysis['page_structure']['sections'])} sections - good for targeted element selection")
        
        if analysis['page_structure']['iframe_elements']:
            recommendations.append(f"Page contains {len(analysis['page_structure']['iframe_elements'])} iframes - may need to switch contexts")
        
        # Element count recommendations
        total_elements = analysis['elements_found']['total_elements']
        if total_elements > 1000:
            recommendations.append("Page has many elements - consider more specific selectors for performance")
        elif total_elements < 100:
            recommendations.append("Page has few elements - may be a loading issue or different page structure")
        
        return recommendations


class TestDOMAnalysis:
    """Test DOM analysis functionality."""
    
    @pytest.fixture
    def edge_driver(self):
        """Create Edge WebDriver for testing."""
        try:
            options = EdgeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Set download preferences
            prefs = {
                "download.default_directory": tempfile.gettempdir(),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
            }
            options.add_experimental_option("prefs", prefs)
            
            driver = webdriver.Edge(options=options)
            driver.set_page_load_timeout(30)
            
            yield driver
            
        except Exception as e:
            pytest.skip(f"Edge WebDriver not available: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()
    
    def test_dom_analysis_basic(self, edge_driver):
        """Test basic DOM analysis functionality."""
        analyzer = DOMAnalyzer(edge_driver)
        
        # Test with a simple page first
        test_url = "https://httpbin.org/html"
        analysis = analyzer.analyze_page_structure(test_url)
        
        assert 'url' in analysis
        assert 'timestamp' in analysis
        assert 'page_title' in analysis
        assert 'elements_found' in analysis
        assert 'attachment_selectors' in analysis
        assert 'supplier_selectors' in analysis
        assert 'page_structure' in analysis
        assert 'recommendations' in analysis
        
        print(f"\n✅ Basic DOM analysis completed for {test_url}")
        print(f"Page title: {analysis['page_title']}")
        print(f"Total elements: {analysis['elements_found']['total_elements']}")
        print(f"Recommendations: {len(analysis['recommendations'])}")
    
    def test_attachment_selector_analysis(self, edge_driver):
        """Test attachment selector analysis."""
        analyzer = DOMAnalyzer(edge_driver)
        
        # Test with a page that might have attachments
        test_url = "https://httpbin.org/forms/post"
        analysis = analyzer.analyze_page_structure(test_url)
        
        attachment_selectors = analysis['attachment_selectors']
        
        assert 'current_selectors' in attachment_selectors
        assert 'alternative_selectors' in attachment_selectors
        assert 'best_selectors' in attachment_selectors
        
        print(f"\n📎 Attachment Selector Analysis:")
        print(f"Current selectors tested: {len(attachment_selectors['current_selectors'])}")
        print(f"Alternative selectors tested: {len(attachment_selectors['alternative_selectors'])}")
        print(f"Best selectors found: {len(attachment_selectors['best_selectors'])}")
        
        if attachment_selectors['best_selectors']:
            best = attachment_selectors['best_selectors'][0]
            print(f"Top selector: {best['selector']} ({best['count']} elements)")
    
    def test_supplier_selector_analysis(self, edge_driver):
        """Test supplier selector analysis."""
        analyzer = DOMAnalyzer(edge_driver)
        
        # Test with a page that might have supplier information
        test_url = "https://httpbin.org/forms/post"
        analysis = analyzer.analyze_page_structure(test_url)
        
        supplier_selectors = analysis['supplier_selectors']
        
        assert 'current_selectors' in supplier_selectors
        assert 'alternative_selectors' in supplier_selectors
        assert 'best_selectors' in supplier_selectors
        
        print(f"\n🏢 Supplier Selector Analysis:")
        print(f"Current selectors tested: {len(supplier_selectors['current_selectors'])}")
        print(f"Alternative selectors tested: {len(supplier_selectors['alternative_selectors'])}")
        print(f"Best selectors found: {len(supplier_selectors['best_selectors'])}")
        
        if supplier_selectors['best_selectors']:
            best = supplier_selectors['best_selectors'][0]
            print(f"Top selector: {best['selector']} ({best['count']} elements)")
    
    def test_page_structure_analysis(self, edge_driver):
        """Test page structure analysis."""
        analyzer = DOMAnalyzer(edge_driver)
        
        test_url = "https://httpbin.org/html"
        analysis = analyzer.analyze_page_structure(test_url)
        
        page_structure = analysis['page_structure']
        
        assert 'sections' in page_structure
        assert 'main_content_areas' in page_structure
        assert 'navigation_elements' in page_structure
        assert 'form_elements' in page_structure
        assert 'iframe_elements' in page_structure
        
        print(f"\n🏗️ Page Structure Analysis:")
        print(f"Sections: {len(page_structure['sections'])}")
        print(f"Main content areas: {len(page_structure['main_content_areas'])}")
        print(f"Navigation elements: {len(page_structure['navigation_elements'])}")
        print(f"Form elements: {len(page_structure['form_elements'])}")
        print(f"Iframe elements: {len(page_structure['iframe_elements'])}")
    
    def test_element_extraction(self, edge_driver):
        """Test element information extraction."""
        analyzer = DOMAnalyzer(edge_driver)
        
        test_url = "https://httpbin.org/html"
        edge_driver.get(test_url)
        
        # Find a simple element
        element = edge_driver.find_element(By.TAG_NAME, "h1")
        element_info = analyzer._extract_element_info(element)
        
        assert 'tag_name' in element_info
        assert 'text_content' in element_info
        assert 'is_displayed' in element_info
        assert 'is_enabled' in element_info
        
        print(f"\n🔍 Element Extraction Test:")
        print(f"Tag: {element_info['tag_name']}")
        print(f"Text: {element_info['text_content']}")
        print(f"Displayed: {element_info['is_displayed']}")
        print(f"Enabled: {element_info['is_enabled']}")


class TestCoupaPageAnalysis:
    """Test analysis of actual Coupa pages."""
    
    @pytest.fixture
    def coupa_driver(self):
        """Create Edge WebDriver configured for Coupa."""
        try:
            options = EdgeOptions()
            
            # Use existing profile if available
            edge_profile_dir = os.path.expanduser("~/Library/Application Support/Microsoft Edge")
            if os.path.exists(edge_profile_dir):
                options.add_argument(f"--user-data-dir={edge_profile_dir}")
                options.add_argument("--profile-directory=Default")
            
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
            
            yield driver, download_dir
            
        except Exception as e:
            pytest.skip(f"Edge WebDriver not available: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()
    
    def test_coupa_login_page_analysis(self, coupa_driver):
        """Test analysis of Coupa login page."""
        driver, download_dir = coupa_driver
        analyzer = DOMAnalyzer(driver)
        
        # Analyze Coupa login page
        login_url = "https://unilever.coupahost.com/login"
        analysis = analyzer.analyze_page_structure(login_url)
        
        print(f"\n🔐 Coupa Login Page Analysis:")
        print(f"Page title: {analysis['page_title']}")
        print(f"Current URL: {analysis['current_url']}")
        print(f"Total elements: {analysis['elements_found']['total_elements']}")
        print(f"Form elements: {len(analysis['page_structure']['form_elements'])}")
        print(f"Recommendations: {analysis['recommendations']}")
        
        # Save analysis to file
        analysis_file = os.path.join(download_dir, "coupa_login_analysis.json")
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print(f"Analysis saved to: {analysis_file}")
    
    def test_coupa_po_page_analysis(self, coupa_driver):
        """Test analysis of a Coupa PO page (if accessible)."""
        driver, download_dir = coupa_driver
        analyzer = DOMAnalyzer(driver)
        
        # Try to analyze a PO page (this might require login)
        po_url = "https://unilever.coupahost.com/order_headers/15826591"
        analysis = analyzer.analyze_page_structure(po_url)
        
        print(f"\n📋 Coupa PO Page Analysis:")
        print(f"Page title: {analysis['page_title']}")
        print(f"Current URL: {analysis['current_url']}")
        
        if 'error' not in analysis:
            print(f"Total elements: {analysis['elements_found']['total_elements']}")
            print(f"Attachment-like elements: {len(analysis['elements_found']['attachment_like_elements'])}")
            print(f"Download-like elements: {len(analysis['elements_found']['download_like_elements'])}")
            print(f"File-like elements: {len(analysis['elements_found']['file_like_elements'])}")
            
            # Check for attachments
            best_attachments = analysis['attachment_selectors']['best_selectors']
            if best_attachments:
                print(f"Best attachment selector: {best_attachments[0]['selector']}")
                print(f"Found {best_attachments[0]['count']} attachment elements")
            
            # Check for supplier info
            best_suppliers = analysis['supplier_selectors']['best_selectors']
            if best_suppliers:
                print(f"Best supplier selector: {best_suppliers[0]['selector']}")
                print(f"Found {best_suppliers[0]['count']} supplier elements")
            
            print(f"Recommendations: {analysis['recommendations']}")
            
            # Save analysis to file
            analysis_file = os.path.join(download_dir, "coupa_po_analysis.json")
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            
            print(f"Analysis saved to: {analysis_file}")
        else:
            print(f"Error accessing PO page: {analysis['error']}")
    
    def test_attachment_element_interaction(self, coupa_driver):
        """Test interaction with attachment elements."""
        driver, download_dir = coupa_driver
        analyzer = DOMAnalyzer(driver)
        
        # Try to access a PO page
        po_url = "https://unilever.coupahost.com/order_headers/15826591"
        analysis = analyzer.analyze_page_structure(po_url)
        
        if 'error' not in analysis:
            best_attachments = analysis['attachment_selectors']['best_selectors']
            
            if best_attachments:
                top_selector = best_attachments[0]['selector']
                print(f"\n🖱️ Testing interaction with selector: {top_selector}")
                
                try:
                    # Find attachment elements
                    attachment_elements = driver.find_elements(By.CSS_SELECTOR, top_selector)
                    
                    if attachment_elements:
                        print(f"Found {len(attachment_elements)} attachment elements")
                        
                        # Test interaction with first element
                        first_element = attachment_elements[0]
                        element_info = analyzer._extract_element_info(first_element)
                        
                        print(f"First element info:")
                        print(f"  Tag: {element_info['tag_name']}")
                        print(f"  Aria-label: {element_info['aria_label']}")
                        print(f"  Title: {element_info['title']}")
                        print(f"  Text: {element_info['text_content']}")
                        print(f"  Displayed: {element_info['is_displayed']}")
                        print(f"  Enabled: {element_info['is_enabled']}")
                        
                        # Test if element is clickable
                        if element_info['is_displayed'] and element_info['is_enabled']:
                            print("✅ Element appears to be clickable")
                        else:
                            print("❌ Element is not clickable")
                    else:
                        print("No attachment elements found with this selector")
                        
                except Exception as e:
                    print(f"❌ Error testing attachment interaction: {e}")
            else:
                print("No attachment selectors found")
        else:
            print(f"Cannot test attachment interaction: {analysis['error']}")


class TestDownloadStrategyAnalysis:
    """Test analysis of different download strategies."""
    
    def test_selector_performance_comparison(self, edge_driver):
        """Compare performance of different selectors."""
        analyzer = DOMAnalyzer(edge_driver)
        
        test_url = "https://httpbin.org/html"
        analysis = analyzer.analyze_page_structure(test_url)
        
        # Compare selector performance
        attachment_selectors = analysis['attachment_selectors']
        supplier_selectors = analysis['supplier_selectors']
        
        print(f"\n⚡ Selector Performance Comparison:")
        
        # Attachment selectors
        print(f"\n📎 Attachment Selectors:")
        for selector_data in attachment_selectors['best_selectors'][:5]:
            print(f"  {selector_data['selector']}: {selector_data['count']} elements")
        
        # Supplier selectors
        print(f"\n🏢 Supplier Selectors:")
        for selector_data in supplier_selectors['best_selectors'][:5]:
            print(f"  {selector_data['selector']}: {selector_data['count']} elements")
    
    def test_download_strategy_recommendations(self, edge_driver):
        """Generate download strategy recommendations."""
        analyzer = DOMAnalyzer(edge_driver)
        
        test_url = "https://httpbin.org/html"
        analysis = analyzer.analyze_page_structure(test_url)
        
        print(f"\n🎯 Download Strategy Recommendations:")
        
        # Analyze recommendations
        for i, recommendation in enumerate(analysis['recommendations'], 1):
            print(f"  {i}. {recommendation}")
        
        # Generate additional recommendations
        elements_found = analysis['elements_found']
        
        if elements_found['attachment_like_elements']:
            print(f"\n📎 Attachment Strategy:")
            print(f"  - Found {len(elements_found['attachment_like_elements'])} attachment-like elements")
            print(f"  - Use aria-label or title attributes for identification")
            print(f"  - Consider role='button' elements for clicking")
        
        if elements_found['download_like_elements']:
            print(f"\n⬇️ Download Strategy:")
            print(f"  - Found {len(elements_found['download_like_elements'])} download-like elements")
            print(f"  - Use href attributes for direct download links")
            print(f"  - Consider button elements for download actions")
        
        if elements_found['file_like_elements']:
            print(f"\n📄 File Strategy:")
            print(f"  - Found {len(elements_found['file_like_elements'])} file-like elements")
            print(f"  - Use title attributes for file type detection")
            print(f"  - Consider href attributes for file URLs")


if __name__ == "__main__":
    # Run specific tests for manual exploration
    print("🧪 DOM Analysis Testing")
    print("=" * 50)
    
    # This would require a real browser setup
    print("Note: These tests require a real browser and may need login credentials")
    print("Run with pytest to execute the full test suite") 