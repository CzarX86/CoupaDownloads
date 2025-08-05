#!/usr/bin/env python3
"""
Test PO Sampling Functionality
Tests the intelligent PO sampling utility for analysis.
"""

import os
import sys
import pytest
import tempfile
import csv
from unittest.mock import patch, Mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.po_sampler import POSampler


class TestPOSampler:
    """Test PO sampling functionality."""
    
    @pytest.fixture
    def sample_csv_file(self):
        """Create a sample CSV file for testing."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        
        # Create sample CSV content
        sample_data = [
            {
                'PO_NUMBER': 'PO15826591',
                'STATUS': 'COMPLETED',
                'SUPPLIER': 'ERNST_AND_YOUNG_LLP-0001118312',
                'ATTACHMENTS_FOUND': '1',
                'ATTACHMENTS_DOWNLOADED': '1',
                'LAST_PROCESSED': '2025-07-28 12:45:17',
                'ERROR_MESSAGE': '',
                'DOWNLOAD_FOLDER': 'ERNST_AND_YOUNG_LLP-0001118312/',
                'COUPA_URL': 'https://unilever.coupahost.com/order_headers/15826591'
            },
            {
                'PO_NUMBER': 'PO15873456',
                'STATUS': 'COMPLETED',
                'SUPPLIER': 'ERNST_AND_YOUNG_LLP-0001118312',
                'ATTACHMENTS_FOUND': '1',
                'ATTACHMENTS_DOWNLOADED': '1',
                'LAST_PROCESSED': '2025-07-28 12:45:25',
                'ERROR_MESSAGE': '',
                'DOWNLOAD_FOLDER': 'ERNST_AND_YOUNG_LLP-0001118312/',
                'COUPA_URL': 'https://unilever.coupahost.com/order_headers/15873456'
            },
            {
                'PO_NUMBER': 'PO15873457',
                'STATUS': 'PENDING',
                'SUPPLIER': '',
                'ATTACHMENTS_FOUND': '0',
                'ATTACHMENTS_DOWNLOADED': '0',
                'LAST_PROCESSED': '',
                'ERROR_MESSAGE': '',
                'DOWNLOAD_FOLDER': '',
                'COUPA_URL': ''
            },
            {
                'PO_NUMBER': 'PO15495542',
                'STATUS': 'NO_ATTACHMENTS',
                'SUPPLIER': '',
                'ATTACHMENTS_FOUND': '0',
                'ATTACHMENTS_DOWNLOADED': '0',
                'LAST_PROCESSED': '2025-07-28 12:43:52',
                'ERROR_MESSAGE': '',
                'DOWNLOAD_FOLDER': '',
                'COUPA_URL': 'https://unilever.coupahost.com/order_headers/15495542'
            },
            {
                'PO_NUMBER': 'PO16234040',
                'STATUS': 'FAILED',
                'SUPPLIER': '',
                'ATTACHMENTS_FOUND': '0',
                'ATTACHMENTS_DOWNLOADED': '0',
                'LAST_PROCESSED': '2025-07-28 12:50:47',
                'ERROR_MESSAGE': 'PO page not found',
                'DOWNLOAD_FOLDER': '',
                'COUPA_URL': 'https://unilever.coupahost.com/order_headers/16234040'
            },
            {
                'PO_NUMBER': 'PO16165279',
                'STATUS': 'PARTIAL',
                'SUPPLIER': 'Ernst_and_Young_LLP-0000337414',
                'ATTACHMENTS_FOUND': '2',
                'ATTACHMENTS_DOWNLOADED': '1',
                'LAST_PROCESSED': '2025-07-28 12:47:47',
                'ERROR_MESSAGE': '',
                'DOWNLOAD_FOLDER': 'Ernst_and_Young_LLP-0000337414/',
                'COUPA_URL': 'https://unilever.coupahost.com/order_headers/16165279'
            }
        ]
        
        with open(temp_file.name, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sample_data[0].keys())
            writer.writeheader()
            writer.writerows(sample_data)
        
        yield temp_file.name
        
        # Cleanup
        os.unlink(temp_file.name)
    
    def test_sampler_initialization(self):
        """Test PO sampler initialization."""
        sampler = POSampler()
        assert sampler.csv_file_path is not None
        assert sampler.po_data == []
        assert sampler.sample_stats == {}
    
    def test_sampler_with_custom_csv(self, sample_csv_file):
        """Test PO sampler with custom CSV file."""
        sampler = POSampler(sample_csv_file)
        assert sampler.csv_file_path == sample_csv_file
    
    def test_load_po_data_success(self, sample_csv_file):
        """Test successful PO data loading."""
        sampler = POSampler(sample_csv_file)
        result = sampler.load_po_data()
        
        assert result is True
        assert len(sampler.po_data) == 6
        assert sampler.po_data[0]['PO_NUMBER'] == 'PO15826591'
        assert sampler.po_data[0]['STATUS'] == 'COMPLETED'
    
    def test_load_po_data_file_not_found(self):
        """Test PO data loading with non-existent file."""
        sampler = POSampler("/non/existent/file.csv")
        result = sampler.load_po_data()
        
        assert result is False
    
    def test_analyze_po_distribution(self, sample_csv_file):
        """Test PO distribution analysis."""
        sampler = POSampler(sample_csv_file)
        sampler.load_po_data()
        analysis = sampler.analyze_po_distribution()
        
        assert analysis['total_pos'] == 6
        assert analysis['status_distribution']['COMPLETED'] == 2
        assert analysis['status_distribution']['PENDING'] == 1
        assert analysis['status_distribution']['NO_ATTACHMENTS'] == 1
        assert analysis['status_distribution']['FAILED'] == 1
        assert analysis['status_distribution']['PARTIAL'] == 1
        
        # Check supplier distribution
        assert 'ERNST_AND_YOUNG_LLP-0001118312' in analysis['supplier_distribution']
        assert analysis['supplier_distribution']['ERNST_AND_YOUNG_LLP-0001118312'] == 2
        
        # Check attachment distribution
        assert analysis['attachment_distribution'][0] == 3  # 3 POs with 0 attachments
        assert analysis['attachment_distribution'][1] == 2  # 2 POs with 1 attachment
        assert analysis['attachment_distribution'][2] == 1  # 1 PO with 2 attachments
    
    def test_sample_recommendations(self, sample_csv_file):
        """Test sample size recommendations."""
        sampler = POSampler(sample_csv_file)
        sampler.load_po_data()
        analysis = sampler.analyze_po_distribution()
        
        recommendations = analysis['sample_recommendations']
        
        assert recommendations['optimal_sample_size'] > 0
        assert recommendations['confidence_level'] == 0.95
        assert recommendations['margin_of_error'] == 0.05
        
        # Check stratified sampling
        stratified = recommendations['stratified_sampling']
        assert stratified['COMPLETED'] > 0
        assert stratified['PENDING'] > 0
        assert stratified['NO_ATTACHMENTS'] > 0
        assert stratified['FAILED'] > 0
        assert stratified['PARTIAL'] > 0
    
    def test_select_optimal_sample(self, sample_csv_file):
        """Test optimal sample selection."""
        sampler = POSampler(sample_csv_file)
        sampler.load_po_data()
        
        selected_pos = sampler.select_optimal_sample()
        
        assert len(selected_pos) > 0
        assert len(selected_pos) <= 6  # Should not exceed total POs
        assert all(po.startswith('PO') for po in selected_pos)
        
        # Check that we have representatives from different statuses
        po_details = sampler.get_po_details(selected_pos)
        statuses = [detail['status'] for detail in po_details]
        
        # Should have at least 2 different statuses
        assert len(set(statuses)) >= 2
    
    def test_select_optimal_sample_with_size(self, sample_csv_file):
        """Test sample selection with specific size."""
        sampler = POSampler(sample_csv_file)
        sampler.load_po_data()
        
        selected_pos = sampler.select_optimal_sample(sample_size=3)
        
        assert len(selected_pos) == 3
        assert all(po.startswith('PO') for po in selected_pos)
    
    def test_stratified_sampling(self, sample_csv_file):
        """Test stratified sampling functionality."""
        sampler = POSampler(sample_csv_file)
        sampler.load_po_data()
        
        # Use stratified sampling
        selected_pos = sampler.select_optimal_sample(stratified=True)
        
        assert len(selected_pos) > 0
        
        # Check that we have representatives from different statuses
        po_details = sampler.get_po_details(selected_pos)
        statuses = [detail['status'] for detail in po_details]
        
        # Should have multiple statuses represented
        assert len(set(statuses)) >= 2
    
    def test_random_sampling(self, sample_csv_file):
        """Test random sampling functionality."""
        sampler = POSampler(sample_csv_file)
        sampler.load_po_data()
        
        # Use random sampling
        selected_pos = sampler.select_optimal_sample(stratified=False)
        
        assert len(selected_pos) > 0
        assert all(po.startswith('PO') for po in selected_pos)
    
    def test_get_po_details(self, sample_csv_file):
        """Test getting detailed PO information."""
        sampler = POSampler(sample_csv_file)
        sampler.load_po_data()
        
        po_numbers = ['PO15826591', 'PO15873456']
        po_details = sampler.get_po_details(po_numbers)
        
        assert len(po_details) == 2
        
        # Check first PO details
        po1 = po_details[0]
        assert po1['po_number'] == 'PO15826591'
        assert po1['status'] == 'COMPLETED'
        assert po1['supplier'] == 'ERNST_AND_YOUNG_LLP-0001118312'
        assert po1['attachments_found'] == 1
        assert po1['attachments_downloaded'] == 1
        assert 'unilever.coupahost.com' in po1['coupa_url']
    
    def test_get_po_details_not_found(self, sample_csv_file):
        """Test getting details for non-existent PO."""
        sampler = POSampler(sample_csv_file)
        sampler.load_po_data()
        
        po_numbers = ['PO99999999']  # Non-existent PO
        po_details = sampler.get_po_details(po_numbers)
        
        assert len(po_details) == 0
    
    def test_export_sample_to_csv(self, sample_csv_file):
        """Test exporting sample to CSV."""
        sampler = POSampler(sample_csv_file)
        sampler.load_po_data()
        
        selected_pos = sampler.select_optimal_sample(sample_size=3)
        output_file = sampler.export_sample_to_csv(selected_pos)
        
        assert output_file is not None
        assert os.path.exists(output_file)
        
        # Verify exported file
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            exported_data = list(reader)
        
        assert len(exported_data) == 3
        assert 'po_number' in exported_data[0]
        assert 'status' in exported_data[0]
        assert 'supplier' in exported_data[0]
        
        # Cleanup
        os.unlink(output_file)
    
    def test_empty_data_handling(self):
        """Test handling of empty data."""
        sampler = POSampler()
        
        # Test analysis without data
        analysis = sampler.analyze_po_distribution()
        assert analysis == {}
        
        # Test sample selection without data
        selected_pos = sampler.select_optimal_sample()
        assert selected_pos == []
    
    def test_statistical_sampling_calculation(self, sample_csv_file):
        """Test statistical sampling calculations."""
        sampler = POSampler(sample_csv_file)
        sampler.load_po_data()
        analysis = sampler.analyze_po_distribution()
        
        recommendations = analysis['sample_recommendations']
        
        # Test that sample size is reasonable
        total_pos = analysis['total_pos']
        optimal_size = recommendations['optimal_sample_size']
        
        assert optimal_size >= 1
        assert optimal_size <= total_pos
        assert optimal_size <= 50  # Should be capped at 50
    
    def test_sampling_with_large_dataset(self):
        """Test sampling with a large simulated dataset."""
        # Create a large temporary CSV
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        
        with open(temp_file.name, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['PO_NUMBER', 'STATUS', 'SUPPLIER', 'ATTACHMENTS_FOUND', 
                           'ATTACHMENTS_DOWNLOADED', 'LAST_PROCESSED', 'ERROR_MESSAGE', 
                           'DOWNLOAD_FOLDER', 'COUPA_URL'])
            
            # Create 1000 POs
            for i in range(1000):
                po_num = f'PO{15826591 + i}'
                status = 'COMPLETED' if i % 3 == 0 else 'PENDING' if i % 3 == 1 else 'FAILED'
                writer.writerow([po_num, status, f'Supplier_{i % 10}', '1', '1', 
                               '2025-07-28 12:00:00', '', f'Supplier_{i % 10}/', 
                               f'https://unilever.coupahost.com/order_headers/{15826591 + i}'])
        
        try:
            sampler = POSampler(temp_file.name)
            sampler.load_po_data()
            
            analysis = sampler.analyze_po_distribution()
            assert analysis['total_pos'] == 1000
            
            selected_pos = sampler.select_optimal_sample()
            # Should select a reasonable sample size (not too large)
            assert len(selected_pos) <= 50
            assert len(selected_pos) >= 10
            
        finally:
            os.unlink(temp_file.name)


def test_integration_with_analysis():
    """Test integration with analysis tools."""
    # This test would require the actual analysis tools to be available
    # For now, we'll just test that the sampler can be imported and used
    try:
        from tests.po_sampler import POSampler
        sampler = POSampler()
        assert sampler is not None
    except ImportError:
        pytest.skip("Analysis tools not available")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"]) 