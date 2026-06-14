# Installation Guide

Complete installation instructions for Ethical OSINT Tracker.

## System Requirements

- **OS**: Linux, macOS, or Windows (WSL recommended)
- **Python**: 3.11 or higher
- **RAM**: 512 MB minimum
- **Disk**: 200 MB for application and dependencies
- **Browser**: Any modern browser (Chrome, Firefox, Safari, Edge)

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

Core dependencies:

| Package | Version | Purpose |
|---|---|---|
| flask | ≥3.0 | Web framework |
| flask-login | ≥0.6 | Session authentication |
| sqlmodel | ≥0.0.21 | ORM (SQLite / MySQL) |
| argon2-cffi | 23.1.0 | Password hashing |
| httpx | ≥0.23 | HTTP client for API calls |
| Pillow | ≥10.0 | Image EXIF extraction |
| PyMySQL | 1.1.1 | MySQL driver (optional) |

### 5. Initialise the Database

```bash
python reset_admin.py
```

Creates an admin account:
- **Username**: `admin`
- **Password**: `changeme`

> Change this password before any public deployment.

For MySQL (production):

```sql
CREATE DATABASE osint_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'osint_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON osint_tracker.* TO 'osint_user'@'localhost';
FLUSH PRIVILEGES;
```

Set the connection string before running `reset_admin.py`:

```bash
export DB_URL=mysql+pymysql://osint_user:secure_password@localhost/osint_tracker
python reset_admin.py
```

### 6. Configure Environment (Optional)

Create a `.env` file in the project root (load it via `export $(cat .env | xargs)` or use `python-dotenv`):

```env
# Database — defaults to SQLite if not set
DB_URL=sqlite:///./dev.db

# Flask session signing key — MUST be set to a long random string in production
SECRET_KEY=change-me-to-something-long-and-random
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
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:3000 "run:app"
```

The app is available at [http://localhost:3000](http://localhost:3000).

### 8. Verify Installation

1. Open http://localhost:3000
2. Log in with `admin` / `changeme`
3. Try a domain lookup: enter `example.com` on the Domain WHOIS page

## Post-Installation

### Configure API Services

1. Go to **Settings** in the sidebar
2. Find the service you want to enable
3. Enter your API key and base URL
4. Toggle **Enabled** and click **Save**

No restart is required — keys are read from the database at request time.

### Database Migrations

For schema changes, use Alembic:

```bash
alembic upgrade head          # Apply all pending migrations
alembic revision --autogenerate -m "describe the change"  # Create new migration
```

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

**Python cache issues**
```bash
find . -type d -name __pycache__ -exec rm -r {} +
pip install -r requirements.txt --force-reinstall --no-cache-dir
```

## Next Steps

- [User Guide](./USER_GUIDE.md) — feature walkthrough
- [API Integration](./API_INTEGRATION.md) — configure external services
- [Architecture](./ARCHITECTURE.md) — technical design
- [Development Guide](./DEVELOPMENT.md) — contributing
- [Deployment Guide](./DEPLOYMENT.md) — production deployment
