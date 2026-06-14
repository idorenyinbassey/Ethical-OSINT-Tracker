#!/data/data/com.termux/files/usr/bin/bash
# Ethical OSINT Tracker - Termux Installation Script
# For Android devices using Termux terminal emulator

set -e  # Exit on error

echo "===================================="
echo "Ethical OSINT Tracker - Termux Setup"
echo "===================================="
echo ""

# Check if running in Termux
if [ ! -d "/data/data/com.termux" ]; then
    echo "Error: This script must be run in Termux terminal"
    echo "Install Termux from F-Droid: https://f-droid.org/en/packages/com.termux/"
    exit 1
fi

echo "Termux environment detected"
echo ""

# Update package lists
echo "Updating Termux packages..."
pkg update -y
pkg upgrade -y

# Install required system packages
echo "Installing system dependencies..."
pkg install -y \
    python \
    python-pip \
    clang \
    libffi \
    libjpeg-turbo \
    zlib \
    freetype \
    git \
    tmux

echo "System packages installed"
echo ""

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "Python $PYTHON_VERSION installed"

# Setup storage access (for image uploads)
echo "Setting up storage access..."
echo "  This allows the app to access device storage for image uploads."
echo "  Press 'Allow' when prompted."
termux-setup-storage
sleep 2
echo "Storage access configured"
echo ""

# Verify we are in the project directory
if [ ! -f "requirements.txt" ]; then
    echo "requirements.txt not found in current directory."
    echo "Please cd to the Ethical-OSINT-Tracker directory first, then run this script."
    exit 1
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python -m venv .venv
echo "Virtual environment created at .venv"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
echo "Virtual environment activated"
echo ""

# Install Python dependencies
echo "Installing Python packages (this may take a few minutes)..."
pip install --upgrade pip
pip install -r requirements.txt
echo "Python packages installed"
echo ""

# Initialise database and admin user
echo "Initialising database..."
python reset_admin.py
echo ""

# Create .env file for optional overrides
echo "Creating environment configuration..."
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Optional overrides — app works fine without these
# SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
# DB_URL=sqlite:///./dev.db
EOF
    echo ".env file created (all values optional)"
else
    echo ".env file already exists"
fi
echo ""

# Create a convenience launch script
echo "Creating launch script..."
cat > run_termux.sh << 'LAUNCH'
#!/data/data/com.termux/files/usr/bin/bash
# Launch Ethical OSINT Tracker on Termux

cd "$(dirname "$0")"
source .venv/bin/activate

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
echo "  1. Launch the app: ./run_termux.sh"
echo "  2. Open browser:   http://localhost:3000"
echo "  3. Login:          admin / changeme"
echo "  4. Change password immediately in Settings"
echo ""
echo "Tips:"
echo "  - Run 'termux-wake-lock' before starting to prevent Android from killing the app"
echo "  - Use tmux to keep the server running when Termux loses focus"
echo "  - See docs/TERMUX_INSTALL.md for more options"
echo ""
echo "To start now, run: ./run_termux.sh"
echo ""
