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

if not exist lichess_db_puzzle.csv (
    echo Downloading Lichess puzzle database...
    echo URL: https://database.lichess.org/lichess_db_puzzle.csv.zst
    echo This may take a while (file is ~2GB compressed)...
    
    where curl >nul 2>nul
    if %errorlevel% neq 0 (
        echo ERROR: curl not found. Please install curl and run again.
        pause
        exit /b 1
    )
    
    curl.exe -L -o lichess_db_puzzle.csv.zst https://database.lichess.org/lichess_db_puzzle.csv.zst
    
    echo Decompressing CSV...
    .venv\Scripts\python.exe -c "import zstandard, os; f_in=open('lichess_db_puzzle.csv.zst','rb'); dctx=zstandard.ZstdDecompressor(); f_out=open('lichess_db_puzzle.csv','wb'); dctx.copy_stream(f_in,f_out); f_in.close(); f_out.close(); os.remove('lichess_db_puzzle.csv.zst')"
    
    echo CSV downloaded and decompressed.
) else (
    echo CSV file already exists. Skipping download.
)

echo.
echo Installation complete!
echo To run the app:
echo   .venv\Scripts\activate
echo   python main.py
echo.
echo CSV file: %CD%\lichess_db_puzzle.csv
echo Database will be created on first import.
pause
