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
    FLASK_DEV, FLASK_DEBUG, FLASK_HOST, FLASK_PORT, GUNICORN_WORKERS,
    GUNICORN_TIMEOUT.
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
        # gunicorn's own default (30s) is too short for scans that legitimately
        # take longer — e.g. Social Search checks up to 273 sites — see
        # start.sh's GUNICORN_TIMEOUT comment for the full explanation.
        timeout = os.getenv("GUNICORN_TIMEOUT", "120")
        print(f"Starting with gunicorn on http://{host}:{port} (production, {workers} worker(s))")
        os.execvp(sys.executable, [
            sys.executable, "-m", "gunicorn",
            "-w", workers,
            "-t", timeout,
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


def update_tac_db_cli():
    """Entry point for `osint-tracker-update-tac-db` — force an immediate
    refresh of the offline IMEI/TAC database, bypassing the scheduler's
    normal once-a-day rate limit. Useful right after install/upgrade, or on
    a server where APScheduler isn't installed and the weekly background
    refresh (app/utils/scheduler.py) never runs."""
    from app.services.tac_lookup import refresh_tac_database
    if refresh_tac_database(min_age_days=0):
        print("✅ TAC database refreshed.")
    else:
        print("⚠️  TAC database not refreshed — see logs. "
              "Existing offline data (bundled or previously downloaded) is unaffected.")
        sys.exit(1)


def check_scrapers_cli():
    """Entry point for `osint-tracker-check-scrapers` — run canary health
    checks against the app's web-scraping-based data sources (AHMIA dark
    web search, Sherlock's site list, Company Registry's Canada scraper)
    and print a report. Exits non-zero if any check fails, for use in a
    cron job or CI workflow, so a scraper break (a site's markup changed)
    gets caught before a user hits it. See app.utils.scraper_health."""
    from app import create_app
    from app.utils.scraper_health import check_and_notify
    create_app()  # ensures DB tables exist before any get_by_service() call
    results = check_and_notify()
    failed = False
    for r in results:
        status = "✅ OK" if r["ok"] else "❌ FAIL"
        print(f"{status}  {r['name']}: {r['detail']}")
        if not r["ok"]:
            failed = True
    if failed:
        sys.exit(1)


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
