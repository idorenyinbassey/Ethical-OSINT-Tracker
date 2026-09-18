#!/bin/bash
# Flask startup script for Ethical OSINT Tracker.
#
# Prefers pipx (an isolated install with no manual venv/pip-install step);
# falls back automatically to a local .venv if pipx isn't available or the
# pipx install fails for any reason. Either way, secrets (SECRET_KEY,
# API_KEYS_FERNET_KEY) are generated once and persisted to secrets.env, and
# the admin password is prompted for with the terminal echo hidden instead
# of being typed inline — see scripts/secrets_bootstrap.sh for why.

set -e

cd "$(dirname "$0")"
# shellcheck source=scripts/secrets_bootstrap.sh
source "scripts/secrets_bootstrap.sh"

echo "Starting Ethical OSINT Tracker (Flask)..."

# ─────────────────────────────────────────────────────────────────────────
# Preferred path: pipx (no manual venv / pip install -r requirements.txt)
# ─────────────────────────────────────────────────────────────────────────
# Termux/Android never uses pipx: PyPI's `cryptography` package cannot
# dlopen against Termux's Python in any form pip can produce ("cannot
# locate symbol PyModule_Type" — confirmed on a real device, wheel and
# from-source build both fail identically). Only Termux's own `pkg
# install python-cryptography` works, and pipx's isolated venvs can't see
# it. The plain-venv fallback below is created with --system-site-packages
# on Termux specifically so it can.
IS_TERMUX=false
if [ -d "/data/data/com.termux" ]; then
    IS_TERMUX=true
fi

USE_PIPX=false
if $IS_TERMUX; then
    echo "Termux detected — using a .venv install (not pipx) so Termux's own"
    echo "python-cryptography package can be shared in via --system-site-packages."
elif command -v pipx >/dev/null 2>&1; then
    USE_PIPX=true
elif command -v pip3 >/dev/null 2>&1 || command -v pip >/dev/null 2>&1; then
    echo "pipx not found — installing it (one-time, isolated, no system packages touched)..."
    if (command -v pip3 >/dev/null 2>&1 && pip3 install --user -q pipx) \
        || (command -v pip >/dev/null 2>&1 && pip install --user -q pipx); then
        python3 -m pipx ensurepath >/dev/null 2>&1 || true
        if command -v pipx >/dev/null 2>&1; then
            USE_PIPX=true
        elif [ -x "$HOME/.local/bin/pipx" ]; then
            PATH="$HOME/.local/bin:$PATH"
            USE_PIPX=true
        fi
    fi
fi

PIPX_RAN=false
if $USE_PIPX; then
    echo "Installing/updating via pipx (isolated venv managed automatically)..."
    if pipx install --force -q .; then
        BIN_DIR="$(pipx environment --value PIPX_BIN_DIR 2>/dev/null || true)"
        [ -z "$BIN_DIR" ] && BIN_DIR="$HOME/.local/bin"
        if [ -x "$BIN_DIR/osint-tracker" ]; then
            RUN_CMD="$BIN_DIR/osint-tracker"
            RESET_CMD="$BIN_DIR/osint-tracker-reset-admin"
            INIT_CMD="$BIN_DIR/osint-tracker-init-db"
            FERNET_GEN_CMD="$BIN_DIR/osint-tracker-gen-fernet-key"
            PIPX_RAN=true
        else
            echo "  ⚠️  pipx install succeeded but the command wasn't found — falling back to venv."
        fi
    else
        echo "  ⚠️  pipx install failed — falling back to a local .venv instead."
    fi
fi

# ─────────────────────────────────────────────────────────────────────────
# Fallback path: local .venv (unchanged behavior for anyone without pipx)
# ─────────────────────────────────────────────────────────────────────────
if ! $PIPX_RAN; then
    VENV_DIR=".venv"
    PYTHON="$VENV_DIR/bin/python"
    PIP="$VENV_DIR/bin/pip"

    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment..."
        if $IS_TERMUX; then
            # --system-site-packages so this venv can see Termux's own
            # `pkg install python-cryptography` — see the IS_TERMUX note
            # above for why PyPI's cryptography can't be used instead.
            python3 -m venv --system-site-packages "$VENV_DIR"
        else
            python3 -m venv "$VENV_DIR"
        fi
    fi

    echo "Installing/updating dependencies in venv..."
    "$PIP" install -q --upgrade pip
    "$PIP" install -q -r requirements.txt

    RUN_CMD="$PYTHON run.py"
    RESET_CMD="$PYTHON reset_admin.py"
    INIT_CMD="$PYTHON -c \"from app import create_app; create_app()\""
    FERNET_GEN_CMD="\"$PYTHON\" -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
fi

# ─────────────────────────────────────────────────────────────────────────
# Secrets: generate/persist SECRET_KEY + API_KEYS_FERNET_KEY, load them
# ─────────────────────────────────────────────────────────────────────────
bootstrap_secrets "$FERNET_GEN_CMD"

# Default database
if [ -z "$DB_URL" ]; then
    export DB_URL="sqlite:///./dev.db"
fi
echo "Using database: $DB_URL"

# Default to a single gunicorn worker: the default SQLite database allows
# only one writer at a time, so extra workers race on the same file and
# intermittently fail requests with "database is locked". Bump this only
# if DB_URL points at a real multi-connection database (e.g. MySQL).
export GUNICORN_WORKERS="${GUNICORN_WORKERS:-1}"

# ─────────────────────────────────────────────────────────────────────────
# Admin account: reset explicitly, first-run init, or just ensure tables
# ─────────────────────────────────────────────────────────────────────────
if [ "${1}" = "--reset-admin" ]; then
    echo "Resetting admin account..."
    ensure_admin_password
    eval "$RESET_CMD"
elif [ ! -f "dev.db" ] && { [ -z "$DB_URL" ] || [ "$DB_URL" = "sqlite:///./dev.db" ]; }; then
    echo "First run — database requires admin account initialization"
    ensure_admin_password
    echo "Initialising database and creating admin account..."
    eval "$RESET_CMD"
else
    # Just ensure tables are created without resetting credentials.
    eval "$INIT_CMD"
fi

# install_termux.sh calls `./start.sh --install-only` so it can run the
# (Termux-identical) pipx/venv + secrets + admin setup above without then
# blocking forever on the server launch below.
if [ "${1}" = "--install-only" ]; then
    echo ""
    echo "✅ Install complete. Run ./start.sh (or ./run_termux.sh) to launch."
    exit 0
fi

echo ""

if $PIPX_RAN; then
    exec "$RUN_CMD"
else
    if [ "${FLASK_DEV:-0}" = "1" ]; then
        echo "Starting Flask development server on http://${FLASK_HOST:-localhost}:${FLASK_PORT:-3000}"
        echo "⚠️  Development mode enabled - debug and features may be exposed"
        echo ""
        exec "$PYTHON" run.py
    else
        echo "Starting Flask application with gunicorn on http://0.0.0.0:${FLASK_PORT:-3000} (production, ${GUNICORN_WORKERS} worker(s))"
        echo ""
        exec "$PYTHON" -m gunicorn -w "$GUNICORN_WORKERS" -b "0.0.0.0:${FLASK_PORT:-3000}" "app.wsgi:app"
    fi
fi
