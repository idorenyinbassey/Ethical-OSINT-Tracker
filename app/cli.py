"""Console-script entry points.

These back the ``osint-tracker`` / ``osint-tracker-reset-admin`` commands
installed by ``pipx install .`` (or ``pip install .``), so the app can be
run without manually creating a virtualenv or running
``pip install -r requirements.txt``. They mirror start.sh's own launch
logic so behavior is identical between the two install methods.
"""
import os
import sys


def run_server():
    """Entry point for the `osint-tracker` console script.

    Honors the same environment variables as start.sh / run.py:
    FLASK_DEV, FLASK_DEBUG, FLASK_HOST, FLASK_PORT, GUNICORN_WORKERS.
    """
    dev_mode = os.getenv("FLASK_DEV", "0") == "1"
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = os.getenv("FLASK_PORT", "3000")

    if dev_mode:
        from app import create_app
        debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
        app = create_app()
        print(f"Starting Flask development server on http://{host}:{port}")
        if debug_mode:
            print("⚠️  Development mode enabled - debug and features may be exposed")
        app.run(debug=debug_mode, host=host, port=int(port))
    else:
        # Production: exec gunicorn so signal handling / worker management
        # behave exactly as they do under start.sh. Defaults to a single
        # worker — safe for the default SQLite database (see start.sh for
        # why a shared SQLite file cannot tolerate multiple writer workers).
        workers = os.getenv("GUNICORN_WORKERS", "1")
        print(f"Starting with gunicorn on http://{host}:{port} (production, {workers} worker(s))")
        os.execvp(sys.executable, [
            sys.executable, "-m", "gunicorn",
            "-w", workers,
            "-b", f"{host if host != '127.0.0.1' else '0.0.0.0'}:{port}",
            "app.wsgi:app",
        ])


def gen_fernet_key_cli():
    """Entry point for `osint-tracker-gen-fernet-key` — prints a fresh Fernet
    key to stdout. Lets start.sh generate API_KEYS_FERNET_KEY through
    whichever venv actually has 'cryptography' installed (the pipx-managed
    one, or .venv) instead of guessing at that venv's path itself."""
    from cryptography.fernet import Fernet
    print(Fernet.generate_key().decode())


def init_db_cli():
    """Entry point for `osint-tracker-init-db` — create tables without
    touching credentials. Used by start.sh's pipx path on every non-reset
    run, so it never has to guess pipx's internal venv layout."""
    from app import create_app
    create_app()


def reset_admin_cli():
    """Entry point for `osint-tracker-reset-admin` — same behavior as reset_admin.py."""
    from app.utils.admin_bootstrap import reset_admin
    password = os.getenv("ADMIN_PASSWORD")
    if not password:
        print("❌ ERROR: ADMIN_PASSWORD environment variable not set")
        print("")
        print("Usage:")
        print("  ADMIN_PASSWORD=your_secure_password osint-tracker-reset-admin")
        sys.exit(1)
    try:
        status = reset_admin(password)
    except ValueError as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)
    print(f"✅ Admin account {status}")
    print("   Username: admin")
