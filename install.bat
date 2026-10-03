@echo off
chcp 65001 >nul
setlocal

echo === Lichess Puzzle Viewer installer ===
echo [DEBUG] Starting installer at %DATE% %TIME%

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] python not found. Install Python 3.9+ and add it to PATH.
    pause
    exit /b 1
)
echo [DEBUG] python found

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
) else (
    echo Virtual environment already exists.
)
echo [DEBUG] venv ready

echo Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip
echo [DEBUG] pip upgraded

echo Installing dependencies...
.venv\Scripts\pip.exe install -r requirements.txt
echo [DEBUG] dependencies installed

echo.
echo [STEP] Checking CSV file...
if exist lichess_db_puzzle.csv (
    echo [INFO] CSV file already exists. Skipping download.
) else (
    echo [STEP] Downloading Lichess puzzle database...
    echo [INFO] URL: https://database.lichess.org/lichess_db_puzzle.csv.zst
    echo [INFO] This may take a while (file is ~2GB compressed)...

    where curl >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] curl not found. Please install curl and run again.
        pause
        exit /b 1
    )
    echo [DEBUG] curl found

    curl.exe -L -o lichess_db_puzzle.csv.zst https://database.lichess.org/lichess_db_puzzle.csv.zst
    echo [DEBUG] CSV downloaded

    echo Decompressing CSV...
    .venv\Scripts\python.exe -c "import zstandard, os; f_in=open('lichess_db_puzzle.csv.zst','rb'); dctx=zstandard.ZstdDecompressor(); f_out=open('lichess_db_puzzle.csv','wb'); dctx.copy_stream(f_in,f_out); f_in.close(); f_out.close(); os.remove('lichess_db_puzzle.csv.zst')"
    echo [DEBUG] CSV decompressed
)

echo.
echo [STEP] Asking about PyInstaller build...
set /p BUILD=Build executable now? (Y/N):
echo [DEBUG] BUILD answer: %BUILD%
if /i not "%BUILD%"=="Y" goto skip_build

echo [STEP] Building executable with PyInstaller...
echo [DEBUG] PyInstaller command will be executed now

if exist icon.ico (
    echo [DEBUG] icon.ico found, building with icon
    .venv\Scripts\pyinstaller.exe --onefile --windowed --name "Lichess Puzzle Viewer" --add-data "lichess_themes.json;." --add-data "icon.ico;." --icon "icon.ico" main.py
) else (
    echo [DEBUG] icon.ico not found, building without icon
    .venv\Scripts\pyinstaller.exe --onefile --windowed --name "Lichess Puzzle Viewer" --add-data "lichess_themes.json;." main.py
)
echo [DEBUG] PyInstaller finished

echo.
echo Build complete!
echo Executable location: %CD%\dist\Lichess Puzzle Viewer.exe

echo.
echo [STEP] Asking about desktop shortcut...
if exist "dist\Lichess Puzzle Viewer.exe" (
    echo [DEBUG] Executable found at dist\Lichess Puzzle Viewer.exe
    set /p CREATE_SHORTCUT=Create desktop shortcut now? (Y/N):
    echo [DEBUG] CREATE_SHORTCUT answer: %CREATE_SHORTCUT%
    if /i "%CREATE_SHORTCUT%"=="Y" (
        echo [DEBUG] Creating shortcut via PowerShell...
        powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Lichess Puzzle Viewer.lnk'); $Shortcut.TargetPath = '%CD%\dist\Lichess Puzzle Viewer.exe'; if (Test-Path '%CD%\icon.ico') { $Shortcut.IconLocation = '%CD%\icon.ico' }; $Shortcut.Save()"
        echo [DEBUG] Shortcut created
        echo Desktop shortcut created!
    )
) else (
    echo [ERROR] Executable not found, skipping shortcut creation.
)

:skip_build

echo.
echo [DONE] Installation complete!
echo To run the app:
echo   .venv\Scripts\activate
echo   python main.py
echo.
echo CSV file: %CD%\lichess_db_puzzle.csv
echo Database will be created on first import.
pause
