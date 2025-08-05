#!/usr/bin/env python3
"""
PO Sampler Utility
Intelligently samples PO numbers from input.csv for analysis based on statistical principles.
"""

import os
import csv
import random
import math
from typing import List, Dict, Any, Tuple
from collections import Counter
import pandas as pd


class POSampler:
    """
    Smart PO sampling utility that determines optimal sample size and selects representative POs.
    """
    
    def __init__(self, csv_file_path: str = ""):
        """Initialize the PO sampler with the input CSV file."""
        if not csv_file_path:
            # Default to input.csv in the parent directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            csv_file_path = os.path.join(os.path.dirname(current_dir), "input.csv")
        
        self.csv_file_path = csv_file_path
        self.po_data = []
        self.sample_stats = {}
        
    def load_po_data(self) -> bool:
        """Load and analyze PO data from the CSV file."""
        try:
            if not os.path.exists(self.csv_file_path):
                print(f"❌ CSV file not found: {self.csv_file_path}")
                return False
            
            # Read CSV data
            with open(self.csv_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.po_data = list(reader)
            
            print(f"✅ Loaded {len(self.po_data)} PO entries from {self.csv_file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading PO data: {e}")
            return False
    
    def analyze_po_distribution(self) -> Dict[str, Any]:
        """Analyze the distribution of PO data to understand patterns."""
        if not self.po_data:
            print("❌ No PO data loaded. Call load_po_data() first.")
            return {}
        
        analysis = {
            'total_pos': len(self.po_data),
            'status_distribution': {},
            'supplier_distribution': {},
            'attachment_distribution': {},
            'url_patterns': {},
            'sample_recommendations': {}
        }
        
        # Analyze status distribution
        status_counts = Counter(row['STATUS'] for row in self.po_data)
        analysis['status_distribution'] = dict(status_counts)
        
        # Analyze supplier distribution
        supplier_counts = Counter(row['SUPPLIER'] for row in self.po_data if row['SUPPLIER'])
        analysis['supplier_distribution'] = dict(supplier_counts)
        
        # Analyze attachment distribution
        attachment_counts = Counter(int(row['ATTACHMENTS_FOUND']) for row in self.po_data)
        analysis['attachment_distribution'] = dict(attachment_counts)
        
        # Analyze URL patterns
        urls = [row['COUPA_URL'] for row in self.po_data if row['COUPA_URL']]
        if urls:
            # Extract PO numbers from URLs
            po_numbers_from_urls = []
            for url in urls:
                if '/order_headers/' in url:
                    po_num = url.split('/order_headers/')[-1]
                    po_numbers_from_urls.append(po_num)
            
            analysis['url_patterns'] = {
                'total_urls': len(urls),
                'valid_urls': len(po_numbers_from_urls),
                'sample_po_numbers': po_numbers_from_urls[:10]  # First 10 for reference
            }
        
        # Generate sample recommendations
        analysis['sample_recommendations'] = self._generate_sample_recommendations(analysis)
        
        return analysis
    
    def _generate_sample_recommendations(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendations for optimal sampling."""
        total_pos = analysis['total_pos']
        status_dist = analysis['status_distribution']
        
        recommendations = {
            'optimal_sample_size': 0,
            'confidence_level': 0.95,
            'margin_of_error': 0.05,
            'stratified_sampling': {},
            'reasoning': []
        }
        
        # Calculate optimal sample size using statistical sampling
        # Using Cochran's formula for finite population
        z_score = 1.96  # 95% confidence level
        p = 0.5  # Conservative estimate for proportion
        q = 1 - p
        e = 0.05  # 5% margin of error
        
        if total_pos > 0:
            # Cochran's formula for finite population
            n0 = (z_score ** 2 * p * q) / (e ** 2)
            optimal_size = n0 / (1 + (n0 - 1) / total_pos)
            
            # Ensure minimum sample size for meaningful analysis
            min_sample = min(10, total_pos)
            max_sample = min(50, total_pos)  # Cap at 50 for practical reasons
            
            recommendations['optimal_sample_size'] = max(min_sample, min(max_sample, int(optimal_size)))
            
            # Stratified sampling recommendations
            if status_dist:
                total_completed = status_dist.get('COMPLETED', 0)
                total_pending = status_dist.get('PENDING', 0)
                total_failed = status_dist.get('FAILED', 0)
                total_no_attachments = status_dist.get('NO_ATTACHMENTS', 0)
                total_partial = status_dist.get('PARTIAL', 0)
                
                # Calculate proportional samples for each status
                sample_size = recommendations['optimal_sample_size']
                
                recommendations['stratified_sampling'] = {
                    'COMPLETED': max(1, int((total_completed / total_pos) * sample_size)),
                    'PENDING': max(1, int((total_pending / total_pos) * sample_size)),
                    'FAILED': max(1, int((total_failed / total_pos) * sample_size)),
                    'NO_ATTACHMENTS': max(1, int((total_no_attachments / total_pos) * sample_size)),
                    'PARTIAL': max(1, int((total_partial / total_pos) * sample_size))
                }
            
            recommendations['reasoning'] = [
                f"Total POs available: {total_pos}",
                f"Optimal sample size: {recommendations['optimal_sample_size']} (95% confidence, 5% margin of error)",
                f"Sample represents {recommendations['optimal_sample_size']/total_pos*100:.1f}% of total population"
            ]
        
        return recommendations
    
    def select_optimal_sample(self, sample_size: int = 0, stratified: bool = True) -> List[str]:
        """
        Select an optimal sample of PO numbers for analysis.
        
        Args:
            sample_size: Number of POs to sample (if 0, uses calculated optimal size)
            stratified: Whether to use stratified sampling by status
        
        Returns:
            List of PO numbers to analyze
        """
        if not self.po_data:
            print("❌ No PO data loaded. Call load_po_data() first.")
            return []
        
        # Get analysis and recommendations
        analysis = self.analyze_po_distribution()
        
        if sample_size == 0:
            sample_size = analysis['sample_recommendations']['optimal_sample_size']
        
        print(f"🎯 Selecting {sample_size} POs for analysis...")
        
        if stratified and analysis['sample_recommendations']['stratified_sampling']:
            return self._stratified_sample(analysis['sample_recommendations']['stratified_sampling'], sample_size)
        else:
            return self._random_sample(sample_size)
    
    def _stratified_sample(self, stratified_counts: Dict[str, int], target_size: int = 0) -> List[str]:
        """Perform stratified sampling based on status distribution."""
        selected_pos = []
        
        for status, count in stratified_counts.items():
            if count > 0:
                # Get POs with this status
                status_pos = [row['PO_NUMBER'] for row in self.po_data if row['STATUS'] == status]
                
                if status_pos:
                    # Sample from this stratum
                    sample_count = min(count, len(status_pos))
                    stratum_sample = random.sample(status_pos, sample_count)
                    selected_pos.extend(stratum_sample)
                    
                    print(f"  📊 {status}: {sample_count}/{len(status_pos)} POs selected")
        
        # Shuffle to avoid bias
        random.shuffle(selected_pos)
        
        # If target size is specified and we have more than needed, trim the list
        if target_size > 0 and len(selected_pos) > target_size:
            selected_pos = selected_pos[:target_size]
        
        print(f"✅ Selected {len(selected_pos)} POs using stratified sampling")
        return selected_pos
    
    def _random_sample(self, sample_size: int) -> List[str]:
        """Perform simple random sampling."""
        all_pos = [row['PO_NUMBER'] for row in self.po_data]
        selected_pos = random.sample(all_pos, min(sample_size, len(all_pos)))
        
        print(f"✅ Selected {len(selected_pos)} POs using random sampling")
        return selected_pos
    
    def get_po_details(self, po_numbers: List[str]) -> List[Dict[str, Any]]:
        """Get detailed information for selected PO numbers."""
        po_details = []
        
        for po_number in po_numbers:
            # Find the PO in the data
            po_data = next((row for row in self.po_data if row['PO_NUMBER'] == po_number), None)
            
            if po_data:
                details = {
                    'po_number': po_number,
                    'status': po_data['STATUS'],
                    'supplier': po_data['SUPPLIER'],
                    'attachments_found': int(po_data['ATTACHMENTS_FOUND']),
                    'attachments_downloaded': int(po_data['ATTACHMENTS_DOWNLOADED']),
                    'coupa_url': po_data['COUPA_URL'],
                    'last_processed': po_data['LAST_PROCESSED'],
                    'error_message': po_data['ERROR_MESSAGE']
                }
                po_details.append(details)
            else:
                print(f"⚠️ PO {po_number} not found in data")
        
        return po_details
    
    def print_sampling_report(self, selected_pos: List[str] = None):
        """Print a comprehensive sampling report."""
        analysis = self.analyze_po_distribution()
        
        print("\n" + "="*80)
        print("📊 PO SAMPLING ANALYSIS REPORT")
        print("="*80)
        
        print(f"📁 Data Source: {self.csv_file_path}")
        print(f"📋 Total POs Available: {analysis['total_pos']}")
        
        # Status distribution
        print(f"\n📊 Status Distribution:")
        for status, count in analysis['status_distribution'].items():
            percentage = (count / analysis['total_pos']) * 100
            print(f"  {status}: {count} ({percentage:.1f}%)")
        
        # Supplier distribution (top 5)
        print(f"\n🏢 Top Suppliers:")
        sorted_suppliers = sorted(analysis['supplier_distribution'].items(), 
                                key=lambda x: x[1], reverse=True)[:5]
        for supplier, count in sorted_suppliers:
            print(f"  {supplier}: {count} POs")
        
        # Attachment distribution
        print(f"\n📎 Attachment Distribution:")
        for attachments, count in sorted(analysis['attachment_distribution'].items()):
            percentage = (count / analysis['total_pos']) * 100
            print(f"  {attachments} attachments: {count} POs ({percentage:.1f}%)")
        
        # Sampling recommendations
        recommendations = analysis['sample_recommendations']
        print(f"\n🎯 Sampling Recommendations:")
        for reason in recommendations['reasoning']:
            print(f"  {reason}")
        
        if recommendations['stratified_sampling']:
            print(f"\n📊 Stratified Sampling Plan:")
            for status, count in recommendations['stratified_sampling'].items():
                print(f"  {status}: {count} POs")
        
        # Selected sample
        if selected_pos:
            print(f"\n✅ Selected Sample ({len(selected_pos)} POs):")
            for i, po in enumerate(selected_pos, 1):
                print(f"  {i:2d}. {po}")
        
        print("="*80)
    
    def export_sample_to_csv(self, selected_pos: List[str], output_file: str = "") -> str:
        """Export the selected sample to a CSV file for analysis."""
        if not output_file:
            output_file = f"po_sample_{len(selected_pos)}_pos.csv"
        
        po_details = self.get_po_details(selected_pos)
        
        if po_details:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = po_details[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(po_details)
            
            print(f"📄 Sample exported to: {output_file}")
            return output_file
        else:
            print("❌ No PO details to export")
            return ""


def main():
    """Main function to demonstrate PO sampling."""
    print("🎯 PO Sampling Utility")
    print("="*50)
    
    # Create sampler
    sampler = POSampler()
    
    # Load data
    if not sampler.load_po_data():
        return
    
    # Analyze distribution
    analysis = sampler.analyze_po_distribution()
    
    # Print analysis report
    sampler.print_sampling_report()
    
    # Select optimal sample
    selected_pos = sampler.select_optimal_sample()
    
    # Print final report with selected sample
    sampler.print_sampling_report(selected_pos)
    
    # Export sample
    sampler.export_sample_to_csv(selected_pos)
    
    print("\n✅ PO sampling completed!")


if __name__ == "__main__":
    main() 