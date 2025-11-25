# Installation Guide

Complete installation instructions for Ethical OSINT Tracker.

## System Requirements

### Minimum Requirements
- **OS**: Linux, macOS, or Windows (WSL recommended)
- **Python**: 3.11 or higher
- **RAM**: 2GB minimum, 4GB recommended
- **Disk**: 500MB for application + dependencies
- **Browser**: Modern browser (Chrome, Firefox, Safari, Edge)

### Recommended Development Environment
- Python 3.11+
- pip 23.0+
- Git 2.30+
- Virtual environment tool (venv or virtualenv)

## Installation Steps

### 1. Install Python

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

#### macOS
```bash
# Using Homebrew
brew install python@3.11
```

#### Windows
Download from [python.org](https://www.python.org/downloads/) or use WSL.

### 2. Clone Repository

```bash
git clone https://github.com/idorenyinbassey/Ethical-OSINT-Tracker.git
cd Ethical-OSINT-Tracker
```

### 3. Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

### 4. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

**Dependencies include:**
- reflex==0.8.9 (Web framework)
- sqlmodel==0.0.27 (ORM)
- argon2-cffi==23.1.0 (Password hashing)
- httpx==0.28.1 (HTTP client)
- pydantic==2.10.3 (Data validation)

### 5. Database Setup

#### Option A: SQLite (Default - Recommended for Development)

```bash
# Initialize database with demo user
python reset_admin.py
```

Creates admin user:
- Username: `admin`
- Password: `changeme`

#### Option B: MySQL (Production)

1. Install MySQL:
```bash
# Ubuntu/Debian
sudo apt install mysql-server

# macOS
brew install mysql
```

2. Create database:
```sql
CREATE DATABASE osint_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'osint_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON osint_tracker.* TO 'osint_user'@'localhost';
FLUSH PRIVILEGES;
```

3. Configure connection in `.env`:
```env
DB_URL=mysql+pymysql://osint_user:secure_password@localhost/osint_tracker
```

4. Install MySQL driver:
```bash
pip install pymysql cryptography
```

5. Initialize:
```bash
python reset_admin.py
```

### 6. Configuration

Create `.env` file in project root:

```env
# Database (optional)
DB_URL=sqlite:///./reflex.db

# API Keys (optional - app works without them)
WHOISXML_API_KEY=
HIBP_API_KEY=
IPINFO_TOKEN=
HUNTER_API_KEY=
NUMVERIFY_KEY=
SHODAN_API_KEY=
VIRUSTOTAL_API_KEY=

# Security (production)
SECRET_KEY=generate_a_random_secret_key_here
ENCRYPT_API_KEYS=true
```

### 7. Run Application

#### Development Mode
```bash
reflex run
```

#### Using Launch Script
```bash
chmod +x start.sh
./start.sh
```

#### Background Mode
```bash
nohup reflex run > reflex.log 2>&1 &
```

### 8. Verify Installation

1. Open browser to http://localhost:3000
2. Login with `admin` / `changeme`
3. Navigate to Dashboard
4. Try a sample investigation (Domain lookup for "example.com")

## Post-Installation

### Change Default Password

1. Login as admin
2. Navigate to Settings → Account (when implemented)
3. Change password
4. Or reset via database:
```bash
python reset_admin.py
# Enter new credentials
```

### Configure API Services

1. Go to **Settings** page
2. Click **Configure** on desired service
3. Enter API key and base URL
4. Set rate limits
5. Enable service

### Import Demo Data (Optional)

```bash
# Coming soon - sample investigations and reports
python scripts/import_demo_data.py
```

## Troubleshooting

### Port Conflicts

If ports 8000 or 3000 are in use:

**Option 1**: Kill existing processes
```bash
# Linux/macOS
lsof -ti:3000,8000 | xargs kill -9

# Or Reflex-specific
pkill -f "reflex run"
```

**Option 2**: Change ports in `rxconfig.py`
```python
config = rx.Config(
    app_name="app",
    backend_port=8001,
    frontend_port=3001,
)
```

### Permission Errors

```bash
# Linux - fix Python permissions
sudo chown -R $USER:$USER .venv

# Reinstall in user space
pip install --user -r requirements.txt
```

### Database Errors

```bash
# Reset database
rm reflex.db
rm -rf alembic/versions/*
python reset_admin.py
```

### Import Errors

```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall --no-cache-dir
```

### Reflex Not Found

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Verify Reflex installation
pip show reflex

# Reinstall if needed
pip install reflex==0.8.9
```

## Upgrading

### From Previous Version

```bash
# Backup database
cp reflex.db reflex.db.backup

# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Run migrations (if using MySQL)
reflex db migrate

# Restart application
reflex run
```

## Uninstallation

```bash
# Deactivate virtual environment
deactivate

# Remove application
cd ..
rm -rf Ethical-OSINT-Tracker

# Optional: Remove Python packages
pip uninstall -r requirements.txt -y
```

## Next Steps

- Read [User Guide](./USER_GUIDE.md) for feature overview
- Configure [API Integration](./API_INTEGRATION.md) for live data
- Review [Architecture](./ARCHITECTURE.md) for technical details
- Check [Development Guide](./DEVELOPMENT.md) to contribute

## Support

Having installation issues? Check:
- [GitHub Issues](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues)
- [Troubleshooting section](#troubleshooting) above
- [Reflex Documentation](https://reflex.dev/docs/)
