# Ethical OSINT Tracker

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.0+](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Copyright (C) 2025 Idorenyin Bassey](https://img.shields.io/badge/copyright-©%202025%20Idorenyin%20Bassey-lightgrey.svg)](https://github.com/idorenyinbassey)

A comprehensive ethical Open Source Intelligence (OSINT) investigation platform built with **Flask** (Python). Perform legally compliant investigations with domain analysis, IP geolocation, email validation, social media reconnaissance, phone number verification, image forensics, and more.

## Features

### Investigation Tools
- **IP Lookup** — Geolocation (IPInfo), threat scoring (VirusTotal), port scan (Shodan)
- **Domain WHOIS** — Registration data via public RDAP (no key required)
- **Email Analysis** — Breach detection (Have I Been Pwned) + deliverability (Hunter.io)
- **Social Media Search** — Username enumeration across 10 platforms
- **Phone Intelligence** — Carrier lookup and validation via NumVerify
- **Image Forensics** — EXIF metadata extraction + optional Google Cloud Vision AI
- **IMEI Lookup** — Device identification via configurable IMEI service

### Case Management
- Create and organise investigations into cases with priority and status tracking
- Link any investigation result to an existing case

### Security & Compliance
- **Authentication** — Argon2 password hashing with Flask-Login session management
- **Rate Limiting** — Per-user in-memory throttling on social search
- **Graceful Degradation** — Falls back to deterministic mock data when APIs are unavailable
- **Ethical Guidelines** — Built-in reminders on every investigation page

### Tech Stack
- **Backend** — Flask 3, Flask-Login, SQLModel (SQLite / MySQL), httpx
- **Frontend** — Jinja2 templates, Tailwind CSS (CDN), dark-mode UI
- **Services** — All external API calls are synchronous (no asyncio required)

## Quick Start

### 1. Clone

```bash
git clone https://github.com/idorenyinbassey/Ethical-OSINT-Tracker.git
cd Ethical-OSINT-Tracker
```

### 2. Create a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialise the database & create demo admin

```bash
python reset_admin.py
```

This creates:
- **Username**: `admin`
- **Password**: `changeme`

> Change this password immediately in any non-local deployment.

### 5. Run

```bash
python run.py
```

Open [http://localhost:3000](http://localhost:3000).

Or use the convenience script:

```bash
chmod +x start.sh
./start.sh
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_URL` | `sqlite:///./dev.db` | SQLAlchemy database URL |
| `SECRET_KEY` | random (generated at startup) | Flask session signing key — set a fixed value in production |

Example `.env` (load with `python-dotenv` or export manually):

```env
DB_URL=sqlite:///./dev.db
SECRET_KEY=change-me-to-something-long-and-random
```

For MySQL in production:

```env
DB_URL=mysql+pymysql://osint_user:password@localhost/osint_tracker
```

## API Services Configuration

Navigate to **Settings** in the app to configure external OSINT services. No restart required — keys are stored in the database and read at request time.

| Service key | Provider | Required for |
|---|---|---|
| `IPInfo` | ipinfo.io | IP geolocation |
| `Shodan` | shodan.io | Port scan / open services |
| `VirusTotal` | virustotal.com | IP threat intelligence |
| `HIBP` | haveibeenpwned.com | Email breach check |
| `Hunter.io` | hunter.io | Email deliverability |
| `NumVerify` | numverify.com | Phone validation |
| `SocialSearch` | GitHub / Twitter APIs | Authenticated social search |
| `ImageRecognition` | Google Cloud Vision | Face / label detection |
| `IMEIService` | imei.info or similar | IMEI device lookup |

For `SocialSearch`, store API keys as JSON in the **Notes** field:
```json
{"github": "ghp_xxx", "twitter": "AAA...bearer..."}
```

API keys are stored in plaintext. For production, implement a secrets manager backend in `app/utils/key_manager.py`.

## Project Structure

```
Ethical-OSINT-Tracker/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Flask configuration
│   ├── db.py                # SQLModel engine + init_db()
│   ├── models/              # SQLModel table definitions
│   ├── repositories/        # Data access layer (session_scope)
│   ├── routes/              # Flask blueprints
│   │   ├── auth.py          # /login  /register  /logout
│   │   ├── dashboard.py     # /
│   │   ├── investigation.py # /investigate/ip|domain|email|social|phone|image|imei
│   │   ├── cases.py         # /cases  (CRUD)
│   │   └── settings.py      # /settings
│   ├── services/            # External API clients (sync httpx)
│   ├── templates/           # Jinja2 HTML templates
│   │   ├── base.html        # Dark sidebar layout
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── investigation/
│   │   ├── cases/
│   │   └── settings/
│   ├── uploads/             # Uploaded images (gitignored)
│   └── utils/               # crypto, rate_limiter, key_manager
├── alembic/                 # Database migration scripts
├── docs/                    # Documentation
├── tests/                   # pytest test suite
├── requirements.txt
├── run.py                   # Entry point
├── reset_admin.py           # Creates / resets the demo admin user
└── start.sh                 # One-command dev start
```

## Security & Ethics

### Ethical Use Policy

This tool is designed **exclusively** for:
- Authorized security research
- Lawful investigations with proper consent
- Academic research and education
- Penetration testing with written permission

**Prohibited uses**: unauthorized surveillance, harassment, doxxing, privacy violations, illegal data collection.

### Security Best Practices

1. Set a strong `SECRET_KEY` environment variable in production
2. Change the default `admin / changeme` credentials immediately
3. Never commit `.env` or API key files to source control
4. Use HTTPS in production (see [Deployment Guide](./docs/DEPLOYMENT.md))
5. For production deployments, implement real API key encryption in `app/utils/crypto.py`

## Development

```bash
# Install dev dependencies
pip install black ruff pytest

# Run tests
PYTHONPATH=. pytest -q

# Format and lint
black app/
ruff check app/ --fix
```

See [Development Guide](./docs/DEVELOPMENT.md) for contributing guidelines.

## Documentation

- [Installation Guide](./docs/INSTALLATION.md)
- [Architecture](./docs/ARCHITECTURE.md)
- [API Integration](./docs/API_INTEGRATION.md)
- [Development Guide](./docs/DEVELOPMENT.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)
- [Termux / Android](./docs/TERMUX.md)

## Troubleshooting

**Port 3000 already in use**
```bash
lsof -ti:3000 | xargs kill -9
```

**Database reset**
```bash
rm dev.db
python reset_admin.py
```

**Import errors**
```bash
pip install -r requirements.txt --force-reinstall --no-cache-dir
```

## Roadmap

- [ ] PDF/DOCX report exports
- [ ] Advanced network graph visualization
- [ ] Real-time collaboration features
- [ ] Blockchain address tracking
- [ ] Dark web monitoring integration
- [ ] Plugin architecture for custom tools

## License

Licensed under the **GNU General Public License v3.0** — see [LICENSE](LICENSE).

## Acknowledgments

- [Flask](https://flask.palletsprojects.com/) — Web framework
- [Flask-Login](https://flask-login.readthedocs.io/) — Authentication
- [SQLModel](https://sqlmodel.tiangolo.com/) — Database ORM
- [Tailwind CSS](https://tailwindcss.com/) — Utility-first CSS
- [httpx](https://www.python-httpx.org/) — HTTP client
- OSINT community for methodology and best practices

## Support

- **Issues**: [GitHub Issues](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues)
- **Discussions**: [GitHub Discussions](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/discussions)

---

**Built for the ethical OSINT community**

> This software is provided for educational and lawful purposes only. Users are solely responsible for ensuring their use complies with all applicable laws and regulations.
