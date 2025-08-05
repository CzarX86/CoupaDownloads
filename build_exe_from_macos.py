#!/usr/bin/env python3
"""
Build EXE from macOS for Windows
Uses Docker to create Windows executable from macOS
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


class MacOSExeBuilder:
    """Builds Windows EXE from macOS using Docker."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.build_dir = self.project_root / "build"
        self.docker_dir = self.build_dir / "docker_build"
        
    def check_docker(self):
        """Check if Docker is available."""
        print("🐳 Checking Docker installation...")
        
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Docker found: {result.stdout.strip()}")
                return True
            else:
                print("❌ Docker not found")
                return False
        except FileNotFoundError:
            print("❌ Docker not installed")
            return False
    
    def create_dockerfile(self):
        """Create Dockerfile for Windows build."""
        print("📝 Creating Dockerfile...")
        
        dockerfile_content = '''# Use Windows Server Core with Python
FROM mcr.microsoft.com/windows/servercore:ltsc2019

# Set working directory
WORKDIR C:\\app

# Download and install Python
RUN powershell -Command \\
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe" -OutFile "python.exe" && \\
    .\\python.exe /quiet InstallAllUsers=1 PrependPath=1 && \\
    del python.exe

# Install PyInstaller
RUN pip install pyinstaller requests

# Copy source files
COPY . .

# Build executable
RUN python build_single_exe.py

# Copy result to output directory
RUN mkdir C:\\output && \\
    copy "build\\dist\\CoupaDownloads.exe" C:\\output\\

# Set output volume
VOLUME C:\\output
'''
        
        dockerfile_path = self.docker_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content, encoding='utf-8')
        
        print("✅ Dockerfile created")
        return dockerfile_path
    
    def create_docker_compose(self):
        """Create docker-compose.yml for easier build."""
        print("📋 Creating docker-compose.yml...")
        
        compose_content = '''version: '3.8'

services:
  windows-builder:
    build: .
    volumes:
      - ./output:/output
    command: cmd /c "copy C:\\output\\CoupaDownloads.exe C:\\output\\ && exit"
'''
        
        compose_path = self.docker_dir / "docker-compose.yml"
        compose_path.write_text(compose_content, encoding='utf-8')
        
        print("✅ docker-compose.yml created")
        return compose_path
    
    def create_build_script(self):
        """Create build script for macOS."""
        print("🚀 Creating build script...")
        
        script_content = '''#!/bin/bash

echo "🏗️ Building Windows EXE from macOS..."
echo "======================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Create output directory
mkdir -p output

# Build Docker image
echo "🐳 Building Docker image..."
docker build -t coupa-downloads-builder .

# Run container and copy files
echo "📦 Running build container..."
docker run --rm -v "$(pwd)/output:/output" coupa-downloads-builder

# Check if build was successful
if [ -f "output/CoupaDownloads.exe" ]; then
    echo "✅ Build successful!"
    echo "📁 Executable: output/CoupaDownloads.exe"
    echo "📊 Size: $(ls -lh output/CoupaDownloads.exe | awk '{print $5}')"
else
    echo "❌ Build failed!"
    exit 1
fi

echo "🎉 Windows EXE created successfully!"
'''
        
        script_path = self.docker_dir / "build.sh"
        script_path.write_text(script_content)
        os.chmod(script_path, 0o755)
        
        print("✅ Build script created")
        return script_path
    
    def create_simple_build_script(self):
        """Create a simpler build script using Wine."""
        print("🍷 Creating Wine build script...")
        
        script_content = '''#!/bin/bash

echo "🍷 Building Windows EXE using Wine..."
echo "======================================"

# Check if Wine is installed
if ! command -v wine > /dev/null 2>&1; then
    echo "❌ Wine is not installed."
    echo "Install with: brew install --cask wine-stable"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 > /dev/null 2>&1; then
    echo "❌ Python 3 is not installed."
    exit 1
fi

# Create build directory
mkdir -p build
cd build

# Download Python for Windows
echo "📥 Downloading Python for Windows..."
PYTHON_URL="https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe"
curl -L -o python-installer.exe "$PYTHON_URL"

# Install Python in Wine
echo "🍷 Installing Python in Wine..."
wine python-installer.exe /quiet InstallAllUsers=1 PrependPath=1

# Install PyInstaller
echo "📦 Installing PyInstaller..."
wine python -m pip install pyinstaller requests

# Copy source files
echo "📋 Copying source files..."
cp -r ../src .
cp -r ../requirements.txt .

# Build executable
echo "🏗️ Building executable..."
wine python build_single_exe.py

# Copy result
if [ -f "dist/CoupaDownloads.exe" ]; then
    cp dist/CoupaDownloads.exe ../output/
    echo "✅ Build successful!"
    echo "📁 Executable: output/CoupaDownloads.exe"
else
    echo "❌ Build failed!"
    exit 1
fi

echo "🎉 Windows EXE created successfully!"
'''
        
        script_path = self.docker_dir / "build_wine.sh"
        script_path.write_text(script_content)
        os.chmod(script_path, 0o755)
        
        print("✅ Wine build script created")
        return script_path
    
    def create_github_actions_workflow(self):
        """Create GitHub Actions workflow for automated builds."""
        print("🤖 Creating GitHub Actions workflow...")
        
        workflow_content = '''name: Build Windows EXE

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build-windows:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller
    
    - name: Build executable
      run: python build_single_exe.py
    
    - name: Setup security
      run: python security_setup.py
    
    - name: Upload artifact
      uses: actions/upload-artifact@v3
      with:
        name: CoupaDownloads-Windows
        path: build/dist/CoupaDownloads.exe
        retention-days: 30
    
    - name: Create release
      if: github.ref == 'refs/heads/main'
      uses: softprops/action-gh-release@v1
      with:
        files: build/dist/CoupaDownloads.exe
        tag_name: v${{ github.run_number }}
        name: Release v${{ github.run_number }}
        body: |
          Windows EXE build for CoupaDownloads
          
          - Single executable file
          - All dependencies included
          - Digital signature applied
          - Security checksums provided
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
'''
        
        workflows_dir = self.project_root / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        workflow_path = workflows_dir / "build-windows.yml"
        workflow_path.write_text(workflow_content, encoding='utf-8')
        
        print("✅ GitHub Actions workflow created")
        return workflow_path
    
    def create_readme(self):
        """Create README for building from macOS."""
        print("📝 Creating build README...")
        
        readme_content = '''# Building Windows EXE from macOS

## 🚀 Quick Start

### Option 1: GitHub Actions (Recommended)

1. **Push** your code to GitHub
2. **Check** Actions tab for automated build
3. **Download** the EXE from releases

### Option 2: Docker Build

```bash
# Navigate to docker build directory
cd build/docker_build

# Run build script
./build.sh

# Find EXE in output/ directory
```

### Option 3: Wine Build

```bash
# Install Wine
brew install --cask wine-stable

# Navigate to docker build directory
cd build/docker_build

# Run Wine build script
./build_wine.sh

# Find EXE in output/ directory
```

## 📋 Requirements

### For Docker Build:
- Docker Desktop installed and running
- 4GB+ RAM available

### For Wine Build:
- Wine installed (`brew install --cask wine-stable`)
- Python 3.8+ installed
- 2GB+ disk space

## 🔧 Troubleshooting

### Docker Issues:
- Ensure Docker Desktop is running
- Check available disk space
- Verify Docker has enough memory allocated

### Wine Issues:
- Install Wine: `brew install --cask wine-stable`
- Wine may take time to download Windows components
- First run may be slow

### Build Failures:
- Check internet connection
- Verify all source files are present
- Review build logs for specific errors

## 📁 Output

Successful builds create:
```
output/
└── CoupaDownloads.exe    # Windows executable
```

## 🎯 Next Steps

After building:
1. Test the EXE on a Windows machine
2. Run security setup if needed
3. Distribute to users

## 🤖 Automated Builds

GitHub Actions automatically builds the EXE on every push to main branch.
Check the Actions tab for build status and downloads.
'''
        
        readme_path = self.docker_dir / "README.md"
        readme_path.write_text(readme_content, encoding='utf-8')
        
        print("✅ Build README created")
    
    def setup_build_environment(self):
        """Setup the complete build environment."""
        print("🏗️ Setting up build environment...")
        print("=" * 50)
        
        try:
            # Create directories
            self.docker_dir.mkdir(parents=True, exist_ok=True)
            (self.project_root / "output").mkdir(exist_ok=True)
            
            # Check Docker
            docker_available = self.check_docker()
            
            # Create build files
            self.create_dockerfile()
            self.create_docker_compose()
            self.create_build_script()
            self.create_simple_build_script()
            self.create_github_actions_workflow()
            self.create_readme()
            
            print("\n" + "=" * 50)
            print("🎉 Build environment setup completed!")
            print("=" * 50)
            
            if docker_available:
                print("✅ Docker build available")
                print("🚀 Run: cd build/docker_build && ./build.sh")
            else:
                print("⚠️ Docker not available")
                print("🍷 Run: cd build/docker_build && ./build_wine.sh")
            
            print("🤖 GitHub Actions workflow created")
            print("📁 Push to GitHub for automated builds")
            
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False


def main():
    """Main function."""
    print("CoupaDownloads - macOS to Windows EXE Builder")
    print("=" * 50)
    
    if platform.system().lower() != "darwin":
        print("❌ This script is designed for macOS")
        return 1
    
    builder = MacOSExeBuilder()
    
    if builder.setup_build_environment():
        print("\n✅ Build environment setup completed successfully!")
        return 0
    else:
        print("\n❌ Build environment setup failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 