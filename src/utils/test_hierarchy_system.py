"""
Comprehensive test for the enhanced folder hierarchy system.
Tests all aspects of the new folder organization feature.
"""

import os
import pandas as pd
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock
import sys

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.folder_hierarchy import FolderHierarchyManager
from core.excel_processor import ExcelProcessor
from core.config import Config


class TestFolderHierarchySystem(unittest.TestCase):
    """Comprehensive test suite for folder hierarchy system."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="hierarchy_test_")
        self.original_download_folder = Config.DOWNLOAD_FOLDER
        Config.DOWNLOAD_FOLDER = self.temp_dir
        self.hierarchy_manager = FolderHierarchyManager()
        self.excel_processor = ExcelProcessor()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
        Config.DOWNLOAD_FOLDER = self.original_download_folder
    
    def test_hierarchy_manager_creation(self):
        """Test FolderHierarchyManager initialization."""
        self.assertIsNotNone(self.hierarchy_manager)
        self.assertTrue(self.hierarchy_manager.hierarchy_enabled)
        self.assertEqual(self.hierarchy_manager.separator_column, "<|>")
    
    def test_excel_structure_analysis_with_hierarchy(self):
        """Test Excel structure analysis with hierarchy columns."""
        # Create test DataFrame with hierarchy
        test_data = {
            'PO_NUMBER': ['PO123456', 'PO789012'],
            'STATUS': ['PENDING', 'PENDING'],
            'SUPPLIER': ['Microsoft', 'Apple'],
            '<|>': ['', ''],
            'Priority': ['High', 'Medium'],
            'Category': ['Technology', 'Hardware'],
            'Region': ['US', 'EU']
        }
        df = pd.DataFrame(test_data)
        
        # Analyze structure
        original_cols, hierarchy_cols, has_hierarchy_data = self.hierarchy_manager.analyze_excel_structure(df)
        
        # Verify results
        self.assertEqual(original_cols, ['PO_NUMBER', 'STATUS', 'SUPPLIER'])
        self.assertEqual(hierarchy_cols, ['Priority', 'Category', 'Region'])
        self.assertTrue(has_hierarchy_data)
    
    def test_excel_structure_analysis_without_hierarchy(self):
        """Test Excel structure analysis without hierarchy columns."""
        # Create test DataFrame without hierarchy
        test_data = {
            'PO_NUMBER': ['PO123456', 'PO789012'],
            'STATUS': ['PENDING', 'PENDING'],
            'SUPPLIER': ['Microsoft', 'Apple']
        }
        df = pd.DataFrame(test_data)
        
        # Analyze structure
        original_cols, hierarchy_cols, has_hierarchy_data = self.hierarchy_manager.analyze_excel_structure(df)
        
        # Verify results
        self.assertEqual(original_cols, ['PO_NUMBER', 'STATUS', 'SUPPLIER'])
        self.assertEqual(hierarchy_cols, [])
        self.assertFalse(has_hierarchy_data)
    
    def test_excel_structure_analysis_with_empty_hierarchy(self):
        """Test Excel structure analysis with empty hierarchy columns."""
        # Create test DataFrame with empty hierarchy
        test_data = {
            'PO_NUMBER': ['PO123456', 'PO789012'],
            'STATUS': ['PENDING', 'PENDING'],
            'SUPPLIER': ['Microsoft', 'Apple'],
            '<|>': ['', ''],
            'Priority': ['', ''],
            'Category': ['', '']
        }
        df = pd.DataFrame(test_data)
        
        # Analyze structure
        original_cols, hierarchy_cols, has_hierarchy_data = self.hierarchy_manager.analyze_excel_structure(df)
        
        # Verify results
        self.assertEqual(original_cols, ['PO_NUMBER', 'STATUS', 'SUPPLIER'])
        self.assertEqual(hierarchy_cols, ['Priority', 'Category'])
        self.assertFalse(has_hierarchy_data)
    
    def test_hierarchy_folder_creation(self):
        """Test hierarchical folder creation."""
        po_data = {
            'po_number': 'PO123456',
            'status': 'PENDING',
            'Priority': 'High',
            'Category': 'Technology',
            'Region': 'US'
        }
        hierarchy_cols = ['Priority', 'Category', 'Region']
        
        folder_path = self.hierarchy_manager.create_folder_path(
            po_data, hierarchy_cols, True
        )
        
        # Verify folder was created
        self.assertTrue(os.path.exists(folder_path))
        
        # Verify path structure
        expected_path = os.path.join(
            self.temp_dir,
            'High',
            'Technology',
            'US',
            'PO123456'
        )
        self.assertEqual(folder_path, expected_path)
    
    def test_fallback_folder_creation(self):
        """Test fallback folder creation."""
        po_data = {
            'po_number': 'PO123456',
            'status': 'PENDING',
            'supplier': 'Microsoft'
        }
        hierarchy_cols = []
        
        folder_path = self.hierarchy_manager.create_folder_path(
            po_data, hierarchy_cols, False, 'Microsoft'
        )
        
        # Verify folder was created
        self.assertTrue(os.path.exists(folder_path))
        
        # Verify path structure
        expected_path = os.path.join(
            self.temp_dir,
            'Microsoft',
            'PO123456'
        )
        self.assertEqual(folder_path, expected_path)
    
    def test_status_suffix_logic(self):
        """Test status suffix logic."""
        # Test PENDING (no suffix)
        po_data = {
            'po_number': 'PO123456',
            'status': 'PENDING',
            'Priority': 'High'
        }
        hierarchy_cols = ['Priority']
        
        folder_path = self.hierarchy_manager.create_folder_path(
            po_data, hierarchy_cols, True
        )
        
        # Should not have status suffix
        self.assertNotIn('_PENDING', folder_path)
        
        # Test FAILED (should have suffix)
        po_data['status'] = 'FAILED'
        folder_path = self.hierarchy_manager.create_folder_path(
            po_data, hierarchy_cols, True
        )
        
        # Should have status suffix
        self.assertIn('_FAILED', folder_path)
    
    def test_nan_value_handling(self):
        """Test handling of NaN values in hierarchy columns."""
        po_data = {
            'po_number': 'PO123456',
            'status': 'PENDING',
            'Priority': 'High',
            'Category': None,  # This will be NaN
            'Region': 'US'
        }
        hierarchy_cols = ['Priority', 'Category', 'Region']
        
        folder_path = self.hierarchy_manager.create_folder_path(
            po_data, hierarchy_cols, True
        )
        
        # Verify folder was created
        self.assertTrue(os.path.exists(folder_path))
        
        # Verify NaN was converted to "Unknown"
        self.assertIn('Unknown', folder_path)
    
    def test_attachment_name_formatting(self):
        """Test attachment name formatting."""
        attachment_list = [
            'PO123456_document1.pdf',
            'PO123456_specification.docx',
            'PO123456_invoice.xlsx'
        ]
        
        formatted = self.hierarchy_manager.format_attachment_names(attachment_list)
        
        # Verify formatting
        expected = 'PO123456_document1.pdf;\nPO123456_specification.docx;\nPO123456_invoice.xlsx'
        self.assertEqual(formatted, expected)
    
    def test_empty_attachment_list(self):
        """Test formatting empty attachment list."""
        formatted = self.hierarchy_manager.format_attachment_names([])
        self.assertEqual(formatted, "")
    
    def test_folder_name_cleaning(self):
        """Test folder name cleaning."""
        test_cases = [
            ('Microsoft Corp', 'Microsoft_Corp'),
            ('High Priority', 'High_Priority'),
            ('Tech/Software', 'Tech_Software'),
            ('Company & Co.', 'Company___Co'),
            ('Very Long Company Name That Exceeds Fifty Characters Limit', 'Very_Long_Company_Name_That_Exceeds_Fifty_Char'),
            ('', 'Unknown'),
            (None, 'Unknown'),
            ('nan', 'Unknown')
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = self.hierarchy_manager._clean_folder_name(input_name)
                self.assertEqual(result, expected)
    
    def test_hierarchy_summary_generation(self):
        """Test hierarchy summary generation."""
        po_data = {
            'po_number': 'PO123456',
            'status': 'PENDING',
            'Priority': 'High',
            'Category': 'Technology'
        }
        hierarchy_cols = ['Priority', 'Category']
        
        summary = self.hierarchy_manager.get_hierarchy_summary(po_data, hierarchy_cols, True)
        
        self.assertEqual(summary['structure_type'], 'hierarchy')
        self.assertEqual(summary['hierarchy_path'], 'High/Technology')
        self.assertEqual(summary['po_number'], 'PO123456')
        self.assertEqual(summary['status'], 'PENDING')
    
    def test_fallback_summary_generation(self):
        """Test fallback summary generation."""
        po_data = {
            'po_number': 'PO123456',
            'status': 'PENDING',
            'supplier': 'Microsoft'
        }
        hierarchy_cols = []
        
        summary = self.hierarchy_manager.get_hierarchy_summary(po_data, hierarchy_cols, False)
        
        self.assertEqual(summary['structure_type'], 'fallback')
        self.assertEqual(summary['supplier'], 'Microsoft')
        self.assertEqual(summary['po_number'], 'PO123456')
        self.assertEqual(summary['status'], 'PENDING')
    
    def test_error_handling_in_folder_creation(self):
        """Test error handling in folder creation."""
        # Test with invalid folder path
        with patch('os.makedirs', side_effect=Exception("Permission denied")):
            with self.assertRaises(Exception) as context:
                po_data = {'po_number': 'PO123456', 'status': 'PENDING'}
                self.hierarchy_manager.create_folder_path(po_data, [], False, 'Microsoft')
            
            self.assertIn("Failed to create folder path", str(context.exception))


class TestExcelProcessorIntegration(unittest.TestCase):
    """Test ExcelProcessor integration with hierarchy system."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="excel_test_")
        self.test_excel_path = os.path.join(self.temp_dir, 'test_input.xlsx')
        self.excel_processor = ExcelProcessor()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_excel_reading_with_hierarchy(self):
        """Test reading Excel with hierarchy columns."""
        # Create test Excel file
        test_data = {
            'PO_NUMBER': ['PO123456', 'PO789012'],
            'STATUS': ['PENDING', 'PENDING'],
            'SUPPLIER': ['Microsoft', 'Apple'],
            '<|>': ['', ''],
            'Priority': ['High', 'Medium'],
            'Category': ['Technology', 'Hardware'],
            'AttachmentName': ['', '']
        }
        df = pd.DataFrame(test_data)
        df.to_excel(self.test_excel_path, index=False)
        
        # Read Excel file
        po_entries, original_cols, hierarchy_cols, has_hierarchy_data = self.excel_processor.read_po_numbers_from_excel(self.test_excel_path)
        
        # Verify results
        self.assertEqual(len(po_entries), 2)
        self.assertEqual(original_cols, ['PO_NUMBER', 'STATUS', 'SUPPLIER'])
        self.assertEqual(hierarchy_cols, ['Priority', 'Category'])
        self.assertTrue(has_hierarchy_data)
        
        # Verify PO data
        self.assertEqual(po_entries[0]['po_number'], 'PO123456')
        self.assertEqual(po_entries[0]['Priority'], 'High')
        self.assertEqual(po_entries[0]['Category'], 'Technology')
    
    def test_excel_reading_without_hierarchy(self):
        """Test reading Excel without hierarchy columns."""
        # Create test Excel file without hierarchy
        test_data = {
            'PO_NUMBER': ['PO123456', 'PO789012'],
            'STATUS': ['PENDING', 'PENDING'],
            'SUPPLIER': ['Microsoft', 'Apple'],
            'AttachmentName': ['', '']
        }
        df = pd.DataFrame(test_data)
        df.to_excel(self.test_excel_path, index=False)
        
        # Read Excel file
        po_entries, original_cols, hierarchy_cols, has_hierarchy_data = self.excel_processor.read_po_numbers_from_excel(self.test_excel_path)
        
        # Verify results
        self.assertEqual(len(po_entries), 2)
        self.assertEqual(original_cols, ['PO_NUMBER', 'STATUS', 'SUPPLIER'])
        self.assertEqual(hierarchy_cols, [])
        self.assertFalse(has_hierarchy_data)
    
    def test_excel_writing_with_hierarchy(self):
        """Test writing Excel with hierarchy columns."""
        # Create test data
        po_entries = [
            {
                'po_number': 'PO123456',
                'status': 'PENDING',
                'supplier': 'Microsoft',
                'Priority': 'High',
                'Category': 'Technology',
                'attachment_names': 'file1.pdf;\nfile2.docx'
            }
        ]
        original_cols = ['PO_NUMBER', 'STATUS', 'SUPPLIER']
        hierarchy_cols = ['Priority', 'Category']
        
        # Write Excel file
        self.excel_processor.write_enhanced_excel(self.test_excel_path, po_entries, original_cols, hierarchy_cols)
        
        # Verify file was created
        self.assertTrue(os.path.exists(self.test_excel_path))
        
        # Read back and verify
        df = pd.read_excel(self.test_excel_path)
        self.assertIn('PO_NUMBER', df.columns)
        self.assertIn('STATUS', df.columns)
        self.assertIn('SUPPLIER', df.columns)
        self.assertIn('<|>', df.columns)
        self.assertIn('Priority', df.columns)
        self.assertIn('Category', df.columns)


if __name__ == '__main__':
    unittest.main()
