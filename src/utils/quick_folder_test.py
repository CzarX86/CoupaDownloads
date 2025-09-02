"""
Quick test script to demonstrate folder structure creation.
Run this to see the folder structure based on your Excel file.
"""

import os
import pandas as pd
import shutil
import re

def clean_folder_name(name: str) -> str:
    """Clean a name to be safe for use as a folder name."""
    if not name:
        return "Unknown"
    
    # Handle nan values
    if pd.isna(name) or str(name).lower() == 'nan':
        return "Unknown"
    
    # Replace spaces and invalid characters with underscores
    cleaned = re.sub(r'[<>:"/\\|?*&\s]', '_', str(name))
    
    # Remove multiple underscores and trim
    cleaned = re.sub(r'_+', '_', cleaned).strip('_')
    cleaned = cleaned.rstrip('._')
    
    # Limit length
    if len(cleaned) > 50:
        cleaned = cleaned[:50].rstrip('_')
    
    return cleaned if cleaned else "Unknown"

def should_add_status_suffix(status: str) -> bool:
    """Determine if status suffix should be added to PO folder name."""
    # Don't add suffix for these statuses
    no_suffix_statuses = ['PENDING', 'COMPLETED']
    return status not in no_suffix_statuses

def test_folder_structure():
    """Test folder structure creation from Excel file."""
    
    # Excel file path
    excel_file_path = "/Users/juliocezar/Dev/work/CoupaDownloads/data/input/input.xlsx"
    
    # Use actual downloads folder
    downloads_dir = os.path.expanduser("~/Downloads/CoupaDownloads")
    
    try:
        print(f"🧪 Testing folder structure creation")
        print(f"📊 Excel file: {excel_file_path}")
        print(f"📁 Downloads directory: {downloads_dir}")
        print("-" * 60)
        
        # Read Excel file - limit to top 100 rows
        df = pd.read_excel(excel_file_path, engine='openpyxl')
        df = df.head(100)  # Limit to top 100 rows
        print(f"📊 Excel structure: {df.shape[0]} rows (limited to 100), {df.shape[1]} columns")
        print(f"📋 Columns: {list(df.columns)}")
        
        # Find separator column
        separator_index = None
        for i, col in enumerate(df.columns):
            if str(col).strip() == "<|>":
                separator_index = i
                break
        
        if separator_index is None:
            print("❌ No separator column '<|>' found")
            return
        
        # Split columns
        original_cols = list(df.columns[:separator_index])
        hierarchy_cols = list(df.columns[separator_index + 1:])
        
        print(f"\n📋 Column Analysis:")
        print(f"   Original: {original_cols}")
        print(f"   Separator: '<|>'")
        print(f"   Hierarchy: {hierarchy_cols}")
        
        # Check if hierarchy columns have meaningful data
        has_hierarchy_data = False
        for col in hierarchy_cols:
            non_empty = df[col].dropna().astype(str).str.strip()
            non_empty = non_empty[non_empty != '']
            non_empty = non_empty[non_empty != 'nan']
            if len(non_empty) > 0:
                has_hierarchy_data = True
                print(f"   ✅ {col}: {len(non_empty)} valid values")
            else:
                print(f"   ❌ {col}: no valid data")
        
        print(f"\n📁 Creating folder structure in downloads directory...")
        
        # Ensure downloads directory exists
        os.makedirs(downloads_dir, exist_ok=True)
        
        created_folders = []
        
        for index, row in df.iterrows():
            po_number = str(row.get('PO_NUMBER', f'PO_{index}')).strip()
            status = str(row.get('STATUS', 'PENDING')).strip()
            
            # Determine PO folder name with appropriate suffix
            po_folder_name = clean_folder_name(po_number)
            if should_add_status_suffix(status):
                po_folder_name = f"{po_folder_name}_{status}"
            
            if has_hierarchy_data:
                # Use hierarchy columns for folder structure
                hierarchy_parts = []
                for col in hierarchy_cols:
                    value = row.get(col)
                    # Handle nan values properly
                    if pd.isna(value) or str(value).strip() == 'nan':
                        hierarchy_parts.append('Unknown')
                    else:
                        clean_value = clean_folder_name(str(value).strip())
                        hierarchy_parts.append(clean_value)
                
                # Add PO number (with status suffix if needed)
                hierarchy_parts.extend([
                    po_folder_name,
                    'FilesDownloaded_from_Coupa'  # Placeholder for actual files
                ])
                
                folder_path = os.path.join(downloads_dir, *hierarchy_parts)
                print(f"   📁 Hierarchy: {'/'.join(hierarchy_parts)}")
                
            else:
                # Use current approach: Supplier + PO
                supplier = str(row.get('SUPPLIER', 'Unknown_Supplier')).strip()
                folder_path = os.path.join(
                    downloads_dir,
                    clean_folder_name(supplier),
                    po_folder_name
                )
                print(f"   📁 Fallback: {clean_folder_name(supplier)}/{po_folder_name}")
            
            # Create folder
            os.makedirs(folder_path, exist_ok=True)
            created_folders.append(folder_path)
        
        print(f"\n✅ Created {len(created_folders)} folders")
        print(f"�� Structure type: {'Hierarchy' if has_hierarchy_data else 'Fallback'}")
        
        # Display tree structure
        print(f"\n🌳 Folder Tree:")
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
        
        print_tree(downloads_dir)
        
        print(f"\n🎯 Test completed successfully!")
        print(f"📁 Check your downloads folder: {downloads_dir}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_folder_structure()
