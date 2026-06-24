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

```bash
python reset_admin.py
```

Creates the default admin account:
- **Username**: `admin`
- **Password**: `changeme`

> Change this password immediately via **Settings → Change Password** or the **Admin Panel** after first login.

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
python reset_admin.py
```

### 6. Configure Environment (Optional)

Create a `.env` file in the project root:

```env
# Database — defaults to SQLite if not set
DB_URL=sqlite:///./dev.db

# Flask session signing key — set a long random string in production
SECRET_KEY=change-me-to-something-long-and-random
```

Load it before starting:
```bash
export $(cat .env | xargs)
```

### 7. Run the Application

**Development**
```bash
python run.py
```

**Using the convenience script**
```bash
chmod +x start.sh
./start.sh
```

**Production (gunicorn)**
```bash
gunicorn -w 4 -b 0.0.0.0:3000 "run:app"
```

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

**Database reset**
```bash
rm dev.db
python reset_admin.py
```

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
