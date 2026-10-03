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

set /p BUILD=Build executable now? (Y/N):
if /i not "%BUILD%"=="Y" goto :skip_build

echo Building executable with PyInstaller...

set PYINSTALLER_ARGS=--onefile --windowed --name "Lichess Puzzle Viewer" --add-data "lichess_themes.json;." main.py
if exist icon.ico (
    set PYINSTALLER_ARGS=%PYINSTALLER_ARGS% --add-data "icon.ico;." --icon "icon.ico"
)

.venv\Scripts\pyinstaller.exe %PYINSTALLER_ARGS%

echo.
echo Build complete!
echo Executable location: %CD%\dist\Lichess Puzzle Viewer.exe

if exist "dist\Lichess Puzzle Viewer.exe" (
    echo.
    set /p CREATE_SHORTCUT=Create desktop shortcut now? (Y/N):
    if /i "%CREATE_SHORTCUT%"=="Y" (
        powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Lichess Puzzle Viewer.lnk'); $Shortcut.TargetPath = '%CD%\dist\Lichess Puzzle Viewer.exe'; if (Test-Path '%CD%\icon.ico') { $Shortcut.IconLocation = '%CD%\icon.ico' }; $Shortcut.Save()"
        echo Desktop shortcut created!
    )
)

:skip_build

echo.
echo Installation complete!
echo To run the app:
echo   .venv\Scripts\activate
echo   python main.py
echo.
echo CSV file: %CD%\lichess_db_puzzle.csv
echo Database will be created on first import.
pause
