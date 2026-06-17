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
    "$PYTHON" reset_admin.py
elif [ ! -f "dev.db" ] && { [ -z "$DB_URL" ] || [ "$DB_URL" = "sqlite:///./dev.db" ]; }; then
    echo "First run — initialising database and creating admin account..."
    "$PYTHON" reset_admin.py
    echo "Admin account created. Change the password on first login."
else
    # Just ensure tables are created without resetting credentials
    "$PYTHON" -c "from app import create_app; app = create_app()"
fi

echo ""
echo "Starting Flask application on http://0.0.0.0:3000"
echo ""

if [ "${FLASK_ENV:-development}" = "production" ]; then
    "$PYTHON" -m gunicorn -w 4 -b 0.0.0.0:3000 "run:app"
else
    "$PYTHON" run.py
fi
