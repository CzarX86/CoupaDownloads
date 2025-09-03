import os
from typing import Dict, List

from config import Config

class FolderHierarchyManager:
    """Simplified folder hierarchy manager for parallel testing."""
    
    def __init__(self):
        # Use the main CoupaDownloads folder, not the temp folder
        self.base_folder = os.path.expanduser("~/Downloads/CoupaDownloads")
    
    def create_folder_path(self, po_data: Dict, hierarchy_cols: List[str], has_hierarchy_data: bool, final_status: str = None) -> str:
        """Create hierarchical folder path for a PO with optional dynamic status."""
        try:
            if not has_hierarchy_data:
                # Use simple structure: base_folder/PO_number (with optional status)
                if final_status:
                    folder_path = os.path.join(self.base_folder, f"{po_data['po_number']}_{final_status}")
                else:
                    folder_path = os.path.join(self.base_folder, po_data['po_number'])
            else:
                # Create hierarchical structure
                path_parts = [self.base_folder]
                
                # Add hierarchy levels
                for col in hierarchy_cols:
                    if col in po_data and po_data[col]:
                        # Clean folder name (remove special characters)
                        folder_name = self._clean_folder_name(po_data[col])
                        path_parts.append(folder_name)
                
                # Add PO folder (with optional status)
                if final_status:
                    path_parts.append(f"{po_data['po_number']}_{final_status}")
                else:
                    path_parts.append(po_data['po_number'])
                folder_path = os.path.join(*path_parts)
            
            # Create the folder
            os.makedirs(folder_path, exist_ok=True)
            
            return folder_path
            
        except Exception as e:
            print(f"⚠️ Warning: Could not create folder hierarchy: {e}")
            # Fallback to simple structure
            if final_status:
                fallback_path = os.path.join(self.base_folder, f"{po_data['po_number']}_{final_status}")
            else:
                fallback_path = os.path.join(self.base_folder, po_data['po_number'])
            os.makedirs(fallback_path, exist_ok=True)
            return fallback_path
    
    def _clean_folder_name(self, name: str) -> str:
        """Clean folder name by removing special characters."""
        import re
        # Remove special characters except alphanumeric, spaces, and hyphens
        cleaned = re.sub(r'[^\w\s-]', '', str(name))
        # Replace spaces with underscores
        cleaned = cleaned.replace(' ', '_')
        # Remove multiple underscores
        cleaned = re.sub(r'_+', '_', cleaned)
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        return cleaned or 'Unknown'
