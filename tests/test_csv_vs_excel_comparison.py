"""
CSV vs Excel Comparison Testing
Comprehensive comparison to evaluate migration decision.
"""

import os
import tempfile
import time
import csv
import pytest
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Tuple


class CSVvsExcelComparison:
    """Comprehensive comparison between CSV and Excel implementations"""
    
    def __init__(self):
        self.test_data = self._generate_test_data()
    
    def _generate_test_data(self, num_records: int = 100) -> List[Dict[str, Any]]:
        """Generate test data for comparison"""
        return [
            {
                'PO_NUMBER': f'PO{15826591 + i}',
                'STATUS': 'PENDING' if i % 3 == 0 else ('COMPLETED' if i % 3 == 1 else 'FAILED'),
                'SUPPLIER': f'Supplier_{i % 10}',
                'ATTACHMENTS_FOUND': i % 5,
                'ATTACHMENTS_DOWNLOADED': i % 3,
                'LAST_PROCESSED': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ERROR_MESSAGE': f'Error {i}' if i % 7 == 0 else '',
                'DOWNLOAD_FOLDER': f'Supplier_{i % 10}/',
                'COUPA_URL': f'https://coupa.company.com/requisition_lines/{15826591 + i}'
            }
            for i in range(num_records)
        ]
    
    def test_file_size_comparison(self):
        """Compare file sizes between CSV and Excel"""
        print("\n📊 File Size Comparison")
        print("=" * 40)
        
        # Create CSV file
        with tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False) as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.test_data[0].keys())
            writer.writeheader()
            writer.writerows(self.test_data)
            csv_size = os.path.getsize(csv_file.name)
            csv_path = csv_file.name
        
        # Create Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
            df = pd.DataFrame(self.test_data)
            df.to_excel(excel_file.name, index=False)
            excel_size = os.path.getsize(excel_file.name)
            excel_path = excel_file.name
        
        # Compare sizes
        size_ratio = excel_size / csv_size
        
        print(f"CSV file size: {csv_size:,} bytes ({csv_size/1024:.1f} KB)")
        print(f"Excel file size: {excel_size:,} bytes ({excel_size/1024:.1f} KB)")
        print(f"Size ratio (Excel/CSV): {size_ratio:.2f}x")
        
        if size_ratio > 10:
            print("⚠️ Excel file is significantly larger")
        elif size_ratio > 5:
            print("⚠️ Excel file is moderately larger")
        else:
            print("✅ Excel file size is reasonable")
        
        # Cleanup
        os.unlink(csv_path)
        os.unlink(excel_path)
        
        return size_ratio
    
    def test_performance_comparison(self):
        """Compare performance between CSV and Excel operations"""
        print("\n⚡ Performance Comparison")
        print("=" * 40)
        
        results = {}
        
        # Test different dataset sizes
        for dataset_size in [10, 50, 100, 500]:
            print(f"\n📈 Testing with {dataset_size} records:")
            
            test_data = self._generate_test_data(dataset_size)
            
            # CSV Write Performance
            csv_write_start = time.time()
            with tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False) as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=test_data[0].keys())
                writer.writeheader()
                writer.writerows(test_data)
                csv_write_time = time.time() - csv_write_start
                csv_path = csv_file.name
            
            # Excel Write Performance
            excel_write_start = time.time()
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
                df = pd.DataFrame(test_data)
                df.to_excel(excel_file.name, index=False)
                excel_write_time = time.time() - excel_write_start
                excel_path = excel_file.name
            
            # CSV Read Performance
            csv_read_start = time.time()
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                csv_data = list(reader)
            csv_read_time = time.time() - csv_read_start
            
            # Excel Read Performance
            excel_read_start = time.time()
            excel_data = pd.read_excel(excel_path).to_dict('records')
            excel_read_time = time.time() - excel_read_start
            
            # Store results
            results[dataset_size] = {
                'csv_write': csv_write_time,
                'excel_write': excel_write_time,
                'csv_read': csv_read_time,
                'excel_read': excel_read_time,
                'write_ratio': excel_write_time / csv_write_time,
                'read_ratio': excel_read_time / csv_read_time
            }
            
            print(f"  Write - CSV: {csv_write_time:.4f}s, Excel: {excel_write_time:.4f}s (ratio: {results[dataset_size]['write_ratio']:.2f}x)")
            print(f"  Read  - CSV: {csv_read_time:.4f}s, Excel: {excel_read_time:.4f}s (ratio: {results[dataset_size]['read_ratio']:.2f}x)")
            
            # Cleanup
            os.unlink(csv_path)
            os.unlink(excel_path)
        
        # Analyze trends
        avg_write_ratio = sum(r['write_ratio'] for r in results.values()) / len(results)
        avg_read_ratio = sum(r['read_ratio'] for r in results.values()) / len(results)
        
        print(f"\n📊 Average Performance Ratios:")
        print(f"  Write: Excel is {avg_write_ratio:.2f}x slower than CSV")
        print(f"  Read:  Excel is {avg_read_ratio:.2f}x slower than CSV")
        
        return results
    
    def test_functionality_comparison(self):
        """Compare functionality features between CSV and Excel"""
        print("\n🔧 Functionality Comparison")
        print("=" * 40)
        
        features = {
            'Multiple Sheets': {'csv': False, 'excel': True},
            'Formatting': {'csv': False, 'excel': True},
            'Conditional Formatting': {'csv': False, 'excel': True},
            'Data Validation': {'csv': False, 'excel': True},
            'Charts/Graphs': {'csv': False, 'excel': True},
            'Cell Protection': {'csv': False, 'excel': True},
            'Native Excel Compatibility': {'csv': False, 'excel': True},
            'Text Editor Compatibility': {'csv': True, 'excel': False},
            'Version Control Friendly': {'csv': True, 'excel': False},
            'Cross-Platform Compatibility': {'csv': True, 'excel': True},
            'File Size Efficiency': {'csv': True, 'excel': False},
            'Processing Speed': {'csv': True, 'excel': False},
            'Dependency Requirements': {'csv': False, 'excel': True},
            'Error Recovery': {'csv': True, 'excel': False},
            'Manual Editing Ease': {'csv': False, 'excel': True}
        }
        
        csv_score = 0
        excel_score = 0
        
        for feature, support in features.items():
            if support['csv']:
                csv_score += 1
            if support['excel']:
                excel_score += 1
            
            status_csv = "✅" if support['csv'] else "❌"
            status_excel = "✅" if support['excel'] else "❌"
            print(f"{feature:<25} CSV: {status_csv}  Excel: {status_excel}")
        
        total_features = len(features)
        csv_percentage = (csv_score / total_features) * 100
        excel_percentage = (excel_score / total_features) * 100
        
        print(f"\n📊 Feature Support Summary:")
        print(f"CSV:  {csv_score}/{total_features} features ({csv_percentage:.1f}%)")
        print(f"Excel: {excel_score}/{total_features} features ({excel_percentage:.1f}%)")
        
        return {
            'csv_score': csv_score,
            'excel_score': excel_score,
            'total_features': total_features
        }
    
    def test_memory_usage_comparison(self):
        """Compare memory usage between CSV and Excel operations"""
        print("\n💾 Memory Usage Comparison")
        print("=" * 40)
        
        try:
            import psutil
            import gc
            
            process = psutil.Process()
            
            # Test with larger dataset
            test_data = self._generate_test_data(1000)
            
            # CSV Memory Test
            gc.collect()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            with tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False) as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=test_data[0].keys())
                writer.writeheader()
                writer.writerows(test_data)
                
                csv_peak_memory = process.memory_info().rss / 1024 / 1024  # MB
                csv_path = csv_file.name
            
            # Read CSV
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                csv_data = list(reader)
            
            csv_read_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Excel Memory Test
            gc.collect()
            excel_initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
                df = pd.DataFrame(test_data)
                df.to_excel(excel_file.name, index=False)
                
                excel_peak_memory = process.memory_info().rss / 1024 / 1024  # MB
                excel_path = excel_file.name
            
            # Read Excel
            excel_data = pd.read_excel(excel_path).to_dict('records')
            excel_read_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            print(f"Initial memory: {initial_memory:.2f} MB")
            print(f"\nCSV Operations:")
            print(f"  Write peak: {csv_peak_memory:.2f} MB (+{csv_peak_memory - initial_memory:.2f} MB)")
            print(f"  Read peak:  {csv_read_memory:.2f} MB (+{csv_read_memory - initial_memory:.2f} MB)")
            
            print(f"\nExcel Operations:")
            print(f"  Write peak: {excel_peak_memory:.2f} MB (+{excel_peak_memory - excel_initial_memory:.2f} MB)")
            print(f"  Read peak:  {excel_read_memory:.2f} MB (+{excel_read_memory - excel_initial_memory:.2f} MB)")
            
            # Cleanup
            os.unlink(csv_path)
            os.unlink(excel_path)
            del csv_data, excel_data, df
            gc.collect()
            
            return {
                'csv_write_memory': csv_peak_memory - initial_memory,
                'csv_read_memory': csv_read_memory - initial_memory,
                'excel_write_memory': excel_peak_memory - excel_initial_memory,
                'excel_read_memory': excel_read_memory - excel_initial_memory
            }
            
        except ImportError:
            print("⚠️ psutil not available for memory testing")
            return {}
    
    def test_error_handling_comparison(self):
        """Compare error handling capabilities"""
        print("\n🛡️ Error Handling Comparison")
        print("=" * 40)
        
        error_tests = {
            'Corrupted File': {
                'csv': self._test_csv_corruption_handling,
                'excel': self._test_excel_corruption_handling
            },
            'Missing File': {
                'csv': self._test_csv_missing_file,
                'excel': self._test_excel_missing_file
            },
            'Invalid Data Types': {
                'csv': self._test_csv_invalid_data,
                'excel': self._test_excel_invalid_data
            }
        }
        
        results = {}
        
        for test_name, test_functions in error_tests.items():
            print(f"\n{test_name}:")
            
            csv_result = test_functions['csv']()
            excel_result = test_functions['excel']()
            
            results[test_name] = {
                'csv': csv_result,
                'excel': excel_result
            }
            
            status_csv = "✅" if csv_result else "❌"
            status_excel = "✅" if excel_result else "❌"
            print(f"  CSV: {status_csv}  Excel: {status_excel}")
        
        return results
    
    def _test_csv_corruption_handling(self) -> bool:
        """Test CSV corruption handling"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False) as csv_file:
                csv_file.write('corrupted,csv,data\ninvalid,format')
                csv_path = csv_file.name
            
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                list(reader)  # Try to read
            
            os.unlink(csv_path)
            return True  # CSV is more forgiving
        except:
            return False
    
    def _test_excel_corruption_handling(self) -> bool:
        """Test Excel corruption handling"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
                excel_file.write(b'corrupted excel data')
                excel_path = excel_file.name
            
            pd.read_excel(excel_path)
            os.unlink(excel_path)
            return False  # Should fail
        except:
            os.unlink(excel_path) if os.path.exists(excel_path) else None
            return True  # Correctly caught error
    
    def _test_csv_missing_file(self) -> bool:
        """Test CSV missing file handling"""
        try:
            with open('non_existent.csv', 'r') as f:
                reader = csv.reader(f)
                list(reader)
            return False
        except FileNotFoundError:
            return True
    
    def _test_excel_missing_file(self) -> bool:
        """Test Excel missing file handling"""
        try:
            pd.read_excel('non_existent.xlsx')
            return False
        except FileNotFoundError:
            return True
    
    def _test_csv_invalid_data(self) -> bool:
        """Test CSV invalid data handling"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(['PO_NUMBER', 'STATUS'])
                writer.writerow(['PO15826591', 'INVALID_STATUS'])
                csv_path = csv_file.name
            
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                list(reader)  # Should handle invalid data
            
            os.unlink(csv_path)
            return True
        except:
            return False
    
    def _test_excel_invalid_data(self) -> bool:
        """Test Excel invalid data handling"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
                data = [{'PO_NUMBER': 'PO15826591', 'STATUS': 'INVALID_STATUS'}]
                df = pd.DataFrame(data)
                df.to_excel(excel_file.name, index=False)
                excel_path = excel_file.name
            
            pd.read_excel(excel_path)  # Should handle invalid data
            os.unlink(excel_path)
            return True
        except:
            return False
    
    def generate_recommendation(self, size_ratio: float, performance_results: dict, 
                              functionality_results: dict, memory_results: dict, 
                              error_results: dict) -> str:
        """Generate migration recommendation based on test results"""
        print("\n🎯 Migration Recommendation")
        print("=" * 40)
        
        # Scoring system
        scores = {
            'csv': 0,
            'excel': 0
        }
        
        # File size (lower is better)
        if size_ratio > 10:
            scores['csv'] += 3
        elif size_ratio > 5:
            scores['csv'] += 2
        else:
            scores['csv'] += 1
        
        # Performance (lower is better)
        avg_write_ratio = sum(r['write_ratio'] for r in performance_results.values()) / len(performance_results)
        avg_read_ratio = sum(r['read_ratio'] for r in performance_results.values()) / len(performance_results)
        
        if avg_write_ratio > 5:
            scores['csv'] += 3
        elif avg_write_ratio > 2:
            scores['csv'] += 2
        else:
            scores['csv'] += 1
        
        if avg_read_ratio > 5:
            scores['csv'] += 3
        elif avg_read_ratio > 2:
            scores['csv'] += 2
        else:
            scores['csv'] += 1
        
        # Functionality (higher is better)
        scores['excel'] += functionality_results['excel_score']
        scores['csv'] += functionality_results['csv_score']
        
        # Memory usage (lower is better)
        if memory_results:
            csv_memory = memory_results.get('csv_read_memory', 0)
            excel_memory = memory_results.get('excel_read_memory', 0)
            
            if excel_memory > csv_memory * 2:
                scores['csv'] += 2
            elif excel_memory > csv_memory:
                scores['csv'] += 1
        
        # Error handling
        error_scores = {'csv': 0, 'excel': 0}
        for test_name, results in error_results.items():
            if results['csv']:
                error_scores['csv'] += 1
            if results['excel']:
                error_scores['excel'] += 1
        
        scores['csv'] += error_scores['csv']
        scores['excel'] += error_scores['excel']
        
        print(f"CSV Score: {scores['csv']}")
        print(f"Excel Score: {scores['excel']}")
        
        # Recommendation
        if scores['excel'] > scores['csv'] * 1.2:
            recommendation = "EXCEL"
            reason = "Excel provides significantly better functionality and user experience"
        elif scores['excel'] > scores['csv']:
            recommendation = "EXCEL (with caution)"
            reason = "Excel has advantages but consider performance impact"
        elif scores['csv'] > scores['excel'] * 1.2:
            recommendation = "CSV"
            reason = "CSV provides better performance and simplicity"
        else:
            recommendation = "HYBRID"
            reason = "Consider using both: CSV for processing, Excel for reporting"
        
        print(f"\n🏆 Recommendation: {recommendation}")
        print(f"💡 Reason: {reason}")
        
        return recommendation


def run_comprehensive_comparison():
    """Run comprehensive CSV vs Excel comparison"""
    print("🧪 CSV vs Excel Comprehensive Comparison")
    print("=" * 60)
    
    comparison = CSVvsExcelComparison()
    
    # Run all comparisons
    size_ratio = comparison.test_file_size_comparison()
    performance_results = comparison.test_performance_comparison()
    functionality_results = comparison.test_functionality_comparison()
    memory_results = comparison.test_memory_usage_comparison()
    error_results = comparison.test_error_handling_comparison()
    
    # Generate recommendation
    recommendation = comparison.generate_recommendation(
        size_ratio, performance_results, functionality_results, 
        memory_results, error_results
    )
    
    print(f"\n✅ Comparison completed! Final recommendation: {recommendation}")
    return recommendation


if __name__ == "__main__":
    run_comprehensive_comparison() 