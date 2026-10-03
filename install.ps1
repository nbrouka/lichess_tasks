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
        Write-Host ""
        $createShortcut = Read-Host "Create desktop shortcut now? (Y/N)"
        if ($createShortcut -match '^[Yy]') {
            $WshShell = New-Object -comObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut("$Home\Desktop\Lichess Puzzle Viewer.lnk")
            $Shortcut.TargetPath = "$ScriptDir\dist\Lichess Puzzle Viewer.exe"
            if (Test-Path "$ScriptDir\icon.ico") {
                $Shortcut.IconLocation = "$ScriptDir\icon.ico"
            }
            $Shortcut.Save()
            Write-Host "Desktop shortcut created!" -ForegroundColor Green
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

if (-not $SkipRun) {
    $run = Read-Host "`nRun the app now? (Y/N)"
    if ($run -match '^[Yy]') {
        & $venvPython main.py
    }
}
