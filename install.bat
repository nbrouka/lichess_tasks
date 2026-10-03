@echo off
chcp 65001 >nul
setlocal

echo === Lichess Puzzle Viewer installer ===

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: python not found. Install Python 3.9+ and add it to PATH.
    pause
    exit /b 1
)

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
) else (
    echo Virtual environment already exists.
)

echo Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip

echo Installing dependencies...
.venv\Scripts\pip.exe install -r requirements.txt

echo.
echo Installation complete!
echo To run the app:
echo   .venv\Scripts\activate
echo   python main.py
pause
