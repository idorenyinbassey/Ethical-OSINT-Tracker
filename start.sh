#!/bin/bash
# Production Startup Script

set -e  # Exit on error

echo "🚀 Starting Ethical OSINT Tracker..."
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -q -r requirements.txt

# Optional: Run migrations
if [ -d "alembic/versions" ] && [ "$(ls -A alembic/versions)" ]; then
    echo "🔄 Running database migrations..."
    alembic upgrade head
fi

# Initialize database
echo "💾 Initializing database (creates tables if not exists)..."
python -c "from app.db import init_db; init_db(); print('✅ Database initialized')"

# Start the application
echo ""
echo "✨ Starting Reflex application..."
echo "📍 Dashboard: http://localhost:3000"
echo "🔑 Demo credentials: admin / changeme"
echo ""

reflex run
