<#
.SYNOPSIS
    Installer for Lichess Puzzle Viewer (Windows)
#>

param(
    [switch]$SkipRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$LICHESS_CSV_URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"
$CSV_FILE = "lichess_db_puzzle.csv"
$ZST_FILE = "lichess_db_puzzle.csv.zst"

function Test-Command {
    param([string]$Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host "=== Lichess Puzzle Viewer installer ===" -ForegroundColor Cyan

if (-not (Test-Command python)) {
    Write-Host "ERROR: 'python' not found. Please install Python 3.9+ from python.org and add it to PATH." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[1b] Checking GTK3 Runtime with Cairo..."
$gtk3Paths = @(
    "C:\Program Files\GTK3-Runtime\bin\cairo-2.dll",
    "C:\Program Files (x86)\GTK3-Runtime\bin\cairo-2.dll"
)
$gtk3Installed = $false
foreach ($path in $gtk3Paths) {
    if (Test-Path $path) {
        $gtk3Installed = $true
        break
    }
}
if (-not $gtk3Installed) {
    Write-Host "[ERROR] GTK3 Runtime with Cairo not found" -ForegroundColor Red
    Write-Host "[INFO] Install GTK3 Runtime from https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases"
    Write-Host "[INFO] After installation, restart the terminal and run this script again"
    exit 1
}
Write-Host "[OK] GTK3 Runtime found"
Write-Host ""

$PythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Python version: $PythonVersion"

if (-not (Test-Path .venv)) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Yellow
}

$venvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "ERROR: venv Python not found at $venvPython" -ForegroundColor Red
    exit 1
}

Write-Host "Upgrading pip..."
& $venvPython -m pip install --upgrade pip

Write-Host "Installing Python dependencies..."
& $venvPython -m pip install -r requirements.txt

if (-not (Test-Path $CSV_FILE)) {
    Write-Host "Downloading Lichess puzzle database..."
    Write-Host "URL: $LICHESS_CSV_URL"
    Write-Host "This may take a while (file is ~2GB compressed)..."
    
    if (-not (Test-Command curl)) {
        Write-Host "ERROR: curl not found. Please install curl and run again." -ForegroundColor Red
        exit 1
    }
    
    curl.exe -L -o $ZST_FILE $LICHESS_CSV_URL
    
    Write-Host "Decompressing CSV..."
    & $venvPython -c @"
import zstandard
import os
with open('$ZST_FILE', 'rb') as f_in:
    dctx = zstandard.ZstdDecompressor()
    with open('$CSV_FILE', 'wb') as f_out:
        dctx.copy_stream(f_in, f_out)
os.remove('$ZST_FILE')
"@
    
    Write-Host "CSV downloaded and decompressed: $CSV_FILE" -ForegroundColor Green
} else {
    Write-Host "CSV file '$CSV_FILE' already exists. Skipping download." -ForegroundColor Yellow
}

Write-Host ""
$build = Read-Host "Build executable now? (Y/N)"
if ($build -match '^[Yy]') {
    Write-Host "Building executable with PyInstaller..." -ForegroundColor Cyan
    
    $pyinstallerArgs = @(
        "--onefile",
        "--windowed",
        "--name", "Lichess Puzzle Viewer",
        "--add-data", "lichess_themes.json;.",
        "main.py"
    )
    
    if (Test-Path "icon.ico") {
        $pyinstallerArgs += @("--add-data", "icon.ico;.")
        $pyinstallerArgs += @("--icon", "icon.ico")
    }
    
    & $venvPython -m pyinstaller @pyinstallerArgs
    
    Write-Host ""
    Write-Host "Build complete!" -ForegroundColor Green
    Write-Host "Executable location: $ScriptDir\dist\Lichess Puzzle Viewer.exe"
    
    if (Test-Path "$ScriptDir\dist\Lichess Puzzle Viewer.exe") {
        Write-Host "[INFO] Copying data files to dist..."
        if (Test-Path "$ScriptDir\lichess_themes.json") {
            Copy-Item "$ScriptDir\lichess_themes.json" "$ScriptDir\dist\lichess_themes.json" -Force
            Write-Host "[OK] lichess_themes.json copied to dist"
        }
        if (Test-Path "$ScriptDir\icon.png") {
            Copy-Item "$ScriptDir\icon.png" "$ScriptDir\dist\icon.png" -Force
            Write-Host "[OK] icon.png copied to dist"
        }
        if (Test-Path "$ScriptDir\icon.ico") {
            Copy-Item "$ScriptDir\icon.ico" "$ScriptDir\dist\icon.ico" -Force
            Write-Host "[OK] icon.ico copied to dist"
        }
    }
} else {
    Write-Host "Skipping build."
}

Write-Host ""
Write-Host "=== Installation complete! ===" -ForegroundColor Green
Write-Host ""

Write-Host "To run the app:"
Write-Host "  .venv\Scripts\activate"
Write-Host "  python main.py"
Write-Host ""
Write-Host "CSV file: $ScriptDir\$CSV_FILE"
Write-Host "Database will be created on first import."

Write-Host ""
Write-Host "[CAIRO] GTK3 Runtime with Cairo is required for SVG pieces"
Write-Host "[INFO] If Cairo is not installed, unicode pieces will be used automatically"

if (-not $SkipRun) {
    $run = Read-Host "`nRun the app now? (Y/N)"
    if ($run -match '^[Yy]') {
        & $venvPython main.py
    }
}
