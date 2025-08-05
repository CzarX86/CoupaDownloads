#!/usr/bin/env python3
"""
Universal installer for CoupaDownloads
Works on Windows, macOS, and Linux
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path


def print_header():
    """Print installation header."""
    print("=" * 50)
    print("    CoupaDownloads - Universal Installer")
    print("=" * 50)
    print()


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} found")
    return True


def check_pip():
    """Check if pip is available."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      capture_output=True, check=True)
        print("✅ pip found")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ pip is not available")
        print("Please ensure pip is installed with Python")
        return False


def create_virtual_environment():
    """Create virtual environment if it doesn't exist."""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True
    
    print("📦 Creating virtual environment...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False


def get_venv_python():
    """Get the Python executable path in virtual environment."""
    if platform.system() == "Windows":
        return Path("venv/Scripts/python.exe")
    else:
        return Path("venv/bin/python")


def get_venv_pip():
    """Get the pip executable path in virtual environment."""
    if platform.system() == "Windows":
        return Path("venv/Scripts/pip.exe")
    else:
        return Path("venv/bin/pip")


def install_dependencies():
    """Install Python dependencies."""
    venv_pip = get_venv_pip()
    
    if not venv_pip.exists():
        print("❌ Virtual environment pip not found")
        return False
    
    print("⬆️ Upgrading pip...")
    try:
        subprocess.run([str(venv_pip), "install", "--upgrade", "pip"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Warning: Could not upgrade pip: {e}")
    
    print("📦 Installing Python dependencies...")
    try:
        subprocess.run([str(venv_pip), "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def create_directories():
    """Create necessary directories."""
    directories = [
        "data/input",
        "data/output", 
        "data/backups"
    ]
    
    print("📁 Creating necessary directories...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {directory}")


def create_sample_input():
    """Create sample input file if it doesn't exist."""
    input_file = Path("data/input/input.csv")
    
    if input_file.exists():
        print("✅ Sample input file already exists")
        return
    
    print("📝 Creating sample input file...")
    sample_content = """PO_NUMBER
PO15262984
PO15327452
PO15362783
"""
    
    try:
        input_file.write_text(sample_content, encoding='utf-8')
        print("✅ Sample input file created")
    except Exception as e:
        print(f"❌ Failed to create sample input file: {e}")


def check_edge_installation():
    """Check if Microsoft Edge is installed."""
    print("🔍 Checking Microsoft Edge installation...")
    
    system = platform.system()
    
    if system == "Windows":
        # Check Windows Store version
        try:
            result = subprocess.run([
                "powershell", "-Command", 
                "(Get-AppxPackage Microsoft.MicrosoftEdge.Stable).Version"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                version = result.stdout.strip()
                print(f"✅ Microsoft Edge found (Windows Store): {version}")
                return True
        except:
            pass
        
        # Check traditional installation
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]
        
        for path in edge_paths:
            if Path(path).exists():
                print(f"✅ Microsoft Edge found (Traditional): {path}")
                return True
    
    elif system == "Darwin":  # macOS
        edge_path = Path("/Applications/Microsoft Edge.app")
        if edge_path.exists():
            print("✅ Microsoft Edge found (macOS)")
            return True
    
    elif system == "Linux":
        edge_paths = [
            "/usr/bin/microsoft-edge",
            "/usr/bin/microsoft-edge-stable",
            "/opt/microsoft/msedge/microsoft-edge"
        ]
        
        for path in edge_paths:
            if Path(path).exists():
                print(f"✅ Microsoft Edge found (Linux): {path}")
                return True
    
    print("⚠️ Microsoft Edge not found")
    print("Please install Microsoft Edge from https://microsoft.com/edge")
    print("The tool will attempt to download the driver anyway...")
    return False


def print_success_message():
    """Print success message with next steps."""
    print()
    print("=" * 50)
    print("    Installation Complete! 🎉")
    print("=" * 50)
    print()
    print("📋 Next steps:")
    print("1. Edit data/input/input.csv with your PO numbers")
    print("2. Activate virtual environment and run the tool")
    print()
    print("💡 The tool will automatically:")
    print("   - Download the correct EdgeDriver")
    print("   - Open Microsoft Edge")
    print("   - Wait for you to log in to Coupa")
    print("   - Download attachments from your POs")
    print()
    
    # Platform-specific instructions
    system = platform.system()
    if system == "Windows":
        print("🚀 Quick start (Windows):")
        print("   venv\\Scripts\\activate")
        print("   python src\\main.py")
        print()
        print("📁 Downloads will be saved to: %USERPROFILE%\\Downloads\\CoupaDownloads\\")
    else:
        print("🚀 Quick start:")
        print("   source venv/bin/activate")
        print("   python src/main.py")
        print()
        print("📁 Downloads will be saved to: ~/Downloads/CoupaDownloads/")


def main():
    """Main installation function."""
    print_header()
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Check pip
    if not check_pip():
        return 1
    
    # Create virtual environment
    if not create_virtual_environment():
        return 1
    
    # Install dependencies
    if not install_dependencies():
        return 1
    
    # Create directories
    create_directories()
    
    # Create sample input
    create_sample_input()
    
    # Check Edge installation
    check_edge_installation()
    
    # Print success message
    print_success_message()
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 