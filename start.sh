#!/bin/bash
# Flask startup script

set -e

echo "Starting Ethical OSINT Tracker (Flask)..."

# Create virtual environment if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

source .venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt

# Default DB
if [ -z "$DB_URL" ]; then
    export DB_URL="sqlite:///./dev.db"
fi

echo "Using database: $DB_URL"

# Only initialise the database on first run (when dev.db does not exist yet)
# Pass --reset flag explicitly to recreate the admin account
if [ "${1}" = "--reset-admin" ]; then
    echo "Resetting admin account..."
    python reset_admin.py
elif [ ! -f "dev.db" ] && [ -z "$DB_URL" -o "$DB_URL" = "sqlite:///./dev.db" ]; then
    echo "First run — initialising database and creating admin account..."
    python reset_admin.py
    echo "Admin account created. Change the password on first login."
else
    # Just initialise tables without resetting credentials
    python -c "from app import create_app; app = create_app()"
fi

echo ""
echo "Starting Flask application on http://0.0.0.0:3000"
echo ""

if [ "${FLASK_ENV:-development}" = "production" ]; then
    python -m gunicorn -w 4 -b 0.0.0.0:3000 "run:app"
else
    python run.py
fi
