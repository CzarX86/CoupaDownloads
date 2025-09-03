import os
import pandas as pd
from typing import List, Tuple, Dict, Any

from config import Config

class ExcelProcessor:
    """Simplified Excel processor for parallel testing."""
    
    def __init__(self):
        self.excel_path = os.path.join(Config.INPUT_DIR, "input.xlsx")
    
    def get_excel_file_path(self) -> str:
        """Get the path to the Excel file."""
        return self.excel_path
    
    def read_po_numbers_from_excel(self, excel_path: str) -> Tuple[List[Dict], List[str], List[str], bool]:
        """Read PO numbers from Excel file."""
        try:
            # Read Excel file (try different sheet names)
            try:
                df = pd.read_excel(excel_path, sheet_name='PO_Data')
            except:
                try:
                    df = pd.read_excel(excel_path, sheet_name='Sheet1')
                except:
                    df = pd.read_excel(excel_path)  # Read first sheet
            
            # Define hierarchy columns
            hierarchy_cols = ['Priority', 'Supplier Segment', 'Spend Type', 'L1 UU Supplier Name']
            
            # Check if hierarchy columns exist
            has_hierarchy_data = all(col in df.columns for col in hierarchy_cols)
            
            # Convert to list of dictionaries
            po_entries = []
            for _, row in df.iterrows():
                entry = {
                    'po_number': str(row['PO_NUMBER']),
                    'status': row.get('STATUS', 'Pending'),
                    'error_message': row.get('ERROR_MESSAGE', ''),
                    'download_folder': row.get('DOWNLOAD_FOLDER', ''),
                    'attachments_found': row.get('ATTACHMENTS_FOUND', 0),
                    'attachments_downloaded': row.get('ATTACHMENTS_DOWNLOADED', 0)
                }
                
                # Add hierarchy data
                for col in hierarchy_cols:
                    if col in df.columns:
                        entry[col] = str(row[col]) if pd.notna(row[col]) else ''
                
                po_entries.append(entry)
            
            # Get original columns
            original_cols = list(df.columns)
            
            print(f"📊 Loaded {len(po_entries)} POs from Excel")
            return po_entries, original_cols, hierarchy_cols, has_hierarchy_data
            
        except Exception as e:
            print(f"❌ Error reading Excel file: {e}")
            return [], [], [], False
    
    def update_po_status(self, po_number: str, status: str, error_message: str = "", download_folder: str = ""):
        """Update PO status in Excel file."""
        try:
            # Read current Excel file
            df = pd.read_excel(self.excel_path, sheet_name='PO_Data')
            
            # Find the PO and update status
            mask = df['PO_NUMBER'] == po_number
            if mask.any():
                df.loc[mask, 'STATUS'] = status
                df.loc[mask, 'ERROR_MESSAGE'] = error_message
                if download_folder:
                    df.loc[mask, 'DOWNLOAD_FOLDER'] = download_folder
            
            # Save updated Excel file
            df.to_excel(self.excel_path, sheet_name='PO_Data', index=False)
            
        except Exception as e:
            print(f"⚠️ Warning: Could not update Excel status for {po_number}: {e}")
