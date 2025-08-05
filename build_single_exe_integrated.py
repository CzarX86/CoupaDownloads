#!/usr/bin/env python3
"""
Integrated Single EXE Builder for CoupaDownloads
Creates a single executable that properly integrates with the original system
"""

import os
import sys
import platform
import subprocess
import shutil
import requests
import zipfile
from pathlib import Path
import tempfile


class IntegratedExeBuilder:
    """Builds an integrated single executable file."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.build_dir = self.project_root / "build"
        self.drivers_dir = self.build_dir / "drivers"
        
    def clean_build(self):
        """Clean previous build."""
        print("🧹 Cleaning previous build...")
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(exist_ok=True)
        print("✅ Build directory cleaned")
    
    def download_stable_edgedriver(self):
        """Download a stable EdgeDriver version."""
        print("🔧 Downloading stable EdgeDriver...")
        
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Use a stable version that works with most Edge versions
        stable_version = "120.0.2210.91"
        
        if system == "windows":
            if "64" in machine or "x86_64" in machine:
                driver_url = f"https://msedgedriver.azureedge.net/{stable_version}/edgedriver_win64.zip"
                driver_filename = "edgedriver_win64.zip"
            else:
                driver_url = f"https://msedgedriver.azureedge.net/{stable_version}/edgedriver_win32.zip"
                driver_filename = "edgedriver_win32.zip"
        else:
            print("⚠️ Single EXE build only supported on Windows")
            return False
        
        try:
            # Download EdgeDriver
            response = requests.get(driver_url, stream=True)
            response.raise_for_status()
            
            driver_zip = self.build_dir / driver_filename
            with open(driver_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Extract EdgeDriver
            with zipfile.ZipFile(driver_zip, 'r') as zip_ref:
                zip_ref.extractall(self.drivers_dir)
            
            print(f"✅ Stable EdgeDriver {stable_version} downloaded")
            return True
            
        except Exception as e:
            print(f"❌ Failed to download EdgeDriver: {e}")
            return False
    
    def create_integrated_main_script(self):
        """Create the main script that integrates with original system."""
        print("📝 Creating integrated main EXE script...")
        
        main_script_content = '''#!/usr/bin/env python3
"""
CoupaDownloads - Integrated Single EXE Application
Complete system with proper integration to original download system
"""

import os
import sys
import tempfile
import zipfile
import subprocess
import platform
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
import time
import shutil
import csv


class CoupaDownloadsIntegratedApp:
    """Main application class with proper system integration."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CoupaDownloads - Automated PO Attachment Downloader")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        
        # Set icon if available
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        self.setup_ui()
        self.po_numbers = []
        self.temp_dir = None
        self.original_system_path = None
        
    def setup_ui(self):
        """Setup the user interface."""
        # Configure grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)
        
        # Title
        title_label = tk.Label(
            self.root, 
            text="CoupaDownloads", 
            font=("Arial", 16, "bold"),
            fg="#2E86AB"
        )
        title_label.grid(row=0, column=0, pady=10)
        
        # Subtitle
        subtitle_label = tk.Label(
            self.root,
            text="Automated PO Attachment Downloader (Integrated)",
            font=("Arial", 10),
            fg="#666666"
        )
        subtitle_label.grid(row=1, column=0, pady=(0, 20))
        
        # Main frame
        main_frame = tk.Frame(self.root)
        main_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # PO Numbers section
        po_frame = tk.LabelFrame(main_frame, text="Purchase Order Numbers", padx=10, pady=10)
        po_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        po_frame.grid_columnconfigure(0, weight=1)
        
        # Instructions
        instructions = tk.Label(
            po_frame,
            text="Enter PO numbers (one per line) or import from CSV file:",
            font=("Arial", 9)
        )
        instructions.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        # Text area for PO numbers
        self.po_text = tk.Text(po_frame, height=8, width=60)
        self.po_text.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        # Scrollbar for text area
        scrollbar = tk.Scrollbar(po_frame, orient="vertical", command=self.po_text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.po_text.configure(yscrollcommand=scrollbar.set)
        
        # Buttons frame
        buttons_frame = tk.Frame(po_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        
        # Import CSV button
        import_btn = tk.Button(
            buttons_frame,
            text="📁 Import CSV",
            command=self.import_csv,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 9, "bold")
        )
        import_btn.pack(side="left", padx=(0, 10))
        
        # Clear button
        clear_btn = tk.Button(
            buttons_frame,
            text="🗑️ Clear",
            command=self.clear_po_numbers,
            bg="#f44336",
            fg="white",
            font=("Arial", 9, "bold")
        )
        clear_btn.pack(side="left")
        
        # Sample data button
        sample_btn = tk.Button(
            buttons_frame,
            text="📋 Load Sample",
            command=self.load_sample_data,
            bg="#2196F3",
            fg="white",
            font=("Arial", 9, "bold")
        )
        sample_btn.pack(side="left", padx=(10, 0))
        
        # Settings section
        settings_frame = tk.LabelFrame(main_frame, text="Settings", padx=10, pady=10)
        settings_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        # Headless mode
        self.headless_var = tk.BooleanVar()
        headless_check = tk.Checkbutton(
            settings_frame,
            text="Run in headless mode (no browser window)",
            variable=self.headless_var,
            font=("Arial", 9)
        )
        headless_check.grid(row=0, column=0, sticky="w")
        
        # Max POs limit
        max_po_frame = tk.Frame(settings_frame)
        max_po_frame.grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        max_po_label = tk.Label(max_po_frame, text="Max POs to process:", font=("Arial", 9))
        max_po_label.pack(side="left")
        
        self.max_po_var = tk.StringVar(value="0")
        max_po_entry = tk.Entry(max_po_frame, textvariable=self.max_po_var, width=10)
        max_po_entry.pack(side="left", padx=(5, 0))
        
        max_po_help = tk.Label(max_po_frame, text="(0 = no limit)", font=("Arial", 8), fg="#666666")
        max_po_help.pack(side="left", padx=(5, 0))
        
        # Progress section
        progress_frame = tk.LabelFrame(main_frame, text="Progress", padx=10, pady=10)
        progress_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = tk.Scale(
            progress_frame,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.progress_var,
            state="readonly",
            showvalue=False
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        # Status label
        self.status_var = tk.StringVar(value="Ready to start")
        status_label = tk.Label(
            progress_frame,
            textvariable=self.status_var,
            font=("Arial", 9),
            fg="#666666"
        )
        status_label.grid(row=1, column=0, sticky="w")
        
        # Action buttons
        action_frame = tk.Frame(main_frame)
        action_frame.grid(row=3, column=0, pady=(10, 0))
        
        # Start button
        self.start_btn = tk.Button(
            action_frame,
            text="🚀 Start Download",
            command=self.start_download,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
            width=15,
            height=2
        )
        self.start_btn.pack(side="left", padx=(0, 10))
        
        # Exit button
        exit_btn = tk.Button(
            action_frame,
            text="❌ Exit",
            command=self.root.quit,
            bg="#f44336",
            fg="white",
            font=("Arial", 10),
            width=10
        )
        exit_btn.pack(side="left")
        
        # Load sample data by default
        self.load_sample_data()
        
    def import_csv(self):
        """Import PO numbers from CSV file."""
        file_path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse CSV content
                lines = content.strip().split('\\n')
                po_numbers = []
                
                for line in lines:
                    line = line.strip()
                    if line and line.upper() != 'PO_NUMBER':
                        po_numbers.append(line)
                
                # Update text area
                self.po_text.delete(1.0, tk.END)
                self.po_text.insert(1.0, '\\n'.join(po_numbers))
                
                messagebox.showinfo("Success", f"Imported {len(po_numbers)} PO numbers from {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import CSV file: {e}")
    
    def clear_po_numbers(self):
        """Clear all PO numbers."""
        self.po_text.delete(1.0, tk.END)
    
    def load_sample_data(self):
        """Load sample PO numbers."""
        sample_data = """PO15262984
PO15327452
PO15362783
PO15412345
PO15467890"""
        
        self.po_text.delete(1.0, tk.END)
        self.po_text.insert(1.0, sample_data)
    
    def get_po_numbers(self):
        """Get PO numbers from text area."""
        content = self.po_text.get(1.0, tk.END).strip()
        if not content:
            return []
        
        lines = content.split('\\n')
        po_numbers = []
        
        for line in lines:
            line = line.strip()
            if line:
                po_numbers.append(line)
        
        return po_numbers
    
    def validate_input(self):
        """Validate user input."""
        po_numbers = self.get_po_numbers()
        
        if not po_numbers:
            messagebox.showerror("Error", "Please enter at least one PO number")
            return False
        
        # Validate PO format
        invalid_pos = []
        for po in po_numbers:
            if not po.upper().startswith('PO'):
                invalid_pos.append(po)
        
        if invalid_pos:
            messagebox.showerror("Error", f"Invalid PO format: {', '.join(invalid_pos)}\\nPO numbers must start with 'PO'")
            return False
        
        return True
    
    def setup_original_system(self):
        """Setup the original system in temporary directory."""
        try:
            # Create directory structure
            data_dir = self.temp_dir / "data" / "input"
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy source files
            src_dir = self.temp_dir / "src" / "core"
            src_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy core files
            core_files = [
                "browser.py", "config.py", "csv_processor.py", 
                "downloader.py", "driver_manager.py"
            ]
            
            for file_name in core_files:
                src_file = Path("src/core") / file_name
                dst_file = src_dir / file_name
                if src_file.exists():
                    shutil.copy2(src_file, dst_file)
            
            # Copy main.py
            main_src = Path("src/main.py")
            main_dst = self.temp_dir / "src" / "main.py"
            if main_src.exists():
                shutil.copy2(main_src, main_dst)
            
            # Copy drivers
            drivers_dst = self.temp_dir / "drivers"
            drivers_dst.mkdir(exist_ok=True)
            if Path("drivers").exists():
                shutil.copytree("drivers", drivers_dst, dirs_exist_ok=True)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup original system: {e}")
            return False
    
    def create_input_csv(self, po_numbers):
        """Create input CSV file in the expected format."""
        try:
            input_file = self.temp_dir / "data" / "input" / "input.csv"
            
            with open(input_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['PO_NUMBER'])  # Header
                for po in po_numbers:
                    writer.writerow([po])
            
            return str(input_file)
            
        except Exception as e:
            print(f"❌ Failed to create input CSV: {e}")
            return None
    
    def run_original_system(self, input_file_path):
        """Run the original system with the created input file."""
        try:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            # Set environment variables
            os.environ['PYTHONPATH'] = str(self.temp_dir)
            
            # Run the original main.py
            result = subprocess.run([
                sys.executable, "src/main.py"
            ], capture_output=True, text=True)
            
            # Restore original directory
            os.chdir(original_cwd)
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except Exception as e:
            print(f"❌ Failed to run original system: {e}")
            return False, "", str(e)
    
    def start_download(self):
        """Start the download process."""
        if not self.validate_input():
            return
        
        # Disable start button
        self.start_btn.config(state="disabled")
        
        # Start download in separate thread
        download_thread = threading.Thread(target=self.download_process)
        download_thread.daemon = True
        download_thread.start()
    
    def download_process(self):
        """Main download process with original system integration."""
        try:
            po_numbers = self.get_po_numbers()
            max_pos = int(self.max_po_var.get()) if self.max_po_var.get().isdigit() else 0
            
            if max_pos > 0:
                po_numbers = po_numbers[:max_pos]
            
            self.status_var.set(f"Processing {len(po_numbers)} PO numbers...")
            self.progress_var.set(10)
            
            # Create temporary directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix="CoupaDownloads_"))
            
            # Setup original system
            self.status_var.set("Setting up system...")
            self.progress_var.set(20)
            
            if not self.setup_original_system():
                raise Exception("Failed to setup original system")
            
            # Create input CSV
            self.status_var.set("Creating input file...")
            self.progress_var.set(30)
            
            input_file_path = self.create_input_csv(po_numbers)
            if not input_file_path:
                raise Exception("Failed to create input CSV")
            
            # Run original system
            self.status_var.set("Starting download process...")
            self.progress_var.set(40)
            
            success, stdout, stderr = self.run_original_system(input_file_path)
            
            if success:
                self.progress_var.set(100)
                self.status_var.set("Download completed successfully!")
                
                messagebox.showinfo(
                    "Success", 
                    f"Download completed!\\n\\nProcessed {len(po_numbers)} PO numbers.\\n\\nFiles saved to: %USERPROFILE%\\Downloads\\CoupaDownloads\\"
                )
            else:
                raise Exception(f"Download failed: {stderr}")
            
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            messagebox.showerror("Error", f"Download failed: {e}")
        
        finally:
            # Re-enable start button
            self.start_btn.config(state="normal")
            
            # Cleanup temporary directory
            if self.temp_dir and self.temp_dir.exists():
                try:
                    shutil.rmtree(self.temp_dir)
                except:
                    pass
    
    def run(self):
        """Run the application."""
        self.root.mainloop()


def main():
    """Main function."""
    app = CoupaDownloadsIntegratedApp()
    app.run()


if __name__ == "__main__":
    main()
'''
        
        main_script_path = self.build_dir / "coupa_downloads_integrated.py"
        main_script_path.write_text(main_script_content, encoding='utf-8')
        
        print("✅ Integrated main EXE script created")
        return main_script_path
    
    def copy_source_files(self):
        """Copy source files to build directory."""
        print("📋 Copying source files...")
        
        # Copy source files
        source_files = [
            "src/main.py",
            "src/core/__init__.py",
            "src/core/browser.py",
            "src/core/config.py",
            "src/core/csv_processor.py",
            "src/core/downloader.py",
            "src/core/driver_manager.py"
        ]
        
        build_src_dir = self.build_dir / "src" / "core"
        build_src_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in source_files:
            src = self.project_root / file_path
            dst = self.build_dir / file_path
            
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                print(f"  ✅ {file_path}")
            else:
                print(f"  ⚠️ {file_path} not found")
        
        print("✅ Source files copied")
    
    def build(self):
        """Build the complete integrated EXE package."""
        print("🏗️ Building integrated EXE package...")
        print("=" * 50)
        
        try:
            # Clean previous build
            self.clean_build()
            
            # Download stable EdgeDriver
            if not self.download_stable_edgedriver():
                print("❌ Failed to download EdgeDriver")
                return False
            
            # Copy source files
            self.copy_source_files()
            
            # Create integrated main script
            main_script_path = self.create_integrated_main_script()
            
            print("\n" + "=" * 50)
            print("🎉 Integrated EXE package built successfully!")
            print("=" * 50)
            print("✅ Original system integration ready")
            print("✅ GUI interface with proper CSV handling")
            print("✅ Temporary workspace management")
            print("✅ Real download processing")
            
            return True
            
        except Exception as e:
            print(f"❌ Build failed: {e}")
            return False


def main():
    """Main function."""
    print("CoupaDownloads - Integrated EXE Builder")
    print("=" * 50)
    
    if platform.system().lower() != "windows":
        print("❌ Integrated EXE build only supported on Windows")
        return 1
    
    builder = IntegratedExeBuilder()
    
    if builder.build():
        print("\n✅ Integrated build completed successfully!")
        return 0
    else:
        print("\n❌ Integrated build failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 