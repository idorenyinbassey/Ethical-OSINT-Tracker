# Installation Guide

Complete installation instructions for Ethical OSINT Tracker.

## System Requirements

- **OS**: Linux, macOS, or Windows (WSL recommended)
- **Python**: 3.11 or higher
- **RAM**: 512 MB minimum
- **Disk**: 300 MB for application, dependencies, and database
- **Browser**: Any modern browser (Chrome, Firefox, Safari, Edge)

---

## Installation Steps

### 1. Install Python 3.11+

**Linux (Ubuntu/Debian)**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

**macOS**
```bash
brew install python@3.11
```

**Windows** — download from [python.org](https://www.python.org/downloads/) or use WSL.

### 2. Clone the Repository

```bash
git clone https://github.com/idorenyinbassey/Ethical-OSINT-Tracker.git
cd Ethical-OSINT-Tracker
```

### 3. Create a Virtual Environment

```bash
python3.11 -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Key dependencies:

| Package | Version | Purpose |
|---|---|---|
| flask | ≥3.0 | Web framework |
| flask-login | ≥0.6 | Session authentication |
| flask-wtf | ≥1.2 | CSRF protection |
| sqlmodel | ≥0.0.21 | ORM (SQLite / MySQL) |
| argon2-cffi | 23.1.0 | Argon2id password hashing |
| httpx[socks] | ≥0.23 | HTTP client (Tor/SOCKS5 support) |
| APScheduler | ≥3.10.0 | Watchlist auto-rescan background job |
| Pillow | ≥10.0 | Image EXIF metadata |
| fpdf2 | ≥2.7.0 | PDF report generation |
| python-docx | ≥1.1.0 | DOCX report generation |
| openpyxl | ≥3.1.0 | XLSX report generation |

### 5. Initialise the Database

There is **no default password**. Running `reset_admin.py` (or `start.sh`,
see step 7) without `ADMIN_PASSWORD` set prompts for it interactively —
hidden input, confirmed twice, never written to shell history:

```bash
python reset_admin.py
```

For non-interactive/scripted setups, supply it via the environment instead
(this also skips the prompt):
```bash
ADMIN_PASSWORD='choose-a-strong-password' python reset_admin.py
```

Creates (or resets, if it already exists) the admin account:
- **Username**: `admin` (fixed)
- **Password**: whatever you entered / supplied

> To change the password later, re-run the same command — it resets the existing
> `admin` account in place.

For MySQL (production):

```sql
CREATE DATABASE osint_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'osint_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON osint_tracker.* TO 'osint_user'@'localhost';
FLUSH PRIVILEGES;
```

Then set the connection string before running:
```bash
export DB_URL=mysql+pymysql://osint_user:secure_password@localhost/osint_tracker
ADMIN_PASSWORD='choose-a-strong-password' python reset_admin.py
```

### 6. Configure Environment

`start.sh` (step 7) generates `SECRET_KEY` and `API_KEYS_FERNET_KEY` once
and persists them to `secrets.env` automatically — a restart never
invalidates sessions or breaks previously-saved API keys, and there's
nothing to do here if you're using it.

Running the app another way (`python run.py` directly, a process manager,
Docker)? `.env` **is** auto-loaded (via `python-dotenv`), or export
variables yourself / `source` a file:

```bash
cat > secrets.env <<'EOF'
SECRET_KEY=<paste a fixed random value, e.g. python -c 'import secrets;print(secrets.token_hex(32))'>
API_KEYS_FERNET_KEY=<paste: python -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())'>
# DB_URL=sqlite:///./dev.db   # optional; this is the default
EOF

set -a && source secrets.env && set +a
```

Keep both values stable once generated — a changing `SECRET_KEY` logs
everyone out, and a changing `API_KEYS_FERNET_KEY` makes stored API keys
undecryptable.

See the README's Environment Variables table for the full list
(`REGISTRATION_ENABLED`, `RETENTION_DAYS`, `CACHE_MAX_SIZE`, `FLASK_DEV`,
`FLASK_DEBUG`, …).

### 7. Run the Application

```bash
chmod +x start.sh
./start.sh
```

No manual virtualenv needed — `start.sh` prefers
[pipx](https://pipx.pypa.io) (installing it automatically if missing) and
falls back to a local `.venv` if pipx isn't available. On a brand-new
database it also prompts for the admin password (hidden input) — see
step 5. For non-interactive/scripted setups:
```bash
ADMIN_PASSWORD='choose-a-strong-password' ./start.sh
```

**Development server** — set `FLASK_DEV=1` (debug stays off unless `FLASK_DEBUG=1`):
```bash
source secrets.env
FLASK_DEV=1 python run.py
```

Open http://localhost:3000 and log in as `admin`.

**Production (gunicorn), run directly instead of via start.sh**
```bash
gunicorn -w 1 -b 0.0.0.0:3000 "app.wsgi:app"
```
Keep `-w 1` unless `DB_URL` points at a real multi-connection database
(e.g. MySQL) — the default SQLite database allows only one writer, so
extra workers intermittently fail requests with "database is locked".

The app is available at [http://localhost:3000](http://localhost:3000).

---

## Post-Installation

### Grant Admin to Existing Users

If you already have user accounts and need to grant admin privileges:

```python
# run as: python -c "exec(open('grant_admin.py').read())"
from app import create_app
from app.repositories.user_repository import set_admin

app = create_app()
with app.app_context():
    set_admin(1, True)   # replace 1 with the user's database ID
```

Or use the Admin Panel at `/admin/users` once logged in as an admin.

### Configure API Services

1. Go to **Settings** in the sidebar
2. Find the service you want to enable
3. Enter your API key and confirm the base URL
4. Toggle **Enabled** and click **Save**

No restart required.

### Database Schema Updates

New columns are added automatically by `init_db()` on startup using idempotent `ALTER TABLE` statements — no manual migration needed for existing databases when upgrading from a previous version.

For structural schema changes (new tables, column type changes), use Alembic:
```bash
alembic upgrade head
```

---

## Troubleshooting

**Port 3000 in use**
```bash
lsof -ti:3000 | xargs kill -9
```

**"Invalid username or password" / forgot the admin password**
The username is always `admin`. Reset the password (works whether or not the
database exists):
```bash
./start.sh --reset-admin        # prompts for the new password, hidden input
# non-interactive: ADMIN_PASSWORD='new-strong-password' ./start.sh --reset-admin
```
Note: `./start.sh` without `--reset-admin` only creates the admin when `dev.db`
does not already exist.

**Getting logged out after every restart**
Shouldn't happen if you're using `start.sh` — it generates and persists a
stable `SECRET_KEY` for you. If you're managing it yourself, make sure
it's a fixed value, not regenerated per run.

**Database reset (wipes all data)**
```bash
rm dev.db
./start.sh   # prompts for a new admin password since dev.db is gone
```

**Scheduler fails to start: `No time zone found with key ...`**
Common on Termux/minimal systems missing the IANA tz database:
```bash
pip install tzdata
```
Non-fatal, but the watchlist rescan and retention purge won't run until fixed.

**APScheduler not installed (watchlist rescan won't run)**
```bash
pip install APScheduler>=3.10.0
```

**Python cache issues**
```bash
find . -type d -name __pycache__ -exec rm -r {} +
pip install -r requirements.txt --force-reinstall --no-cache-dir
```

**IMEI lookup fails**
Verify the base URL in Settings is `https://dash.imei.info/api`. The API requires a funded account balance on dash.imei.info.

---

## Next Steps

- [User Guide](./USER_GUIDE.md) — feature walkthrough
- [API Integration](./API_INTEGRATION.md) — configure external services
- [Architecture](./ARCHITECTURE.md) — technical design
- [Development Guide](./DEVELOPMENT.md) — contributing
- [Deployment Guide](./DEPLOYMENT.md) — production deployment
- [Termux / Android](./TERMUX.md) — mobile installation
