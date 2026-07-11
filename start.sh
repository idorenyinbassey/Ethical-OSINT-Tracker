#!/bin/bash
# Flask startup script for Ethical OSINT Tracker

set -e

VENV_DIR=".venv"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

echo "Starting Ethical OSINT Tracker (Flask)..."

# Create virtual environment if it does not exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created at $VENV_DIR"
fi

# Use the venv pip directly — no need to source activate just for installation
echo "Installing/updating dependencies in venv..."
"$PIP" install -q --upgrade pip
"$PIP" install -q -r requirements.txt

# Activate for the rest of the session (DB init + app launch inherit the env)
# shellcheck source=.venv/bin/activate
source "$VENV_DIR/bin/activate"

# Default database
if [ -z "$DB_URL" ]; then
    export DB_URL="sqlite:///./dev.db"
fi

echo "Using database: $DB_URL"

# Initialise database / admin on first run, or on --reset-admin request
if [ "${1}" = "--reset-admin" ]; then
    echo "Resetting admin account..."
    if [ -z "$ADMIN_PASSWORD" ]; then
        echo "❌ ERROR: ADMIN_PASSWORD environment variable not set"
        echo "Usage: ADMIN_PASSWORD=your_secure_password $0 --reset-admin"
        exit 1
    fi
    "$PYTHON" reset_admin.py
elif [ ! -f "dev.db" ] && { [ -z "$DB_URL" ] || [ "$DB_URL" = "sqlite:///./dev.db" ]; }; then
    # First run with new SQLite database requires admin password
    echo "First run — database requires admin account initialization"
    if [ -z "$ADMIN_PASSWORD" ]; then
        echo "❌ ERROR: ADMIN_PASSWORD environment variable not set"
        echo ""
        echo "Usage for first run:"
        echo "  ADMIN_PASSWORD=your_secure_password ./start.sh"
        echo ""
        echo "Requirements:"
        echo "  - ADMIN_PASSWORD must be at least 8 characters"
        echo "  - Store securely, never hardcode or commit to version control"
        exit 1
    fi
    echo "Initialising database and creating admin account..."
    "$PYTHON" reset_admin.py
    echo "✅ Admin account created successfully"
else
    # Just ensure tables are created without resetting credentials
    "$PYTHON" -c "from app import create_app; app = create_app()"
fi

echo ""

# Development mode requires explicit FLASK_DEV=1 environment variable
# Production (gunicorn) is the default for security
if [ "${FLASK_DEV:-0}" = "1" ]; then
    echo "Starting Flask development server on http://localhost:3000"
    echo "⚠️  Development mode enabled - debug and features may be exposed"
    echo ""
    "$PYTHON" run.py
else
    echo "Starting Flask application with gunicorn on http://0.0.0.0:3000 (production)"
    echo ""
    "$PYTHON" -m gunicorn -w 4 -b 0.0.0.0:3000 "run:app"
fi
