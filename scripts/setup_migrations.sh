#!/usr/bin/env bash
set -euo pipefail

# Usage: bash scripts/setup_migrations.sh
# This script creates a local venv (if missing), installs requirements,
# and runs `alembic upgrade head` to create/update the local SQLite DB.

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Create venv if missing
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment .venv..."
  python3 -m venv .venv
  . .venv/bin/activate
  echo "Installing requirements..."
  pip install --upgrade pip
  pip install -r requirements.txt
else
  # Activate existing venv for the script
  if [ -z "${VIRTUAL_ENV-}" ]; then
    echo "Activating existing .venv"
    # shellcheck disable=SC1091
    . .venv/bin/activate
  fi
fi

# Ensure DB URL defaults to local SQLite if not provided
export DB_URL="${DB_URL:-sqlite:///./dev.db}"

echo "Running migrations: alembic upgrade head"
alembic upgrade head

echo "Migrations applied. Current revision:"
alembic current || true

echo "Done. If you need to reset DB, use: sqlite3 dev.db '.tables'"