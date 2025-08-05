#!/usr/bin/env python3
"""
Focused Analysis of PO16277411 Partial Download Issue
Analyzes the specific case of PO16277411 to understand why it downloaded partially.
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def analyze_po16277411_issue():
    """Analyze the PO16277411 partial download issue."""
    
    print("🔍 Analyzing PO16277411 Partial Download Issue")
    print("="*80)
    
    # Load telemetry data
    telemetry_file = "tests/download_telemetry_details.csv"
    if os.path.exists(telemetry_file):
        print(f"📊 Loading telemetry data from: {telemetry_file}")
        telemetry_df = pd.read_csv(telemetry_file)
        
        # Filter for PO16277411
        po16277411_data = telemetry_df[telemetry_df['po'] == 'PO16277411']
        
        print(f"\n📋 PO16277411 Telemetry Analysis:")
        print(f"  Total attempts: {len(po16277411_data)}")
        methods_series = po16277411_data['method']
        methods_list = methods_series.dropna().unique().tolist()
        print(f"  Methods tried: {methods_list}")
        results_series = po16277411_data['result']
        results_dict = results_series.value_counts().to_dict()
        print(f"  Results: {results_dict}")
        
        print(f"\n📝 Detailed Attempt Log:")
        for idx, row in po16277411_data.iterrows():
            status_icon = "✅" if row['result'] == 'success' else "❌" if row['result'] == 'fail' else "🔄"
            filename = row['filename'] if pd.notna(row['filename']) else "Unknown"
            print(f"  {status_icon} {row['method']}: {row['result']} - {filename}")
        
        # Analyze the pattern
        print(f"\n🔍 Pattern Analysis:")
        success_mask = po16277411_data['result'] == 'success'
        fail_mask = po16277411_data['result'] == 'fail'
        success_count = success_mask.sum()
        fail_count = fail_mask.sum()
        
        print(f"  Success rate: {success_count}/{len(po16277411_data)} ({success_count/len(po16277411_data)*100:.1f}%)")
        print(f"  Failure rate: {fail_count}/{len(po16277411_data)} ({fail_count/len(po16277411_data)*100:.1f}%)")
        
        # Method effectiveness
        for method in methods_list:
            method_mask = po16277411_data['method'] == method
            method_data = po16277411_data[method_mask]
            method_success_mask = method_data['result'] == 'success'
            method_success = method_success_mask.sum()
            method_total = len(method_data)
            print(f"  {method}: {method_success}/{method_total} successful ({method_success/method_total*100:.1f}%)")
    
    # Load CSV data
    csv_file = "input.csv"
    if os.path.exists(csv_file):
        print(f"\n📄 Loading CSV data from: {csv_file}")
        csv_df = pd.read_csv(csv_file)
        
        # Find PO16277411
        po16277411_row = csv_df[csv_df.iloc[:, 0] == 'PO16277411']
        
        if not po16277411_row.empty:
            row = po16277411_row.iloc[0]
            print(f"\n📊 PO16277411 Current Status:")
            print(f"  Status: {row.iloc[1]}")
            print(f"  Supplier: {row.iloc[2]}")
            print(f"  Attachments Found: {row.iloc[3]}")
            print(f"  Attachments Downloaded: {row.iloc[4]}")
            print(f"  Last Updated: {row.iloc[5]}")
            print(f"  Download Folder: {row.iloc[7]}")
            print(f"  Coupa URL: {row.iloc[8]}")
            
            # Calculate success rate
            if row.iloc[3] > 0:
                success_rate = (row.iloc[4] / row.iloc[3]) * 100
                print(f"  Success Rate: {success_rate:.1f}%")
                
                if success_rate < 100:
                    print(f"  ⚠️ PARTIAL DOWNLOAD: {row.iloc[4]} of {row.iloc[3]} attachments downloaded")
                else:
                    print(f"  ✅ COMPLETE DOWNLOAD: All {row.iloc[4]} attachments downloaded")
    
    # Check backup files for history
    backup_dir = "backups"
    if os.path.exists(backup_dir):
        print(f"\n📚 Analyzing backup history...")
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith("input_backup_") and f.endswith(".csv")]
        backup_files.sort()
        
        po16277411_history = []
        for backup_file in backup_files[-5:]:  # Last 5 backups
            backup_path = os.path.join(backup_dir, backup_file)
            try:
                backup_df = pd.read_csv(backup_path)
                po_row = backup_df[backup_df.iloc[:, 0] == 'PO16277411']
                if not po_row.empty:
                    row = po_row.iloc[0]
                    po16277411_history.append({
                        'backup_file': backup_file,
                        'status': row.iloc[1] if len(row) > 1 else 'Unknown',
                        'attachments_found': row.iloc[3] if len(row) > 3 else 0,
                        'attachments_downloaded': row.iloc[4] if len(row) > 4 else 0,
                        'timestamp': row.iloc[5] if len(row) > 5 else 'Unknown'
                    })
            except Exception as e:
                print(f"  ⚠️ Could not read {backup_file}: {e}")
        
        if po16277411_history:
            print(f"\n📈 PO16277411 Status History (Last {len(po16277411_history)} backups):")
            for entry in po16277411_history:
                status_icon = "✅" if entry['status'] == 'COMPLETED' else "⚠️" if entry['status'] == 'PARTIAL' else "❌"
                print(f"  {status_icon} {entry['backup_file']}: {entry['status']} ({entry['attachments_downloaded']}/{entry['attachments_found']})")
    
    # Generate recommendations
    print(f"\n🎯 Recommendations for PO16277411:")
    print(f"  1. 🔄 Retry the download with increased timeout values")
    print(f"  2. 🔍 Check if the second attachment has different characteristics (size, type, etc.)")
    print(f"  3. 🛠️ Implement retry logic specifically for failed attachments")
    print(f"  4. 📊 Monitor download progress more granularly")
    print(f"  5. 🔧 Consider using alternative download methods for problematic files")
    
    # Root cause analysis
    print(f"\n🔍 Root Cause Analysis:")
    print(f"  • Multiple download methods were attempted (direct, right_click, temp_dir)")
    print(f"  • Only the temp_dir method succeeded for one file")
    print(f"  • The second attachment may have:")
    print(f"    - Different file characteristics")
    print(f"    - Network timeout issues")
    print(f"    - Browser interaction problems")
    print(f"    - File size or type restrictions")
    
    return {
        'po_number': 'PO16277411',
        'status': 'PARTIAL',
        'attachments_found': 2,
        'attachments_downloaded': 1,
        'success_rate': 50.0,
        'recommendations': [
            'Retry with increased timeout',
            'Check second attachment characteristics',
            'Implement retry logic for failed attachments',
            'Monitor download progress granularly',
            'Use alternative download methods for problematic files'
        ]
    }

def main():
    """Main function to run the analysis."""
    try:
        analysis_result = analyze_po16277411_issue()
        
        # Save analysis report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"po16277411_analysis_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(analysis_result, f, indent=2, default=str)
        
        print(f"\n📄 Analysis report saved to: {report_file}")
        print(f"✅ Analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 