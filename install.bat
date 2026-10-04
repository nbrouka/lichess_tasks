@echo off
chcp 65001 >nul
setlocal

echo ========================================
echo Lichess Puzzle Viewer installer
echo ========================================
echo [START] %DATE% %TIME%
echo [CWD] %CD%
echo.

echo [1] Checking prerequisites...
echo.
echo [1a] Checking python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] python not found
    echo [INFO] Install Python 3.9+ from https://www.python.org/downloads/windows/ and add it to PATH
    pause
    exit /b 1
)
echo [OK] python found
echo.

echo [1b] Checking GTK3 Runtime with Cairo...
set "GTK3_INSTALLED=0"
where cairo-2.dll >nul 2>nul
if %errorlevel% equ 0 set "GTK3_INSTALLED=1"
if not exist "C:\Program Files\GTK3-Runtime\bin\cairo-2.dll" (
    if not exist "C:\Program Files (x86)\GTK3-Runtime\bin\cairo-2.dll" (
        if %GTK3_INSTALLED% equ 0 (
            echo [ERROR] GTK3 Runtime with Cairo not found
            echo [INFO] Install GTK3 Runtime from https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
            echo [INFO] After installation, restart the terminal and run this script again
            pause
            exit /b 1
        )
    )
)
echo [OK] GTK3 Runtime found
echo.

echo [2] Checking venv...
if not exist .venv (
    echo [INFO] venv not found, creating...
    python -m venv .venv
) else (
    echo [OK] venv already exists
)
echo.

echo [3] Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip
echo [OK] pip upgraded
echo.

echo [4] Installing dependencies...
.venv\Scripts\pip.exe install -r requirements.txt
echo [OK] dependencies installed
echo.

echo [5] Checking CSV file...
if exist lichess_db_puzzle.csv (
    echo [OK] CSV exists, skipping download
    goto skip_download
)
echo [INFO] CSV not found, starting download
echo [INFO] URL: https://database.lichess.org/lichess_db_puzzle.csv.zst

where curl >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] curl not found
    pause
    exit /b 1
)
echo [OK] curl found

echo [INFO] Downloading CSV (this may take a while)...
curl.exe -L -o lichess_db_puzzle.csv.zst https://database.lichess.org/lichess_db_puzzle.csv.zst
echo [OK] CSV downloaded

echo [INFO] Decompressing CSV...
.venv\Scripts\python.exe -c "import zstandard, os; f_in=open('lichess_db_puzzle.csv.zst','rb'); dctx=zstandard.ZstdDecompressor(); f_out=open('lichess_db_puzzle.csv','wb'); dctx.copy_stream(f_in,f_out); f_in.close(); f_out.close(); os.remove('lichess_db_puzzle.csv.zst')"
echo [OK] CSV decompressed

:skip_download
echo.

echo [6] Asking about PyInstaller build...
set /p BUILD=Build executable now? (Y/N):
echo [DEBUG] BUILD input: "%BUILD%"
if /i not "%BUILD%"=="Y" goto skip_build
echo [INFO] Building executable...

if exist icon.ico (
    echo [INFO] icon.ico found, building with icon
    .venv\Scripts\pyinstaller.exe --onefile --windowed --name "Lichess Puzzle Viewer" --add-data "lichess_themes.json;." --add-data "icon.ico;." --icon "icon.ico" main.py
    goto after_icon_build
)
echo [INFO] icon.ico not found, building without icon
.venv\Scripts\pyinstaller.exe --onefile --windowed --name "Lichess Puzzle Viewer" --add-data "lichess_themes.json;." main.py
:after_icon_build
echo [OK] PyInstaller finished
echo.

echo [7] Build result...
if exist "dist\Lichess Puzzle Viewer.exe" (
    echo [OK] Executable found: dist\Lichess Puzzle Viewer.exe
    echo [INFO] Copying data files to dist...
    if exist "lichess_themes.json" (
        copy /Y "lichess_themes.json" "dist\lichess_themes.json" >nul
        echo [OK] lichess_themes.json copied to dist
    )
    if exist "icon.png" (
        copy /Y "icon.png" "dist\icon.png" >nul
        echo [OK] icon.png copied to dist
    )
    if exist "icon.ico" (
        copy /Y "icon.ico" "dist\icon.ico" >nul
        echo [OK] icon.ico copied to dist
    )
) else (
    echo [ERROR] Executable NOT found: dist\Lichess Puzzle Viewer.exe
)
echo.

echo [8] Asking about desktop shortcut...
if exist "dist\Lichess Puzzle Viewer.exe" goto ask_shortcut
echo [ERROR] Executable not found, skipping shortcut creation
goto skip_shortcut

:ask_shortcut
echo [DEBUG] exe exists, asking about shortcut
set /p CREATE_SHORTCUT=Create desktop shortcut now? (Y/N):
echo [DEBUG] CREATE_SHORTCUT input: "%CREATE_SHORTCUT%"
if /i not "%CREATE_SHORTCUT%"=="Y" goto skip_shortcut
echo [INFO] Creating shortcut...
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Lichess Puzzle Viewer.lnk'); $Shortcut.TargetPath = '%CD%\dist\Lichess Puzzle Viewer.exe'; if (Test-Path '%CD%\icon.ico') { $Shortcut.IconLocation = '%CD%\icon.ico' }; $Shortcut.Save()"
echo [OK] Shortcut created

:skip_shortcut

:skip_build
echo.

echo [CAIRO] GTK3 Runtime with Cairo is required for SVG pieces
echo [INFO] If Cairo is not installed, unicode pieces will be used automatically
echo.

echo [DONE] Installation complete!
echo To run the app:
echo   .venv\Scripts\activate
echo   python main.py
echo.
echo CSV file: %CD%\lichess_db_puzzle.csv
echo Database will be created on first import.
pause
