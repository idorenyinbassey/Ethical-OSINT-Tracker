# Ethical OSINT Tracker

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.0+](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Copyright (C) 2025 Idorenyin Bassey](https://img.shields.io/badge/copyright-©%202025%20Idorenyin%20Bassey-lightgrey.svg)](https://github.com/idorenyinbassey)

A comprehensive ethical Open Source Intelligence (OSINT) investigation platform built with **Flask** (Python). Perform legally compliant investigations with domain analysis, IP geolocation, subdomain enumeration, email header forensics, social media reconnaissance, MAC vendor lookup, file metadata extraction, blockchain lookups, phone number verification, and more.

## Features

### Investigation Tools

All tools marked **zero-key** work without any API configuration out of the box.

- **IP Lookup** — ip-api.com geolocation (free, zero-key primary); optional enrichment via IPInfo.io, threat scoring via VirusTotal, port scan via Shodan
- **Domain WHOIS** — Registration data via public RDAP (zero-key)
- **Subdomain Scanner** — crt.sh Certificate Transparency log enumeration + DNS wordlist bruteforce of 75 common subdomains; discovered entries resolved via socket (zero-key)
- **Email Analysis** — Breach detection (Have I Been Pwned) + deliverability (Hunter.io)
- **Email Header Analyser** — Parse raw email headers: full Received chain, originating IP extraction, SPF/DKIM/DMARC flag detection, relay hop visualisation (zero-key)
- **Social Search** — Sherlock/Maigret-style username enumeration across 36 platforms; HTTP response analysis (status code, page content, redirect URL detection) via ThreadPoolExecutor(12) (zero-key)
- **Phone Lookup** — Carrier lookup and validation via NumVerify
- **MAC Vendor Lookup** — OUI prefix to manufacturer resolution via macvendors.com (zero-key)
- **File & Document Forensics** — Metadata extraction for images (EXIF + GPS via Pillow), audio (ID3/Vorbis via mutagen), video (hachoir), PDF (pypdf), DOCX (python-docx), XLSX (openpyxl); replaces the former Image Forensics tool (zero-key for metadata; Google Cloud Vision optional)
- **Crypto / Blockchain Lookup** — Bitcoin balance and transaction history via blockchain.info; Ethereum via blockcypher.com (zero-key)
- **IMEI Lookup** — Device identification via configurable IMEI service

### Case Management
- Create and organise investigations into cases with priority and status tracking
- Link any investigation result to an existing case

### Security & Compliance
- **Authentication** — Argon2 password hashing with Flask-Login session management
- **Rate Limiting** — Per-user in-memory throttling on social search
- **Tor / Proxy Support** — Route all HTTP requests through Tor (`socks5://127.0.0.1:9050`) or any HTTP proxy via the TorProxy setting
- **Graceful Degradation** — Falls back to deterministic mock data when APIs are unavailable
- **Ethical Guidelines** — Built-in reminders on every investigation page

### Tech Stack
- **Backend** — Flask 3, Flask-Login, SQLModel (SQLite / MySQL), httpx[socks]
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
| `IPInfo` | ipinfo.io | IP geolocation (optional enrichment — ip-api.com is the free default) |
| `Shodan` | shodan.io | Port scan / open services |
| `VirusTotal` | virustotal.com | IP threat intelligence |
| `HIBP` | haveibeenpwned.com | Email breach check |
| `Hunter.io` | hunter.io | Email deliverability |
| `NumVerify` | numverify.com | Phone validation |
| `ImageRecognition` | Google Cloud Vision | Face / label detection on uploaded files |
| `IMEIService` | imei.info or similar | IMEI device lookup |
| `TorProxy` | Tor / any HTTP proxy | Route all HTTP requests through Tor or a proxy (`socks5://127.0.0.1:9050`) |

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
│   │   ├── investigation.py # /investigate/ip|domain|subdomain|email|email-header
│   │   │                    #              |social|phone|mac|file|crypto|imei
│   │   ├── cases.py         # /cases  (CRUD)
│   │   └── settings.py      # /settings
│   ├── services/            # External API clients (sync httpx)
│   │   ├── cache.py         # TTL in-memory cache decorator
│   │   ├── ip_client.py     # ip-api.com (primary) + IPInfo.io (optional)
│   │   ├── rdap_client.py   # Public RDAP
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
│   │   ├── crypto_client.py # blockchain.info + blockcypher.com
│   │   └── imei_client.py
│   ├── templates/           # Jinja2 HTML templates
│   │   ├── base.html        # Dark sidebar layout
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── investigation/
│   │   ├── cases/
│   │   └── settings/
│   ├── uploads/             # Uploaded files (gitignored)
│   └── utils/               # crypto, rate_limiter, key_manager, proxy_client
├── alembic/                 # Database migration scripts
├── docs/                    # Documentation
├── tests/                   # pytest test suite
├── requirements.txt
├── run.py                   # Entry point
├── reset_admin.py           # Creates / resets the demo admin user
└── start.sh                 # One-command dev start
```

## Dependencies

Core runtime dependencies (see `requirements.txt` for pinned versions):

| Package | Purpose |
|---|---|
| `flask` | Web framework |
| `flask-login` | Session management |
| `sqlmodel` | ORM (SQLAlchemy wrapper) |
| `httpx[socks]` | HTTP client with SOCKS5 / Tor proxy support |
| `argon2-cffi` | Argon2id password hashing |
| `Pillow` | Image EXIF + GPS metadata extraction |
| `mutagen` | Audio file ID3 / Vorbis tag extraction |
| `pypdf` | PDF metadata extraction |
| `hachoir` | Video file metadata extraction |
| `python-docx` | DOCX document property extraction |
| `openpyxl` | XLSX workbook property extraction |
| `dnspython` | DNS record enumeration (optional; falls back to socket) |

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
- [x] Blockchain address tracking
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
