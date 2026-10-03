#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LICHESS_CSV_URL="https://database.lichess.org/lichess_db_puzzle.csv.zst"
CSV_FILE="lichess_db_puzzle.csv"
ZST_FILE="lichess_db_puzzle.csv.zst"

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "ERROR: '$1' not found. Please install it first."
        exit 1
    fi
}

install_system_deps() {
    echo "Checking system dependencies..."
    
    if command -v apt-get &> /dev/null; then
        echo "Detected Debian/Ubuntu. Installing system packages..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq python3-venv python3-pip python3-tk \
                                  libjpeg-dev zlib1g-dev libcairo2 \
                                  zstd curl
    elif command -v dnf &> /dev/null; then
        echo "Detected Fedora. Installing system packages..."
        sudo dnf install -y python3-tkinter libjpeg-turbo-devel zlib-devel \
                           cairo-devel zstd curl
    elif command -v pacman &> /dev/null; then
        echo "Detected Arch Linux. Installing system packages..."
        sudo pacman -S --noconfirm tk libjpeg-turbo cairo zstd curl
    elif command -v brew &> /dev/null; then
        echo "Detected macOS. Installing system packages..."
        brew install python-tk cairo zstd curl
    else
        echo "WARNING: Unknown package manager. Please install manually:"
        echo "  - Python 3.9+ with tkinter"
        echo "  - libjpeg, zlib, cairo"
        echo "  - zstd, curl"
    fi
}

download_lichess_csv() {
    if [ -f "$CSV_FILE" ]; then
        echo "CSV file '$CSV_FILE' already exists. Skipping download."
        return
    fi
    
    echo "Downloading Lichess puzzle database..."
    echo "URL: $LICHESS_CSV_URL"
    echo "This may take a while (file is ~2GB compressed)..."
    
    if ! command -v curl &> /dev/null; then
        echo "ERROR: curl not found. Please install curl and run again."
        exit 1
    fi
    
    curl -L -o "$ZST_FILE" "$LICHESS_CSV_URL"
    
    echo "Decompressing CSV..."
    if command -v zstd &> /dev/null; then
        zstd -d "$ZST_FILE" -o "$CSV_FILE"
        rm "$ZST_FILE"
    else
        echo "zstd not found, using Python to decompress..."
        python3 -c "
import zstandard
with open('$ZST_FILE', 'rb') as f_in:
    dctx = zstandard.ZstdDecompressor()
    with open('$CSV_FILE', 'wb') as f_out:
        dctx.copy_stream(f_in, f_out)
import os
os.remove('$ZST_FILE')
"
    fi
    
    echo "CSV downloaded and decompressed: $CSV_FILE"
}

build_executable() {
    echo ""
    read -p "Build executable now? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping build."
        return
    fi
    
    echo "Building executable with PyInstaller..."
    
    PYINSTALLER_ARGS=(
        --onefile
        --windowed
        --name "Lichess Puzzle Viewer"
        --add-data "lichess_themes.json:."
        main.py
    )
    
    if [ -f "icon.png" ]; then
        PYINSTALLER_ARGS+=(--add-data "icon.png:.")
        PYINSTALLER_ARGS+=(--icon "icon.png")
    fi
    
    pyinstaller "${PYINSTALLER_ARGS[@]}"
    
    echo ""
    echo "Build complete!"
    echo "Executable location: $SCRIPT_DIR/dist/Lichess Puzzle Viewer"
    
    if [ -f "$SCRIPT_DIR/dist/Lichess Puzzle Viewer" ] && [ -f "$SCRIPT_DIR/icon.png" ]; then
        echo ""
        echo "Creating desktop shortcut..."
        DESKTOP_FILE="$HOME/.local/share/applications/lichess-puzzle-viewer.desktop"
        mkdir -p "$(dirname "$DESKTOP_FILE")"
        chmod +x "$SCRIPT_DIR/dist/Lichess Puzzle Viewer" 2>/dev/null || true
        cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=Lichess Puzzle Viewer
Exec="$SCRIPT_DIR/dist/Lichess Puzzle Viewer"
Icon=$SCRIPT_DIR/icon.png
Terminal=false
Categories=Game;BoardGame;
EOF
        chmod +x "$DESKTOP_FILE"
        echo "Menu shortcut created: $DESKTOP_FILE"
        
        echo ""
        read -p "Create desktop shortcut on ~/Desktop? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            USER_DESKTOP="$HOME/Desktop/Lichess Puzzle Viewer.desktop"
            cat > "$USER_DESKTOP" << EOF
[Desktop Entry]
Type=Application
Name=Lichess Puzzle Viewer
Exec="$SCRIPT_DIR/dist/Lichess Puzzle Viewer"
Icon=$SCRIPT_DIR/icon.png
Terminal=false
Categories=Game;BoardGame;
EOF
            chmod +x "$USER_DESKTOP"
            echo "Desktop shortcut created: $USER_DESKTOP"
            if command -v gio &> /dev/null; then
                gio set "$USER_DESKTOP" metadata::trusted true 2>/dev/null || true
                echo "Shortcut marked as trusted."
            else
                echo "If it does not appear, run: update-desktop-database ~/.local/share/applications"
                echo "Or right-click the icon and select 'Allow Launching'."
            fi
        fi
    fi
}

echo "=== Lichess Puzzle Viewer installer ==="

check_command python3
check_command pip3

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: $PYTHON_VERSION"

install_system_deps

download_lichess_csv

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing Python dependencies..."
pip install -r requirements.txt

build_executable

echo ""
echo "=== Installation complete! ==="
echo ""
echo "To run the app:"
echo "  source .venv/bin/activate"
echo "  python main.py"
echo ""
echo "CSV file: $SCRIPT_DIR/$CSV_FILE"
echo "Database will be created on first import."
