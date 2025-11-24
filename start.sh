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

# Set default DB_URL if not provided (can be overridden externally)
if [ -z "$DB_URL" ]; then
    export DB_URL="sqlite:///./dev.db"
fi

echo "🗄  Using database URL: $DB_URL"

# Optional: Run migrations (Alembic)
if [ -d "alembic/versions" ] && [ "$(ls -A alembic/versions)" ]; then
        echo "🔄 Running database migrations (alembic upgrade head)..."
        alembic upgrade head || echo "⚠️ Alembic migration failed; continuing with SQLModel create_all fallback"
fi

# Initialize database
echo "💾 Initializing database (creates tables if not exists)..."
python -c "from app.db import init_db; init_db(); print('✅ Database initialized')"

# Start the application
echo ""
echo "✨ Starting Reflex application..."
echo "📍 Demo credentials: admin / changeme"
echo ""

if [ "$HEADLESS" = "1" ] || [ "$HEADLESS" = "true" ]; then
    echo "🌀 Headless mode enabled (backend-only). Set HEADLESS=0 to restore full UI."
    reflex run --env prod --backend-only
else
    reflex run --env dev
fi
