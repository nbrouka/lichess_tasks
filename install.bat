@echo off
chcp 65001 >nul
setlocal

echo ========================================
echo Lichess Puzzle Viewer installer
echo ========================================
echo [START] %DATE% %TIME%
echo [CWD] %CD%
echo.

echo [1] Checking python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] python not found
    pause
    exit /b 1
)
echo [OK] python found
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

echo [CAIRO] Checking for Cairo library...
set "CAIRO_INSTALLED=0"
where cairo-2.dll >nul 2>nul
if %errorlevel% equ 0 set "CAIRO_INSTALLED=1"
where libcairo-2.dll >nul 2>nul
if %errorlevel% equ 0 set "CAIRO_INSTALLED=1"
echo [DEBUG] CAIRO_INSTALLED=%CAIRO_INSTALLED%

if "%CAIRO_INSTALLED%"=="1" (
    echo [OK] Cairo library found
    goto after_cairo
)

echo [WARN] Cairo library not found. SVG pieces will not work without it.
echo.
echo [STEP] Install Cairo via package manager?
echo   Y - Install Cairo via Chocolatey or Scoop
echo   N - Skip (unicode pieces will be used instead)
echo.
set /p INSTALL_CAIRO=Install Cairo now? (Y/N):
echo [DEBUG] INSTALL_CAIRO input: "%INSTALL_CAIRO%"
if /i not "%INSTALL_CAIRO%"=="Y" goto skip_cairo

echo [INFO] Trying to install Cairo...

set "CAIRO_ARCH=win64"
if "%PROCESSOR_ARCHITECTURE%"=="AMD64" set "CAIRO_ARCH=win64"
if "%PROCESSOR_ARCHITECTURE%"=="x86" set "CAIRO_ARCH=win32"
echo [DEBUG] Detected architecture: %CAIRO_ARCH%

where winget >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] winget found, installing GTK3 Runtime...
    winget install -e --id GnuWin32.Cairo --accept-source-agreements --accept-package-agreements
    goto after_cairo_install
)

where choco >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Chocolatey found, installing cairo...
    choco install cairo -y
    goto after_cairo_install
)

where scoop >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Scoop found, installing cairo...
    scoop install cairo
    goto after_cairo_install
)

echo [INFO] Neither winget/Chocolatey/Scoop found. Downloading GTK4 Runtime with Cairo...
if "%CAIRO_ARCH%"=="win64" (
    echo [INFO] Downloading 64-bit GTK4 Runtime...
    curl.exe -L -o "%TEMP%\gtk4-runtime.exe" "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/latest/gtk4-runtime-4.16.1-2024-11-01-ts-win64.exe"
) else (
    echo [INFO] Downloading 32-bit GTK4 Runtime...
    curl.exe -L -o "%TEMP%\gtk4-runtime.exe" "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/latest/gtk4-runtime-4.16.1-2024-11-01-ts-win32.exe"
)
if not exist "%TEMP%\gtk4-runtime.exe" (
    echo [ERROR] Failed to download GTK4 runtime
    pause
    goto skip_cairo
)
echo [OK] Download complete

echo [INFO] Installing Cairo silently...
net session >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Administrator rights detected, installing system-wide...
    "%TEMP%\gtk4-runtime.exe" /S
) else (
    echo [WARN] No administrator rights. Installing to user profile...
    "%TEMP%\gtk4-runtime.exe" /S /D=%LOCALAPPDATA%\GTK4-Runtime
)
echo [OK] Installation completed

set "CAIRO_BIN=C:\Program Files\GTK4-Runtime\bin"
if not exist "%CAIRO_BIN%\cairo-2.dll" (
    set "CAIRO_BIN=%LOCALAPPDATA%\GTK4-Runtime\bin"
)
if exist "%CAIRO_BIN%\cairo-2.dll" (
    echo [OK] Cairo found at %CAIRO_BIN%
    copy /Y "%CAIRO_BIN%\cairo-2.dll" "dist\" >nul
    echo [OK] cairo-2.dll copied to dist
    copy /Y "%CAIRO_BIN%\libcairo-2.dll" "dist\" >nul
    echo [OK] libcairo-2.dll copied to dist
) else (
    echo [ERROR] Cairo installation failed or cairo-2.dll not found
    echo [INFO] Install Cairo manually:
    echo   - winget: winget install -e --id GnuWin32.Cairo
    echo   - Chocolatey: choco install cairo
    echo   - Scoop: scoop install cairo
    echo   - Or download GTK4 Runtime from https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
    pause
    goto skip_cairo
)

:after_cairo_install
echo [OK] Cairo installation completed
echo [INFO] You may need to restart the terminal or reinstall the executable for changes to take effect.

:skip_cairo
echo.

:after_cairo
echo.

echo [DONE] Installation complete!
echo To run the app:
echo   .venv\Scripts\activate
echo   python main.py
echo.
echo CSV file: %CD%\lichess_db_puzzle.csv
echo Database will be created on first import.
pause
