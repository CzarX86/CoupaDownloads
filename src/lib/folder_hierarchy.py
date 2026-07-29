"""
Folder hierarchy management module for Coupa Downloads automation.
Handles creation of structured folder paths based on Excel data with flexible column names.
"""

import os
import re
import sys
import time
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import structlog
from ..config.app_config import Config

logger = structlog.get_logger(__name__)


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
                          has_hierarchy_data: bool, supplier_name: Optional[str] = None,
                          create_dir: bool = True) -> str:
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
                return self._create_hierarchy_folder_path(po_data, hierarchy_cols, create_dir)
            else:
                return self._create_fallback_folder_path(po_data, supplier_name, create_dir)
                
        except Exception as e:
            raise Exception(f"Failed to create folder path: {e}")
    
    def _create_hierarchy_folder_path(self, po_data: Dict[str, Any], hierarchy_cols: List[str], create_dir: bool = True) -> str:
        """Create hierarchical folder structure using hierarchy columns.

        New policy: always create a canonical working folder ending in __WORK.
        Final status suffix is only applied once via finalize_folder().
        """
        hierarchy_parts = []
        
        for col in hierarchy_cols:
            value = po_data.get(col, '')
            
            # Handle nan values properly
            if pd.isna(value) or str(value).strip() == 'nan' or str(value).strip() == '':
                clean_value = 'Unknown'
            else:
                clean_value = self._clean_folder_name(str(value).strip())
            
            hierarchy_parts.append(clean_value)
        
        # Add canonical PO work folder (no status yet)
        po_number = str(po_data.get('po_number', 'Unknown_PO')).strip()
        po_folder_name = self._clean_folder_name(po_number)
        # If the PO already starts with 'PO' (with or without underscore),
        # don't add another prefix. Check for 'po' prefix case-insensitively.
        if not po_folder_name.lower().startswith('po'):
            po_folder_name = f"PO_{po_folder_name}"
        work_name = f"{po_folder_name}__WORK"
        hierarchy_parts.append(work_name)
        
        # Create full path
        base_dir = os.path.abspath(os.path.expanduser(Config.DOWNLOAD_FOLDER))
        folder_path = os.path.join(base_dir, *hierarchy_parts)
        
        # Create the folder structure if requested
        if create_dir:
            self._create_folder_structure(folder_path)
        
        return folder_path
    
    def _create_fallback_folder_path(self, po_data: Dict[str, Any], supplier_name: Optional[str], create_dir: bool = True) -> str:
        """Create fallback folder structure using supplier and PO with canonical __WORK folder."""
        po_number = str(po_data.get('po_number', 'Unknown_PO')).strip()
        supplier = supplier_name or str(po_data.get('supplier', 'Unknown_Supplier')).strip()
        
        # Clean names
        clean_supplier = self._clean_folder_name(supplier)
        po_folder_name = self._clean_folder_name(po_number)
        
        # Avoid double-prefixing: if the PO already starts with 'PO' leave it as-is.
        if not po_folder_name.lower().startswith('po'):
            po_folder_name = f"PO_{po_folder_name}"
        work_name = f"{po_folder_name}__WORK"
        
        # Create path
        base_dir = os.path.abspath(os.path.expanduser(Config.DOWNLOAD_FOLDER))
        folder_path = os.path.join(base_dir, clean_supplier, work_name)

        # Create the folder structure if requested
        if create_dir:
            self._create_folder_structure(folder_path)

        return folder_path
    
    def _should_add_status_suffix(self, status: str) -> bool:
        """Determine if status suffix should be added to PO folder name.

        New policy: always add suffix for any status except transitional 'PENDING'.
        Ensures there is never an unsuffixed final folder and avoids duplicates.
        """
        if status == 'PENDING':
            return False
        return True

    def finalize_folder(self, path: str, final_status: str) -> str:
        """Rename a canonical __WORK folder to its final status folder (atomic best-effort).

        If the folder is already finalized, returns it unchanged. Any existing
        final target is merged with the current content to prevent data loss.
        """
        import shutil

        def _safe_log(level: str, event: str, **kwargs: Any) -> None:
            try:
                getattr(logger, level)(event, **kwargs)
            except Exception:
                pass

        try:
            # Check for partial downloads loops
            if os.path.exists(path) and os.path.isdir(path):
                for _ in range(15):
                    try:
                        files = os.listdir(path)
                        if any(f.endswith('.crdownload') or f.endswith('.tmp') or f.endswith('.download') for f in files):
                            _safe_log("info", "Waiting for partial downloads to complete...", path=path)
                            time.sleep(1.0)
                            continue
                    except OSError:
                        pass
                    break

            # Cooldown period to let the OS/browser release file handles
            time.sleep(1.0 if sys.platform == "win32" else 0.3)

            if not path or not os.path.isdir(path):
                _safe_log("debug", "Finalize skipped: path missing or not a dir", path=path, exists=os.path.exists(path))
                return path

            status_upper = (final_status or '').upper().strip() or 'FAILED'
            base_dir = os.path.dirname(path)
            base_name = os.path.basename(path)

            # Keep original for logging
            original = base_name

            # Remove any sequence of __WORK at the end (case insensitive)
            base_name = re.sub(r'[_]*(?:__WORK)+[_]*$', '', base_name, flags=re.IGNORECASE)

            # Normalize underscores
            base_name = re.sub(r'_+', '_', base_name).strip('_')

            # Known terminal suffixes we manage
            known_suffixes = [
                '_COMPLETED', '_FAILED', '_NO_ATTACHMENTS', '_PARTIAL', '_PO_NOT_FOUND', '_TIMEOUT'
            ]
            upper_name = base_name.upper()

            # If already ends with any known suffix but not the desired one, strip it
            for suf in known_suffixes:
                if upper_name.endswith(suf) and suf != f'_{status_upper}':
                    base_name = base_name[: -len(suf)]
                    base_name = base_name.rstrip('_')
                    break

            # Append status if policy requires
            if self._should_add_status_suffix(status_upper):
                if not base_name.upper().endswith(f'_{status_upper}'):
                    base_name = f'{base_name}_{status_upper}'
            else:
                # Ensure we didn't leave trailing underscore
                base_name = base_name.rstrip('_')

            # Final sanitation
            base_name = re.sub(r'_+', '_', base_name).rstrip('_')

            target_path = os.path.join(base_dir, base_name)

            if os.path.exists(target_path):
                if os.path.abspath(path) == os.path.abspath(target_path):
                    _safe_log("debug", "Finalize no-op: path equals target", path=path)
                    return target_path
                
                try:
                    if os.path.samefile(path, target_path):
                        _safe_log("debug", "Finalize no-op: samefile", path=path, target=target_path)
                        return target_path
                except (OSError, AttributeError):
                    pass

            # If target exists, merge
            if os.path.exists(target_path):
                _safe_log("info", "Target folder exists, merging contents", source=path, target=target_path)
                self._merge_directories(path, target_path)
                # Force cleanup of source after merge (rmtree) CHECK for safety
                if os.path.exists(path):
                    if self._is_safe_to_delete(path):
                        try:
                            shutil.rmtree(path)
                            _safe_log("info", "Source folder safe-deleted after merge", path=path)
                        except Exception as e:
                            _safe_log("warning", "Failed to safe-delete source after merge", path=path, error=str(e))
                    else:
                        _safe_log("warning", "Source folder contains leftover files, valid data preserved", path=path)
                return target_path

            # Attempt atomic rename with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    os.rename(path, target_path)
                    _safe_log("info", "Folder finalized", original_name=original, final_name=os.path.basename(target_path), status=status_upper)
                    return target_path
                except OSError as e:
                    if attempt < max_retries - 1:
                        _safe_log("warning", "Rename failed, retrying...", error=str(e), attempt=attempt+1)
                        time.sleep(1.0)
                    else:
                        _safe_log("error", "Rename failed after retries, falling back to merge", error=str(e))
                        # Fallback using merge logic which now includes robust cleanup
                        try:
                            self._merge_directories(path, target_path)
                            if os.path.exists(path) and self._is_safe_to_delete(path):
                                shutil.rmtree(path)
                            return target_path
                        except Exception as inner_e:
                            _safe_log("error", "Critical: Failed to merge/cleanup fallback", error=str(inner_e))
                            return path

        except Exception as e:
            _safe_log("error", "Unexpected error in finalize_folder", error=str(e), path=path, status=final_status)
            return path
        
        return path

    def _is_safe_to_delete(self, folder_path: str) -> bool:
        """Check if folder contains only disposable system files."""
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                if f not in ('.DS_Store', 'Thumbs.db', 'desktop.ini'):
                    return False
        return True

    def _merge_directories(self, source: str, target: str) -> None:
        """Merge contents of source directory into target directory."""
        import shutil
        try:
            if not os.path.exists(target):
                os.makedirs(target, exist_ok=True)
            
            for item in os.listdir(source):
                s = os.path.join(source, item)
                d = os.path.join(target, item)
                
                if item in ('.DS_Store', 'Thumbs.db', 'desktop.ini'):
                    continue

                if os.path.isdir(s):
                    self._merge_directories(s, d)
                else:
                    # Retry file moves
                    for _ in range(3):
                        try:
                            if os.path.exists(d):
                                os.remove(d) # Overwrite existing
                            shutil.move(s, d)
                            break
                        except Exception:
                            time.sleep(0.5)
            
            # Additional cleanup check inside merge is redundant now as caller does it, 
            # but leaving basic rmdir try for recursive calls safety
            try:
                if not os.listdir(source):
                    os.rmdir(source)
            except Exception:
                pass

        except Exception as e:
            logger.error("Error during directory merge", source=source, target=target, error=str(e))
            raise
    
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
