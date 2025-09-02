"""
Demo script to showcase the enhanced folder hierarchy system.
This script demonstrates how the new folder organization works.
"""

import os
import pandas as pd
import tempfile
import shutil
import sys

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.folder_hierarchy import FolderHierarchyManager
from core.excel_processor import ExcelProcessor
from core.config import Config


def create_demo_excel():
    """Create a demo Excel file with hierarchy structure."""
    demo_data = {
        'PO_NUMBER': ['PO123456', 'PO789012', 'PO345678'],
        'STATUS': ['PENDING', 'PENDING', 'PENDING'],
        'SUPPLIER': ['Microsoft', 'Apple', 'Google'],
        '<|>': ['', '', ''],
        'Priority': ['High', 'Medium', 'Low'],
        'Category': ['Technology', 'Hardware', 'Software'],
        'Region': ['US', 'EU', 'APAC'],
        'AttachmentName': ['', '', '']
    }
    
    df = pd.DataFrame(demo_data)
    return df


def demo_hierarchy_system():
    """Demonstrate the enhanced folder hierarchy system."""
    print("🚀 Enhanced Folder Hierarchy System Demo")
    print("=" * 60)
    
    # Create temporary environment
    temp_dir = tempfile.mkdtemp(prefix="hierarchy_demo_")
    original_download_folder = Config.DOWNLOAD_FOLDER
    Config.DOWNLOAD_FOLDER = temp_dir
    
    try:
        # Initialize components
        hierarchy_manager = FolderHierarchyManager()
        excel_processor = ExcelProcessor()
        
        print(f"📁 Demo environment: {temp_dir}")
        print()
        
        # Create demo Excel data
        demo_df = create_demo_excel()
        print("📊 Demo Excel Structure:")
        print(f"   Columns: {list(demo_df.columns)}")
        print(f"   Rows: {len(demo_df)}")
        print()
        
        # Analyze Excel structure
        original_cols, hierarchy_cols, has_hierarchy_data = hierarchy_manager.analyze_excel_structure(demo_df)
        
        print("🔍 Structure Analysis:")
        print(f"   Original columns: {original_cols}")
        print(f"   Hierarchy columns: {hierarchy_cols}")
        print(f"   Has hierarchy data: {has_hierarchy_data}")
        print()
        
        # Demonstrate folder creation for each PO
        print("📁 Folder Creation Demo:")
        for index, row in demo_df.iterrows():
            po_number = row['PO_NUMBER']
            status = row['STATUS']
            supplier = row['SUPPLIER']
            
            # Create PO data dictionary
            po_data = {
                'po_number': po_number,
                'status': status,
                'supplier': supplier,
                'Priority': row['Priority'],
                'Category': row['Category'],
                'Region': row['Region']
            }
            
            # Create folder path
            folder_path = hierarchy_manager.create_folder_path(
                po_data, hierarchy_cols, has_hierarchy_data, supplier
            )
            
            # Get hierarchy summary
            summary = hierarchy_manager.get_hierarchy_summary(po_data, hierarchy_cols, has_hierarchy_data)
            
            print(f"   PO: {po_number}")
            print(f"      Structure: {summary['structure_type']}")
            if has_hierarchy_data:
                print(f"      Path: {summary['hierarchy_path']}")
            else:
                print(f"      Supplier: {summary['supplier']}")
            print(f"      Folder: {os.path.basename(folder_path)}")
            print()
        
        # Demonstrate attachment tracking
        print("📎 Attachment Tracking Demo:")
        attachment_list = [
            'PO123456_document1.pdf',
            'PO123456_specification.docx',
            'PO123456_invoice.xlsx'
        ]
        
        formatted_attachments = hierarchy_manager.format_attachment_names(attachment_list)
        print(f"   Attachments: {attachment_list}")
        print(f"   Formatted: {formatted_attachments}")
        print()
        
        # Show folder tree
        print("🌳 Created Folder Tree:")
        def print_tree(path, prefix=""):
            if not os.path.exists(path):
                return
            
            items = [item for item in os.listdir(path) if os.path.isdir(os.path.join(path, item))]
            items.sort()
            
            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                item_path = os.path.join(path, item)
                
                print(f"{prefix}{'└── ' if is_last else '├── '}{item}")
                
                if os.path.isdir(item_path):
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    print_tree(item_path, new_prefix)
        
        print_tree(temp_dir)
        print()
        
        print("✅ Demo completed successfully!")
        print(f"📁 Check the demo folder: {temp_dir}")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        Config.DOWNLOAD_FOLDER = original_download_folder
        print(f"🧹 Demo environment cleaned up")


def demo_status_suffix_logic():
    """Demonstrate status suffix logic."""
    print("\n🎯 Status Suffix Logic Demo")
    print("=" * 40)
    
    hierarchy_manager = FolderHierarchyManager()
    
    test_cases = [
        ('PENDING', False, 'No suffix for PENDING'),
        ('COMPLETED', False, 'No suffix for COMPLETED'),
        ('FAILED', True, 'Suffix for FAILED'),
        ('NO_ATTACHMENTS', True, 'Suffix for NO_ATTACHMENTS'),
        ('PARTIAL', True, 'Suffix for PARTIAL'),
        ('SKIPPED', True, 'Suffix for SKIPPED')
    ]
    
    for status, should_have_suffix, description in test_cases:
        result = hierarchy_manager._should_add_status_suffix(status)
        emoji = "✅" if result == should_have_suffix else "❌"
        print(f"   {emoji} {status}: {result} ({description})")


def demo_folder_name_cleaning():
    """Demonstrate folder name cleaning."""
    print("\n🧹 Folder Name Cleaning Demo")
    print("=" * 40)
    
    hierarchy_manager = FolderHierarchyManager()
    
    test_cases = [
        ('Microsoft Corp', 'Microsoft_Corp'),
        ('High Priority', 'High_Priority'),
        ('Tech/Software', 'Tech_Software'),
        ('Company & Co.', 'Company___Co'),
        ('', 'Unknown'),
        ('nan', 'Unknown'),
        ('Very Long Company Name That Exceeds Fifty Characters Limit', 'Very_Long_Company_Name_That_Exceeds_Fifty_Char')
    ]
    
    for input_name, expected in test_cases:
        result = hierarchy_manager._clean_folder_name(input_name)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{input_name}' → '{result}'")


if __name__ == "__main__":
    demo_hierarchy_system()
    demo_status_suffix_logic()
    demo_folder_name_cleaning()
