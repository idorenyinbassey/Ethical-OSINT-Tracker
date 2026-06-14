# Architecture Overview

Technical architecture of Ethical OSINT Tracker — a Flask web application for ethical OSINT investigations.

## Core Technologies

| Layer | Technology | Version |
|---|---|---|
| Web framework | [Flask](https://flask.palletsprojects.com/) | ≥ 3.0 |
| Authentication | [Flask-Login](https://flask-login.readthedocs.io/) | ≥ 0.6 |
| ORM | [SQLModel](https://sqlmodel.tiangolo.com/) (SQLAlchemy) | ≥ 0.0.21 |
| Database | SQLite (dev) / MySQL (prod) | — |
| HTTP client | [httpx[socks]](https://www.python-httpx.org/) | ≥ 0.23 |
| Password hashing | [argon2-cffi](https://argon2-cffi.readthedocs.io/) | 23.1.0 |
| Image processing | [Pillow](https://pillow.readthedocs.io/) | ≥ 10.0 |
| Audio metadata | [mutagen](https://mutagen.readthedocs.io/) | — |
| PDF metadata | [pypdf](https://pypdf.readthedocs.io/) | — |
| Video metadata | [hachoir](https://hachoir.readthedocs.io/) | — |
| DOCX metadata | [python-docx](https://python-docx.readthedocs.io/) | — |
| XLSX metadata | [openpyxl](https://openpyxl.readthedocs.io/) | — |
| DNS enumeration | [dnspython](https://www.dnspython.org/) (optional) | — |
| Frontend | Jinja2 templates + Tailwind CSS (CDN) | — |

## Project Structure

```
Ethical-OSINT-Tracker/
├── app/
│   ├── __init__.py          # Flask app factory — create_app()
│   ├── config.py            # Config class (SECRET_KEY, DB_URL, UPLOAD_FOLDER)
│   ├── db.py                # SQLModel engine and init_db()
│   ├── models/              # SQLModel table classes
│   │   ├── user.py          # User (UserMixin)
│   │   ├── investigation.py # Investigation result record
│   │   ├── case.py          # Case (status, priority, owner)
│   │   ├── api_config.py    # External service credentials
│   │   ├── intelligence_report.py
│   │   └── team.py
│   ├── repositories/        # Data-access layer (session_scope)
│   │   ├── base.py          # session_scope context manager
│   │   ├── user_repository.py
│   │   ├── investigation_repository.py
│   │   ├── case_repository.py
│   │   ├── api_config_repository.py
│   │   ├── intelligence_report_repository.py
│   │   └── team_repository.py
│   ├── routes/              # Flask blueprints
│   │   ├── auth.py          # /login  /register  /logout
│   │   ├── dashboard.py     # /
│   │   ├── investigation.py # /investigate/* (11 tools)
│   │   ├── cases.py         # /cases  (CRUD + detail + edit)
│   │   └── settings.py      # /settings
│   ├── services/            # External API clients (all sync)
│   │   ├── cache.py         # TTL in-memory cache decorator
│   │   ├── ip_client.py     # ip-api.com (primary) + IPInfo.io (optional)
│   │   ├── rdap_client.py   # Public RDAP (no key needed)
│   │   ├── subdomain_client.py  # crt.sh CT logs + DNS wordlist bruteforce
│   │   ├── hibp_client.py   # Have I Been Pwned
│   │   ├── hunter_client.py # Hunter.io
│   │   ├── email_header_client.py  # Raw header parsing (SPF/DKIM/DMARC)
│   │   ├── numverify_client.py
│   │   ├── virustotal_client.py
│   │   ├── shodan_client.py
│   │   ├── social_client.py # 36-platform Sherlock-style, ThreadPoolExecutor(12)
│   │   ├── mac_client.py    # macvendors.com OUI lookup
│   │   ├── file_client.py   # Pillow/mutagen/hachoir/pypdf/python-docx/openpyxl
│   │   ├── crypto_client.py # blockchain.info (BTC) + blockcypher.com (ETH)
│   │   └── imei_client.py
│   ├── templates/           # Jinja2 templates
│   │   ├── base.html        # Shared sidebar layout
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── investigation/
│   │   ├── cases/
│   │   └── settings/
│   ├── uploads/             # Uploaded files (runtime, gitignored)
│   └── utils/
│       ├── crypto.py        # API key encrypt/decrypt (passthrough dev)
│       ├── rate_limiter.py  # In-memory rate limiter + RateLimiter class
│       ├── key_manager.py   # Stub for external secrets managers
│       └── proxy_client.py  # httpx client factory — injects TorProxy if enabled
├── alembic/                 # Alembic migration environment
├── tests/
├── run.py                   # Entry point: python run.py
├── reset_admin.py           # Creates / resets the admin user
└── start.sh                 # One-command startup script
```

## Request Lifecycle

```
Browser
  │
  ▼
Flask router  ──────────────────────────────────────────────────
  │                                                             │
  ▼                                                             │
Blueprint route function (app/routes/)                         │
  │                                                             │
  ├── Reads form / query params                                 │
  ├── Calls repositories for DB reads                          │
  ├── Calls service clients for external API calls             │
  └── Calls repositories to persist results                    │
  │                                                             │
  ▼                                                             │
Jinja2 template render ──────────────────────────────────────► Response
```

## Authentication

Flask-Login manages sessions.

1. `POST /login` — validates credentials with Argon2, calls `login_user(user)`
2. `@login_required` — decorator on all protected routes
3. `user_loader` — loads `User` from DB by session cookie on every request
4. `POST /logout` — calls `logout_user()`

`User` inherits from both `UserMixin` and `SQLModel` so Flask-Login's helpers (`current_user`, `is_authenticated`) work out of the box.

## Data Access Layer

All DB operations go through the repository layer using a `session_scope` context manager:

```python
@contextmanager
def session_scope(expire_on_commit=True):
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

Repositories return plain detached model instances (or explicit copies) so callers never encounter `DetachedInstanceError` after the session closes.

## Service Layer

Each OSINT service is a standalone module in `app/services/`. All clients are **synchronous** — they use `httpx.Client` (not `httpx.AsyncClient`).

Common patterns:

- **TTL cache**: `@cached(ttl=3600)` decorator wraps each function; results are stored in a process-level dict
- **Graceful fallback**: if the API key is missing, the service is disabled, or the call fails, the client returns `None` (or mock data for VirusTotal/Shodan)
- **Config from DB**: `get_by_service("ServiceName")` fetches the stored `APIConfig` at call time — no restart needed after updating keys

`social_client.py` checks 36 platforms in parallel using `concurrent.futures.ThreadPoolExecutor` (12 workers). Each check analyses the HTTP response status code, page content, and redirect URL to determine whether a profile exists — no API key required.

`subdomain_client.py` queries the crt.sh Certificate Transparency log API and then resolves discovered names (plus a 75-entry common-subdomain wordlist) via dnspython or the built-in `socket` module.

`file_client.py` dispatches to different metadata backends based on file extension: Pillow for images (EXIF + GPS), mutagen for audio (ID3/Vorbis), hachoir for video, pypdf for PDF, python-docx for DOCX, and openpyxl for XLSX.

All service clients obtain their `httpx.Client` instance through `utils/proxy_client.py`, which transparently injects the configured TorProxy SOCKS5 or HTTP proxy when the TorProxy setting is enabled in the database.

## Database

`init_db()` calls `SQLModel.metadata.create_all(engine)` on startup. This is idempotent — it only creates missing tables.

For schema migrations use Alembic (`alembic/`). In development, `init_db()` alone is sufficient.

| Table | Purpose |
|---|---|
| `user` | Accounts with Argon2 password hashes |
| `investigation` | Every tool run: kind, query, result JSON, links to user/case |
| `case` | Investigation containers with status and priority |
| `apiconfig` | External service credentials stored per service name |
| `intelligencereport` | Generated summary reports |
| `team` / `teammember` | Multi-user team structures |

## Frontend

Templates use Jinja2 and Tailwind CSS loaded via CDN. No build step required.

The `base.html` layout provides:
- Dark sidebar with navigation links for all tools
- Flash message rendering (success / error)
- Logged-in user display and logout link
- Active-link highlighting via `request.endpoint`

Each tool page follows the same two-column pattern: form on the left, results on the right.

## Security Notes

- Passwords hashed with **Argon2id** (argon2-cffi default parameters)
- Sessions signed with `SECRET_KEY` — set a strong random value in production
- API keys stored in plaintext by default — implement `encrypt_api_key` / `decrypt_api_key` in `app/utils/crypto.py` for production
- No CSRF tokens currently — add `flask-wtf` for production deployments
- Uploaded images stored in `app/uploads/` — restrict this directory in web server config
