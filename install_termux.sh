#!/data/data/com.termux/files/usr/bin/bash
# Ethical OSINT Tracker — Termux Installation Script
# For Android devices using the Termux terminal emulator

set -e

echo "===================================="
echo "Ethical OSINT Tracker — Termux Setup"
echo "===================================="
echo ""

# Check if running in Termux
if [ ! -d "/data/data/com.termux" ]; then
    echo "Error: This script must be run inside Termux."
    echo "Install Termux from F-Droid: https://f-droid.org/en/packages/com.termux/"
    exit 1
fi

echo "Termux environment detected."
echo ""

# Update package lists
echo "Updating Termux packages..."
pkg update -y
pkg upgrade -y

# Install required system packages (native libs needed by Pillow, etc.)
echo "Installing system dependencies..."

# Build toolchain
pkg install -y \
    clang \
    binutils \
    make \
    patchelf \
    rust

# Python runtime
pkg install -y \
    python \
    python-pip

# Image libraries — required by Pillow for JPEG/PNG/TIFF/WebP/GIF forensics
pkg install -y \
    libjpeg-turbo \
    libpng \
    libtiff \
    libwebp \
    freetype \
    zlib \
    openjpeg

# XML/HTML parsing — required by python-docx and beautifulsoup4
pkg install -y \
    libxml2 \
    libxslt

# Crypto — libffi required by argon2-cffi (password hashing)
pkg install -y \
    libffi \
    openssl

# Utilities
pkg install -y \
    git \
    tmux

echo "System packages installed."
echo ""

PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "Python $PYTHON_VERSION detected."

# Storage access for image uploads
echo "Setting up storage access..."
echo "  Press 'Allow' when prompted."
termux-setup-storage
sleep 2
echo "Storage access configured."
echo ""

# Must be run from the project directory
if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found."
    echo "Please cd into the Ethical-OSINT-Tracker directory first, then re-run this script."
    exit 1
fi

VENV_DIR=".venv"
PIP="$VENV_DIR/bin/pip"
PYTHON_VENV="$VENV_DIR/bin/python"

# Create virtual environment
echo "Creating Python virtual environment..."
python -m venv "$VENV_DIR"
echo "Virtual environment created at $VENV_DIR"
echo ""

# Install into venv using explicit venv pip — no source/activate needed for installation
echo "Upgrading pip inside venv..."
"$PIP" install --upgrade pip

echo "Installing Python packages (this may take a few minutes on Termux)..."
"$PIP" install -r requirements.txt
echo "Python packages installed."
echo ""

# Initialise database and admin user using venv Python
echo "Initialising database..."
"$PYTHON_VENV" reset_admin.py
echo ""

# Optional environment config file
echo "Creating environment configuration..."
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Optional overrides — the app works without these
# SECRET_KEY=your-secret-key-here
# DB_URL=sqlite:///./dev.db
EOF
    echo ".env file created."
else
    echo ".env file already exists — skipping."
fi
echo ""

# Convenience launch script (uses source/activate for the runtime session)
echo "Creating launch script..."
cat > run_termux.sh << 'LAUNCH'
#!/data/data/com.termux/files/usr/bin/bash
# Launch Ethical OSINT Tracker on Termux

cd "$(dirname "$0")"

VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Run install_termux.sh first."
    exit 1
fi

# Activate for the runtime session so Flask and all imports resolve correctly
source "$VENV_DIR/bin/activate"

# Kill any existing process on port 3000
fuser -k 3000/tcp 2>/dev/null || true

echo "Starting Ethical OSINT Tracker..."
echo "Open http://localhost:3000 in your browser"
echo "Press Ctrl+C to stop"
echo ""

python run.py
LAUNCH

chmod +x run_termux.sh
echo "Launch script created: ./run_termux.sh"
echo ""

echo "===================================="
echo "Installation Complete!"
echo "===================================="
echo ""
echo "Quick Start:"
echo "  1. Launch the app:  ./run_termux.sh"
echo "  2. Open browser:    http://localhost:3000"
echo "  3. Login:           admin / changeme"
echo "  4. Change password immediately in Settings"
echo ""
echo "Tips:"
echo "  - Run 'termux-wake-lock' before starting to prevent Android killing the app"
echo "  - Use tmux to keep the server running when Termux loses focus"
echo ""
echo "To start now, run:  ./run_termux.sh"
echo ""
