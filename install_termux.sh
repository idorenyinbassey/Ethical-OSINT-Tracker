#!/data/data/com.termux/files/usr/bin/bash
# Ethical OSINT Tracker — Termux Installation Script
# For Android devices using the Termux terminal emulator
#
# Handles Termux-specific system setup only (native packages, storage
# permission). The actual Python install (pipx-preferred, venv fallback),
# secret generation, and admin account setup are all delegated to
# start.sh, which is identical on Termux and desktop Linux — see
# scripts/secrets_bootstrap.sh for why that logic lives in one place.

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

# Build toolchain — rust/cargo is required to compile pydantic-core and
# argon2-cffi from source on Termux (no pre-built ARM wheels available).
# Compilation takes 5-15 minutes and needs ~2 GB free RAM; close other apps first.
pkg install -y \
    clang \
    binutils \
    make \
    patchelf \
    rust

# Python runtime + pipx (avoids a manual venv — see start.sh)
pkg install -y \
    python \
    python-pip
pkg install -y python-pipx 2>/dev/null || true   # not on every Termux mirror; start.sh falls back if missing

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
    tmux \
    psmisc  # provides fuser, used by run_termux.sh to free a stuck port

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

echo "Handing off to start.sh for the Python install, secrets, and admin setup..."
echo ""
chmod +x start.sh
./start.sh --install-only

# Convenience launch script — a thin wrapper around start.sh with a couple
# of Termux-specific niceties (wake lock reminder, freeing a stuck port).
echo "Creating launch script..."
cat > run_termux.sh << 'LAUNCH'
#!/data/data/com.termux/files/usr/bin/bash
# Launch Ethical OSINT Tracker on Termux.
cd "$(dirname "$0")"

# Kill any existing process on the target port (a previous run left hanging).
fuser -k "${FLASK_PORT:-3000}/tcp" 2>/dev/null || true

echo "Starting Ethical OSINT Tracker..."
echo "Open http://localhost:${FLASK_PORT:-3000} in your browser"
echo "Press Ctrl+C to stop"
echo ""

exec ./start.sh
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
echo "  3. Log in with the admin username/password you set during install"
echo ""
echo "Tips:"
echo "  - Run 'termux-wake-lock' before starting to prevent Android killing the app"
echo "  - Use tmux to keep the server running when Termux loses focus"
echo ""
echo "To start now, run:  ./run_termux.sh"
echo ""
