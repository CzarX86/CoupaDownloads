"""
MSG File Processor
Handles conversion of .msg files to PDF and extraction of attachments.
"""

import os
import shutil
import subprocess
import tempfile
from typing import List, Tuple, Optional
from pathlib import Path

from .config import Config


class MSGProcessor:
    """Processes MSG files by converting to PDF and extracting attachments."""
    
    def __init__(self):
        self.temp_dir = None
        
    def process_msg_file(self, msg_file_path: str, po_number: str, supplier_folder: str) -> bool:
        """
        Process a single MSG file.
        
        Args:
            msg_file_path: Path to the MSG file
            po_number: PO number for naming
            supplier_folder: Folder where to create subfolder
            
        Returns:
            bool: True if processing was successful
        """
        try:
            msg_filename = os.path.basename(msg_file_path)
            msg_name_without_ext = os.path.splitext(msg_filename)[0]
            
            # Create consistent naming for both PDF and subfolder
            # Remove any existing PO prefix from the original filename
            clean_msg_name = msg_name_without_ext
            
            # Handle cases where filename already has PO prefix (recursive to handle multiple PO prefixes)
            clean_msg_name = self._remove_po_prefixes(clean_msg_name)
            
            # Create subfolder with consistent naming (same as PDF) - using MSG prefix
            subfolder_name = f"PO{po_number}_MSG_{clean_msg_name}"
            subfolder_path = os.path.join(supplier_folder, subfolder_name)
            
            # Create the subfolder
            os.makedirs(subfolder_path, exist_ok=True)
            print(f"    📁 Created subfolder: {subfolder_name}")
            
            # Convert MSG to PDF (save in supplier folder with PO_MSG prefix)
            pdf_path = self._convert_msg_to_pdf(msg_file_path, supplier_folder, po_number, clean_msg_name)
            
            # If PDF was created, also copy it to subfolder for organization
            if pdf_path and os.path.exists(pdf_path):
                pdf_copy_path = os.path.join(subfolder_path, os.path.basename(pdf_path))
                shutil.copy2(pdf_path, pdf_copy_path)
                print(f"    📄 Copied PDF to subfolder: {os.path.basename(pdf_path)}")
            
            # Extract attachments
            attachments_extracted = self._extract_attachments(msg_file_path, subfolder_path, po_number)
            
            # Move original MSG file to subfolder with consistent naming
            msg_dest_filename = f"PO{po_number}_MSG_{clean_msg_name}.msg"
            msg_dest_path = os.path.join(subfolder_path, msg_dest_filename)
            shutil.move(msg_file_path, msg_dest_path)
            print(f"    📧 Moved original MSG: {msg_dest_filename}")
            
            # Report results
            if pdf_path:
                print(f"    📄 Converted to PDF: {os.path.basename(pdf_path)}")
            if attachments_extracted > 0:
                print(f"    📎 Extracted {attachments_extracted} attachment(s)")
            
            return True
            
        except Exception as e:
            print(f"    ❌ Failed to process MSG file {msg_filename}: {e}")
            return False
    
    def _convert_msg_to_pdf(self, msg_path: str, output_folder: str, po_number: str, msg_name: str) -> Optional[str]:
        """
        Convert MSG file to PDF using available tools.
        
        Args:
            msg_path: Path to MSG file
            output_folder: Folder to save PDF
            po_number: PO number for naming
            msg_name: Original MSG filename without extension
            
        Returns:
            Optional[str]: Path to created PDF file, or None if failed
        """
        try:
            pdf_filename = f"PO{po_number}_MSG_{msg_name}.pdf"
            pdf_path = os.path.join(output_folder, pdf_filename)
            
            # Try different conversion methods
            if self._try_libreoffice_conversion(msg_path, pdf_path):
                return pdf_path
            elif self._try_python_conversion(msg_path, pdf_path):
                return pdf_path
            else:
                print(f"    ⚠️ Could not convert MSG to PDF (no suitable converter found)")
                return None
                
        except Exception as e:
            print(f"    ❌ PDF conversion failed: {e}")
            return None
    
    def _try_libreoffice_conversion(self, msg_path: str, pdf_path: str) -> bool:
        """Try to convert MSG to PDF using LibreOffice."""
        try:
            # Check if LibreOffice is available
            result = subprocess.run(['libreoffice', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Convert using LibreOffice
                cmd = [
                    'libreoffice', '--headless', '--convert-to', 'pdf',
                    '--outdir', os.path.dirname(pdf_path), msg_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    # LibreOffice creates PDF with original name, rename it
                    temp_pdf = os.path.join(os.path.dirname(pdf_path), 
                                          os.path.splitext(os.path.basename(msg_path))[0] + '.pdf')
                    if os.path.exists(temp_pdf):
                        shutil.move(temp_pdf, pdf_path)
                        return True
                        
            return False
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    def _try_python_conversion(self, msg_path: str, pdf_path: str) -> bool:
        """Try to convert MSG to PDF using Python libraries."""
        try:
            # Try using extract-msg library
            import extract_msg
            
            msg = extract_msg.Message(msg_path)
            
            # Create a well-formatted HTML representation
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{msg.subject or 'Email'}</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f9f9f9;
                    }}
                    .email-container {{
                        background: white;
                        padding: 30px;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        border-bottom: 2px solid #0078d4;
                        padding-bottom: 15px;
                        margin-bottom: 20px;
                    }}
                    .subject {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #0078d4;
                        margin-bottom: 10px;
                    }}
                    .meta {{
                        background: #f5f5f5;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }}
                    .meta p {{
                        margin: 5px 0;
                        font-size: 14px;
                    }}
                    .meta strong {{
                        color: #555;
                        min-width: 60px;
                        display: inline-block;
                    }}
                    .body {{
                        font-size: 16px;
                        line-height: 1.8;
                        word-wrap: break-word;
                    }}
                    .body p {{
                        margin: 0 0 16px 0;
                    }}
                    .body br {{
                        display: block;
                        margin: 8px 0;
                    }}
                    .footer {{
                        margin-top: 30px;
                        padding-top: 15px;
                        border-top: 1px solid #ddd;
                        font-size: 12px;
                        color: #666;
                    }}
                </style>
            </head>
            <body>
                <div class="email-container">
                    <div class="header">
                        <div class="subject">{msg.subject or 'No Subject'}</div>
                    </div>
                    
                    <div class="meta">
                        <p><strong>From:</strong> {msg.sender or 'Unknown'}</p>
                        <p><strong>To:</strong> {msg.to or 'Unknown'}</p>
                        <p><strong>Date:</strong> {msg.date or 'Unknown'}</p>
                        <p><strong>CC:</strong> {msg.cc or 'None'}</p>
                    </div>
                    
                    <div class="body">{self._format_email_body(msg.body) or 'No body content'}</div>
                    
                    <div class="footer">
                        <p>Converted from MSG file on {msg.date or 'Unknown date'}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Save as HTML first
            html_path = os.path.join(os.path.dirname(pdf_path), 'temp.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Convert HTML to PDF using weasyprint or similar
            if self._html_to_pdf(html_path, pdf_path):
                os.remove(html_path)  # Clean up temp HTML
                return True
                
            return False
            
        except ImportError:
            print(f"    ⚠️ extract-msg library not available for MSG conversion")
            return False
        except Exception as e:
            print(f"    ⚠️ Python MSG conversion failed: {e}")
            # Try to create a simple PDF from file content as fallback
            return self._create_simple_pdf_from_file(msg_path, pdf_path)
    
    def _html_to_pdf(self, html_path: str, pdf_path: str) -> bool:
        """Convert HTML to PDF using available libraries."""
        try:
            # Try weasyprint
            from weasyprint import HTML
            HTML(html_path).write_pdf(pdf_path)
            return True
        except ImportError:
            try:
                # Try pdfkit
                import pdfkit
                pdfkit.from_file(html_path, pdf_path)
                return True
            except ImportError:
                print(f"    ⚠️ No PDF conversion library available (weasyprint or pdfkit)")
                return False
        except Exception:
            return False
    
    def _create_simple_pdf_from_file(self, msg_path: str, pdf_path: str) -> bool:
        """Create a simple PDF from file content when MSG conversion fails."""
        try:
            # Read the file content
            with open(msg_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Create a well-formatted HTML representation
            filename = os.path.basename(msg_path)
            from datetime import datetime
            file_date = datetime.fromtimestamp(os.path.getmtime(msg_path)).strftime('%Y-%m-%d %H:%M:%S')
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{filename}</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f9f9f9;
                    }}
                    .file-container {{
                        background: white;
                        padding: 30px;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        border-bottom: 2px solid #0078d4;
                        padding-bottom: 15px;
                        margin-bottom: 20px;
                    }}
                    .filename {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #0078d4;
                        margin-bottom: 10px;
                    }}
                    .meta {{
                        background: #f5f5f5;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }}
                    .meta p {{
                        margin: 5px 0;
                        font-size: 14px;
                    }}
                    .meta strong {{
                        color: #555;
                        min-width: 80px;
                        display: inline-block;
                    }}
                    .content {{
                        font-size: 14px;
                        line-height: 1.6;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                        background: #fafafa;
                        padding: 20px;
                        border-radius: 5px;
                        border-left: 4px solid #0078d4;
                        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    }}
                    .footer {{
                        margin-top: 30px;
                        padding-top: 15px;
                        border-top: 1px solid #ddd;
                        font-size: 12px;
                        color: #666;
                    }}
                </style>
            </head>
            <body>
                <div class="file-container">
                    <div class="header">
                        <div class="filename">{filename}</div>
                    </div>
                    
                    <div class="meta">
                        <p><strong>Type:</strong> MSG File (converted to PDF)</p>
                        <p><strong>Date:</strong> {file_date}</p>
                        <p><strong>Size:</strong> {len(content)} characters</p>
                    </div>
                    
                    <div class="content">{content}</div>
                    
                    <div class="footer">
                        <p>Converted from MSG file on {file_date}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Save as HTML first
            html_path = os.path.join(os.path.dirname(pdf_path), 'temp_fallback.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Convert HTML to PDF
            if self._html_to_pdf(html_path, pdf_path):
                os.remove(html_path)  # Clean up temp HTML
                return True
                
            return False
            
        except Exception as e:
            print(f"    ⚠️ Fallback PDF creation failed: {e}")
            return False
    
    def _extract_attachments(self, msg_path: str, output_folder: str, po_number: str) -> int:
        """
        Extract attachments from MSG file, filtering out signature images and artifacts.
        
        Args:
            msg_path: Path to MSG file
            output_folder: Folder to save attachments
            po_number: PO number for naming
            
        Returns:
            int: Number of attachments extracted
        """
        try:
            import extract_msg
            
            msg = extract_msg.Message(msg_path)
            attachments = msg.attachments
            extracted_count = 0
            filtered_count = 0
            
            for i, attachment in enumerate(attachments):
                try:
                    # Get attachment filename
                    filename = attachment.longFilename or attachment.shortFilename or f"attachment_{i+1}"
                    
                    # Check if this attachment should be filtered out
                    if self._should_filter_attachment(filename, attachment):
                        filtered_count += 1
                        print(f"    🚫 Filtered out: {filename} (signature/icon artifact)")
                        continue
                    
                    # Create proper filename with PO prefix
                    clean_filename = filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
                    attachment_filename = f"PO{po_number}_{clean_filename}"
                    attachment_path = os.path.join(output_folder, attachment_filename)
                    
                    # Save attachment
                    with open(attachment_path, 'wb') as f:
                        f.write(attachment.data)
                    
                    print(f"    📎 Extracted: {attachment_filename}")
                    extracted_count += 1
                    
                except Exception as e:
                    print(f"    ❌ Failed to extract attachment {i+1}: {e}")
                    continue
            
            if filtered_count > 0:
                print(f"    🚫 Filtered out {filtered_count} signature/icon artifacts")
            
            return extracted_count
            
        except ImportError:
            print(f"    ⚠️ extract-msg library not available for attachment extraction")
            return 0
        except Exception as e:
            print(f"    ❌ Attachment extraction failed: {e}")
            return 0
    
    def _remove_po_prefixes(self, filename: str) -> str:
        """
        Recursively remove PO prefixes from filename.
        
        Args:
            filename: Filename that may contain PO prefixes
            
        Returns:
            str: Filename with PO prefixes removed
        """
        if not filename.upper().startswith('PO'):
            return filename
        
        # Split by underscore to check for PO + numbers pattern
        parts = filename.split('_', 1)
        if len(parts) > 1 and parts[0].upper().startswith('PO') and parts[0][2:].isdigit():
            # Remove the PO + numbers part, recursively check the rest
            remaining = parts[1]
            return self._remove_po_prefixes(remaining)
        else:
            # Just remove "PO" prefix and recursively check the rest
            remaining = filename[2:]
            return self._remove_po_prefixes(remaining)
    
    def _format_email_body(self, body: str) -> str:
        """
        Format email body with proper paragraphs and spacing.
        
        Args:
            body: Raw email body text
            
        Returns:
            str: Formatted HTML with proper paragraphs
        """
        if not body:
            return ''
        
        # Convert line breaks to HTML
        # First, normalize line endings
        body = body.replace('\r\n', '\n').replace('\r', '\n')
        
        # Split into paragraphs (double line breaks)
        paragraphs = body.split('\n\n')
        
        # Process each paragraph
        formatted_paragraphs = []
        for paragraph in paragraphs:
            if paragraph.strip():
                # Replace single line breaks with <br> tags within paragraphs
                paragraph_html = paragraph.replace('\n', '<br>')
                # Wrap in <p> tag
                formatted_paragraphs.append(f'<p>{paragraph_html}</p>')
        
        # Join paragraphs with proper spacing
        return '\n'.join(formatted_paragraphs)
    
    def _should_filter_attachment(self, filename: str, attachment) -> bool:
        """
        Determine if an attachment should be filtered out as a signature/icon artifact.
        
        Args:
            filename: Attachment filename
            attachment: Attachment object from extract_msg
            
        Returns:
            bool: True if attachment should be filtered out
        """
        # Check if filtering is enabled
        if not Config.FILTER_MSG_ARTIFACTS:
            return False
            
        filename_lower = filename.lower()
        
        # Filter out common signature and icon artifacts
        signature_patterns = [
            # Signature images
            'signature', 'sig_', '_sig', 'sign_', '_sign',
            # Email client icons
            'icon', 'logo', 'brand', 'avatar', 'profile',
            # Small images typically used in signatures
            'banner', 'header', 'footer', 'divider',
            # Common signature file patterns
            'email_sig', 'email_signature', 'outlook_sig',
            # Image file extensions that are typically small artifacts
            'gif', 'png', 'jpg', 'jpeg', 'bmp', 'ico'
        ]
        
        # Check filename patterns
        for pattern in signature_patterns:
            if pattern in filename_lower:
                return True
        
        # Filter by file size (very small files are likely artifacts)
        try:
            file_size = len(attachment.data)
            if file_size < Config.MSG_ARTIFACT_MIN_SIZE:
                return True
        except:
            pass
        
        # Filter by content type if available
        try:
            content_type = getattr(attachment, 'contentType', '').lower()
            if content_type in ['image/gif', 'image/png', 'image/jpeg', 'image/bmp', 'image/x-icon']:
                # Only filter small images, allow larger ones
                if len(attachment.data) < Config.MSG_IMAGE_MIN_SIZE:
                    return True
        except:
            pass
        
        # Filter out files with no extension (often embedded objects)
        if '.' not in filename and len(attachment.data) < 2048:
            return True
        
        return False
    
    def cleanup(self):
        """Clean up temporary resources."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass


# Global MSG processor instance
msg_processor = MSGProcessor() 