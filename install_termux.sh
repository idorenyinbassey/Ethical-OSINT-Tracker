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
    echo "❌ Error: This script must be run in Termux terminal"
    echo "Install Termux from F-Droid: https://f-droid.org/en/packages/com.termux/"
    exit 1
fi

echo "✓ Termux environment detected"
echo ""

# Update package lists
echo "📦 Updating Termux packages..."
pkg update -y
pkg upgrade -y

# Install required system packages
echo "📦 Installing system dependencies..."
pkg install -y \
    python \
    python-pip \
    rust \
    binutils \
    clang \
    libffi \
    libjpeg-turbo \
    zlib \
    freetype \
    git \
    which

echo "✓ System packages installed"
echo ""

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python $PYTHON_VERSION installed"

# Install uv package manager (fast, Rust-based)
echo "📦 Installing uv package manager..."
if ! command -v uv &> /dev/null; then
    pip install --upgrade pip
    pip install uv
    echo "✓ uv installed successfully"
else
    echo "✓ uv already installed"
fi

# Verify uv installation
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv installation failed"
    echo "Falling back to pip for installation"
    USE_UV=false
else
    echo "✓ uv is ready ($(uv --version))"
    USE_UV=true
fi

echo ""

# Setup storage access (optional but recommended)
echo "📁 Setting up storage access..."
echo "   This allows the app to access your device's storage for file uploads."
echo "   Press 'Allow' when prompted."
termux-setup-storage
sleep 2
echo "✓ Storage access configured"
echo ""

# Create project directory
echo "📂 Creating project directory..."
if [ -d "$HOME/ethical-osint-tracker" ]; then
    echo "⚠️  Directory already exists. Backing up to ethical-osint-tracker.bak"
    rm -rf "$HOME/ethical-osint-tracker.bak"
    mv "$HOME/ethical-osint-tracker" "$HOME/ethical-osint-tracker.bak"
fi

cd "$HOME"
echo "✓ Changed to $HOME"
echo ""

# Clone repository (if this script is standalone) or assume already in repo
if [ ! -f "requirements.txt" ]; then
    echo "⚠️  requirements.txt not found in current directory"
    echo "Please cd to the Ethical-OSINT-Tracker directory and run this script"
    exit 1
fi

# Create virtual environment using uv
echo "🐍 Creating Python virtual environment..."
if [ "$USE_UV" = true ]; then
    uv venv .venv --python python
else
    python -m venv .venv
fi
echo "✓ Virtual environment created at .venv"
echo ""

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install Python dependencies
echo "📦 Installing Python packages (this may take 5-10 minutes)..."
if [ "$USE_UV" = true ]; then
    echo "Using uv for fast installation..."
    uv pip install -r requirements.txt
else
    echo "Using pip for installation..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi
echo "✓ Python packages installed"
echo ""

# Create database directory
echo "💾 Setting up database..."
mkdir -p data
echo "✓ Database directory created"
echo ""

# Run database migrations
echo "🔄 Running database migrations..."
if command -v alembic &> /dev/null; then
    alembic upgrade head
    echo "✓ Database migrations complete"
else
    echo "⚠️  Alembic not found, skipping migrations"
    echo "   Run 'alembic upgrade head' manually after activation"
fi
echo ""

# Create launch script optimized for Termux (ports 8000/3000 instead of 8001/3001)
echo "📝 Creating launch script..."
cat > run_termux.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
# Launch script for Ethical OSINT Tracker on Termux

# Change to project directory
cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Export environment variables for Termux
export PORT=8000
export FRONTEND_PORT=3000
export REFLEX_DEV_MODE=false  # Disable hot-reload for better performance

# Kill any existing processes on these ports
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 3000/tcp 2>/dev/null || true

# Start the application
echo "🚀 Starting Ethical OSINT Tracker..."
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

reflex run --backend-port 8000 --frontend-port 3000 --loglevel info
EOF

chmod +x run_termux.sh
echo "✓ Launch script created: ./run_termux.sh"
echo ""

# Update rxconfig.py for Termux compatibility
echo "⚙️  Configuring app for Termux..."
if [ -f "rxconfig.py" ]; then
    # Check if ports are already configured
    if ! grep -q "backend_port" rxconfig.py; then
        # Backup original
        cp rxconfig.py rxconfig.py.bak
        
        # Add Termux-specific configuration
        cat >> rxconfig.py << 'EOF'

# Termux-specific configuration
import os
if os.environ.get("PORT"):
    config.backend_port = int(os.environ.get("PORT", 8000))
if os.environ.get("FRONTEND_PORT"):
    config.frontend_port = int(os.environ.get("FRONTEND_PORT", 3000))
EOF
        echo "✓ rxconfig.py updated for Termux"
    else
        echo "✓ rxconfig.py already configured"
    fi
fi
echo ""

# Create .env file for database
echo "📝 Creating environment configuration..."
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Database configuration
DATABASE_URL=sqlite:///./data/app.db

# Security
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Termux-specific
TERMUX_MODE=true
EOF
    echo "✓ .env file created"
else
    echo "✓ .env file already exists"
fi
echo ""

# Initialize database with admin user
echo "👤 Creating admin user..."
python << EOF
import sys
sys.path.insert(0, '.')

try:
    from app.db import init_db
    from app.repositories.user_repository import create_user, get_by_username
    
    # Initialize database
    init_db()
    
    # Check if admin exists
    admin = get_by_username("admin")
    if not admin:
        create_user("admin", "changeme")
        print("✓ Admin user created (username: admin, password: changeme)")
        print("⚠️  IMPORTANT: Change the password after first login!")
    else:
        print("✓ Admin user already exists")
except Exception as e:
    print(f"⚠️  Database initialization: {e}")
    print("   You may need to run migrations manually")
EOF
echo ""

echo "===================================="
echo "✅ Installation Complete!"
echo "===================================="
echo ""
echo "📖 Quick Start:"
echo "   1. Launch the app: ./run_termux.sh"
echo "   2. Open browser: http://localhost:3000"
echo "   3. Login: admin / changeme"
echo ""
echo "📱 Mobile Access:"
echo "   - Use Termux:API for better integration"
echo "   - Keep screen on during operation"
echo "   - Consider using Wake Lock app"
echo ""
echo "🔧 Troubleshooting:"
echo "   - Pillow issues: pkg install libjpeg-turbo"
echo "   - Permission errors: termux-setup-storage"
echo "   - Port conflicts: check run_termux.sh"
echo ""
echo "📚 Documentation: docs/TERMUX_INSTALL.md"
echo ""
echo "🚀 To start now, run: ./run_termux.sh"
echo ""
