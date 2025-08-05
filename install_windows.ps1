# CoupaDownloads - Windows PowerShell Installer
# Run as: PowerShell -ExecutionPolicy Bypass -File install_windows.ps1

param(
    [switch]$SkipPythonCheck,
    [switch]$SkipVirtualEnv,
    [switch]$Force
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   CoupaDownloads - Windows Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Check if Python is installed
if (-not $SkipPythonCheck) {
    if (-not (Test-Command "python")) {
        Write-Host "❌ Python is not installed or not in PATH" -ForegroundColor Red
        Write-Host "Please install Python from https://python.org" -ForegroundColor Yellow
        Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    Write-Host "✅ Python found" -ForegroundColor Green
    python --version
}

# Check if pip is available
if (-not (Test-Command "pip")) {
    Write-Host "❌ pip is not available" -ForegroundColor Red
    Write-Host "Please ensure pip is installed with Python" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ pip found" -ForegroundColor Green

# Create virtual environment if it doesn't exist
if (-not $SkipVirtualEnv) {
    if (-not (Test-Path "venv") -or $Force) {
        Write-Host ""
        Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
        python -m venv venv
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
        Write-Host "✅ Virtual environment created" -ForegroundColor Green
    } else {
        Write-Host "✅ Virtual environment already exists" -ForegroundColor Green
    }
}

# Activate virtual environment
Write-Host ""
Write-Host "🔄 Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to activate virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Upgrade pip
Write-Host ""
Write-Host "⬆️ Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install requirements
Write-Host ""
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Create necessary directories
Write-Host ""
Write-Host "📁 Creating necessary directories..." -ForegroundColor Yellow
$directories = @("data\input", "data\output", "data\backups")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Green
    }
}

# Create sample input file if it doesn't exist
if (-not (Test-Path "data\input\input.csv") -or $Force) {
    Write-Host ""
    Write-Host "📝 Creating sample input file..." -ForegroundColor Yellow
    @"
PO_NUMBER
PO15262984
PO15327452
PO15362783
"@ | Out-File -FilePath "data\input\input.csv" -Encoding UTF8
    Write-Host "✅ Sample input file created" -ForegroundColor Green
}

# Check if Microsoft Edge is installed
Write-Host ""
Write-Host "🔍 Checking Microsoft Edge installation..." -ForegroundColor Yellow
$edgeInstalled = $false

# Check Windows Store version
try {
    $edgePackage = Get-AppxPackage -Name "Microsoft.MicrosoftEdge.Stable" -ErrorAction SilentlyContinue
    if ($edgePackage) {
        Write-Host "✅ Microsoft Edge found (Windows Store version)" -ForegroundColor Green
        Write-Host "  Version: $($edgePackage.Version)" -ForegroundColor Gray
        $edgeInstalled = $true
    }
} catch {
    # Ignore errors
}

# Check traditional installation
if (-not $edgeInstalled) {
    $edgePaths = @(
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe"
    )
    
    foreach ($path in $edgePaths) {
        if (Test-Path $path) {
            Write-Host "✅ Microsoft Edge found (Traditional installation)" -ForegroundColor Green
            Write-Host "  Path: $path" -ForegroundColor Gray
            $edgeInstalled = $true
            break
        }
    }
}

if (-not $edgeInstalled) {
    Write-Host "⚠️ Microsoft Edge not found" -ForegroundColor Yellow
    Write-Host "Please install Microsoft Edge from https://microsoft.com/edge" -ForegroundColor Yellow
    Write-Host "The tool will attempt to download the driver anyway..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Installation Complete! 🎉" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor White
Write-Host "1. Edit data\input\input.csv with your PO numbers" -ForegroundColor Gray
Write-Host "2. Run: python src\main.py" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 The tool will automatically:" -ForegroundColor White
Write-Host "   - Download the correct EdgeDriver" -ForegroundColor Gray
Write-Host "   - Open Microsoft Edge" -ForegroundColor Gray
Write-Host "   - Wait for you to log in to Coupa" -ForegroundColor Gray
Write-Host "   - Download attachments from your POs" -ForegroundColor Gray
Write-Host ""
Write-Host "📁 Downloads will be saved to: $env:USERPROFILE\Downloads\CoupaDownloads\" -ForegroundColor Gray
Write-Host ""
Write-Host "🚀 Quick start:" -ForegroundColor White
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "   python src\main.py" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to exit" 