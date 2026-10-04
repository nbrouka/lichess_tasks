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
Write-Host "[CAIRO] Checking for Cairo library..."
$cairoInstalled = $false
if (Get-Command cairo-2.dll -ErrorAction SilentlyContinue) { $cairoInstalled = $true }
if (Get-Command libcairo-2.dll -ErrorAction SilentlyContinue) { $cairoInstalled = $true }
Write-Host "[DEBUG] CAIRO_INSTALLED=$cairoInstalled"

if (-not $cairoInstalled) {
    Write-Host "[WARN] Cairo library not found. SVG pieces will not work without it." -ForegroundColor Yellow
    Write-Host ""
    $installCairo = Read-Host "Install Cairo automatically now? (Y/N)"
    if ($installCairo -match '^[Yy]') {
        Write-Host "[INFO] Trying to install Cairo..."
        $is64Bit = [Environment]::Is64BitOperatingSystem
        Write-Host "[DEBUG] OS architecture: $(if ($is64Bit) { 'x64' } else { 'x86' })"
        
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host "[INFO] winget found, installing GTK3 Runtime..."
            winget install -e --id GnuWin32.Cairo --accept-source-agreements --accept-package-agreements
        } elseif (Get-Command choco -ErrorAction SilentlyContinue) {
            Write-Host "[INFO] Chocolatey found, installing cairo..."
            choco install cairo -y
        } elseif (Get-Command scoop -ErrorAction SilentlyContinue) {
            Write-Host "[INFO] Scoop found, installing cairo..."
            scoop install cairo
        } else {
            Write-Host "[INFO] Neither winget/Chocolatey/Scoop found. Downloading GTK3 Runtime..."
            $gtkUrl = if ($is64Bit) {
                "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/latest/gtk3-runtime-3.24.37-2023-05-11-ts-win64.exe"
            } else {
                "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/latest/gtk3-runtime-3.24.37-2023-05-11-ts-win32.exe"
            }
            $gtkInstaller = Join-Path $env:TEMP "gtk3-runtime.exe"
            Invoke-WebRequest -Uri $gtkUrl -OutFile $gtkInstaller -UseBasicParsing
            if (Test-Path $gtkInstaller) {
                Write-Host "[OK] Download complete"
                Write-Host "[INFO] Installing Cairo silently..."
                if ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
                    Start-Process -FilePath $gtkInstaller -ArgumentList "/S" -Wait
                } else {
                    $installPath = Join-Path $env:LOCALAPPDATA "GTK3-Runtime"
                    Start-Process -FilePath $gtkInstaller -ArgumentList "/S","/D=$installPath" -Wait
                }
                Write-Host "[OK] Installation completed"
                $cairoBin = "C:\Program Files\GTK3-Runtime\bin"
                if (-not (Test-Path "$cairoBin\cairo-2.dll")) {
                    $cairoBin = Join-Path $env:LOCALAPPDATA "GTK3-Runtime\bin"
                }
                if (Test-Path "$cairoBin\cairo-2.dll") {
                    Write-Host "[OK] Cairo found at $cairoBin"
                    Copy-Item "$cairoBin\cairo-2.dll" "$ScriptDir\dist\" -Force
                    Write-Host "[OK] cairo-2.dll copied to dist"
                    Copy-Item "$cairoBin\libcairo-2.dll" "$ScriptDir\dist\" -Force
                    Write-Host "[OK] libcairo-2.dll copied to dist"
                } else {
                    Write-Host "[ERROR] Cairo installation failed or cairo-2.dll not found" -ForegroundColor Red
                }
            } else {
                Write-Host "[ERROR] Failed to download Cairo runtime" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "[INFO] Skipping Cairo installation. Unicode pieces will be used instead."
    }
} else {
    Write-Host "[OK] Cairo library found"
}

if (-not $SkipRun) {
    $run = Read-Host "`nRun the app now? (Y/N)"
    if ($run -match '^[Yy]') {
        & $venvPython main.py
    }
}
