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

Write-Host "=== Lichess Puzzle Viewer installer ===" -ForegroundColor Cyan

function Test-Command {
    param([string]$Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

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

Write-Host "Activating virtual environment..."
$venvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "ERROR: venv Python not found at $venvPython" -ForegroundColor Red
    exit 1
}

Write-Host "Upgrading pip..."
& $venvPython -m pip install --upgrade pip

Write-Host "Installing dependencies..."
& $venvPython -m pip install -r requirements.txt

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "To run the app:"
Write-Host "  .venv\Scripts\activate"
Write-Host "  python main.py"

if (-not $SkipRun) {
    $run = Read-Host "`nRun the app now? (Y/N)"
    if ($run -match '^[Yy]') {
        & $venvPython main.py
    }
}
