"""
Folder hierarchy management module for Coupa Downloads automation.
Handles creation of structured folder paths based on Excel data with flexible column names.
"""

import os
import re
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
from .config import Config


class FolderHierarchyManager:
    """Manages folder hierarchy creation and organization."""
    
    def __init__(self):
        self.hierarchy_enabled = True
        self.separator_column = "<|>"
    
    def analyze_excel_structure(self, df: pd.DataFrame) -> Tuple[List[str], List[str], bool]:
        """
        Analyze Excel structure to identify hierarchy columns.
        
        Args:
            df: Pandas DataFrame from Excel file
            
        Returns:
            Tuple of (original_columns, hierarchy_columns, has_hierarchy_data)
        """
        # Find separator column
        separator_index = None
        for i, col in enumerate(df.columns):
            if str(col).strip() == self.separator_column:
                separator_index = i
                break
        
        if separator_index is None:
            # No separator found - use fallback structure
            return list(df.columns), [], False
        
        # Split columns
        original_cols = list(df.columns[:separator_index])
        hierarchy_cols = list(df.columns[separator_index + 1:])
        
        # Check if hierarchy columns have meaningful data
        has_hierarchy_data = self._validate_hierarchy_data(df, hierarchy_cols)
        
        return original_cols, hierarchy_cols, has_hierarchy_data
    
    def _validate_hierarchy_data(self, df: pd.DataFrame, hierarchy_cols: List[str]) -> bool:
        """
        Validate if hierarchy columns contain meaningful data.
        
        Args:
            df: Pandas DataFrame
            hierarchy_cols: List of hierarchy column names
            
        Returns:
            True if any hierarchy column has valid data
        """
        for col in hierarchy_cols:
            if col not in df.columns:
                continue
                
            # Check for non-empty, non-null values
            non_empty = df[col].dropna().astype(str).str.strip()
            non_empty = non_empty[non_empty != '']
            non_empty = non_empty[non_empty != 'nan']
            
            if len(non_empty) > 0:
                return True
        
        return False
    
    def create_folder_path(self, po_data: Dict[str, Any], hierarchy_cols: List[str], 
                          has_hierarchy_data: bool, supplier_name: str = None) -> str:
        """
        Create folder path based on PO data and hierarchy configuration.
        
        Args:
            po_data: Dictionary containing PO information
            hierarchy_cols: List of hierarchy column names
            has_hierarchy_data: Whether hierarchy columns contain data
            supplier_name: Supplier name (used for fallback)
            
        Returns:
            str: Full folder path for downloads
        """
        try:
            if has_hierarchy_data:
                return self._create_hierarchy_folder_path(po_data, hierarchy_cols)
            else:
                return self._create_fallback_folder_path(po_data, supplier_name)
                
        except Exception as e:
            raise Exception(f"Failed to create folder path: {e}")
    
    def _create_hierarchy_folder_path(self, po_data: Dict[str, Any], hierarchy_cols: List[str]) -> str:
        """Create hierarchical folder structure using hierarchy columns."""
        hierarchy_parts = []
        
        for col in hierarchy_cols:
            value = po_data.get(col, '')
            
            # Handle nan values properly
            if pd.isna(value) or str(value).strip() == 'nan':
                hierarchy_parts.append('Unknown')
            else:
                clean_value = self._clean_folder_name(str(value).strip())
                hierarchy_parts.append(clean_value)
        
        # Add PO number with appropriate status suffix
        po_number = str(po_data.get('po_number', 'Unknown_PO')).strip()
        status = str(po_data.get('status', 'PENDING')).strip()
        
        po_folder_name = self._clean_folder_name(po_number)
        if self._should_add_status_suffix(status):
            po_folder_name = f"{po_folder_name}_{status}"
        
        hierarchy_parts.append(po_folder_name)
        
        # Create full path
        folder_path = os.path.join(Config.DOWNLOAD_FOLDER, *hierarchy_parts)
        
        # Create the folder structure
        self._create_folder_structure(folder_path)
        
        return folder_path
    
    def _create_fallback_folder_path(self, po_data: Dict[str, Any], supplier_name: str) -> str:
        """Create fallback folder structure using supplier and PO."""
        po_number = str(po_data.get('po_number', 'Unknown_PO')).strip()
        status = str(po_data.get('status', 'PENDING')).strip()
        supplier = supplier_name or str(po_data.get('supplier', 'Unknown_Supplier')).strip()
        
        # Clean names
        clean_supplier = self._clean_folder_name(supplier)
        po_folder_name = self._clean_folder_name(po_number)
        
        # Add status suffix if needed
        if self._should_add_status_suffix(status):
            po_folder_name = f"{po_folder_name}_{status}"
        
        # Create path
        folder_path = os.path.join(Config.DOWNLOAD_FOLDER, clean_supplier, po_folder_name)
        
        # Create the folder structure
        self._create_folder_structure(folder_path)
        
        return folder_path
    
    def _should_add_status_suffix(self, status: str) -> bool:
        """Determine if status suffix should be added to PO folder name."""
        # Don't add suffix for these statuses
        no_suffix_statuses = ['PENDING', 'COMPLETED']
        return status not in no_suffix_statuses
    
    def _clean_folder_name(self, name: str) -> str:
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
        
        # Remove trailing periods and underscores
        cleaned = cleaned.rstrip('._')
        
        # Limit length to avoid filesystem issues
        if len(cleaned) > 50:
            cleaned = cleaned[:50].rstrip('_')
        
        # Ensure it's not empty
        if not cleaned:
            cleaned = "Unknown"
            
        return cleaned
    
    def _create_folder_structure(self, folder_path: str) -> None:
        """Create the complete folder structure."""
        try:
            os.makedirs(folder_path, exist_ok=True)
        except Exception as e:
            raise Exception(f"Could not create folder structure '{folder_path}': {e}")
    
    def format_attachment_names(self, attachment_list: List[str]) -> str:
        """
        Format attachment names for Excel storage.
        
        Args:
            attachment_list: List of attachment file names
            
        Returns:
            str: Formatted string with semicolon and newline separators
        """
        if not attachment_list:
            return ""
        
        # Join with semicolon and newline
        return ";\n".join(attachment_list)
    
    def get_hierarchy_summary(self, po_data: Dict[str, Any], hierarchy_cols: List[str], 
                            has_hierarchy_data: bool) -> Dict[str, str]:
        """Get a summary of the folder hierarchy for logging."""
        if has_hierarchy_data:
            hierarchy_parts = []
            for col in hierarchy_cols:
                value = po_data.get(col, '')
                if pd.isna(value) or str(value).strip() == 'nan':
                    hierarchy_parts.append('Unknown')
                else:
                    hierarchy_parts.append(self._clean_folder_name(str(value).strip()))
            
            return {
                'structure_type': 'hierarchy',
                'hierarchy_path': '/'.join(hierarchy_parts),
                'po_number': str(po_data.get('po_number', 'Unknown')),
                'status': str(po_data.get('status', 'PENDING'))
            }
        else:
            return {
                'structure_type': 'fallback',
                'supplier': str(po_data.get('supplier', 'Unknown_Supplier')),
                'po_number': str(po_data.get('po_number', 'Unknown')),
                'status': str(po_data.get('status', 'PENDING'))
            }
