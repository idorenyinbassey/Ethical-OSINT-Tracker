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

# Initialize DB and create demo admin
python reset_admin.py

echo ""
echo "Starting Flask application on http://0.0.0.0:3000"
echo "Demo credentials: admin / changeme"
echo ""

if [ "${FLASK_ENV:-development}" = "production" ]; then
    python -m gunicorn -w 4 -b 0.0.0.0:3000 "run:app"
else
    python run.py
fi
