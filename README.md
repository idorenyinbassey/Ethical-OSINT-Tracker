# Ethical OSINT Tracker

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.0+](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Copyright (C) 2025 Idorenyin Bassey](https://img.shields.io/badge/copyright-©%202025%20Idorenyin%20Bassey-lightgrey.svg)](https://github.com/idorenyinbassey)

A comprehensive ethical Open Source Intelligence (OSINT) investigation platform built with **Flask** (Python). Perform legally compliant investigations with domain analysis, IP geolocation, subdomain enumeration, email forensics, social media reconnaissance, company registry lookups, person search, vehicle identification, file metadata extraction, blockchain analysis, phone verification, and interactive location mapping.

---

## Features

### Investigation Tools

Tools marked **zero-key** work without any API configuration out of the box.

#### Network & Domain
| Tool | Description | Key required? |
|------|-------------|---------------|
| **IP Lookup** | ip-api.com geolocation (free primary); optional enrichment via VirusTotal threat scoring and Shodan port scan | Zero-key (enrichment optional) |
| **Domain WHOIS** | Registration data, nameservers, status, creation/expiry via public RDAP (rdap.org + IANA fallback) | Zero-key |
| **Subdomain Scanner** | crt.sh Certificate Transparency log enumeration + DNS wordlist bruteforce (75 prefixes) + `socket` resolution | Zero-key |
| **Email Analysis** | Breach detection (Have I Been Pwned) + deliverability check (Hunter.io) | Optional |
| **Email Header Analyser** | Parse raw email headers: full Received chain, originating IP extraction, SPF/DKIM/DMARC detection, relay hop visualisation | Zero-key |
| **MAC Vendor Lookup** | OUI prefix to manufacturer resolution via macvendors.com | Zero-key |

#### People & Entities
| Tool | Description | Key required? |
|------|-------------|---------------|
| **Social Search** | Sherlock/Maigret-style username enumeration across **273 platforms** — social networks, dev tools, gaming, art, music, Nigerian sites (Nairaland, Jobberman), NFT/crypto, Bluesky, Threads, HackerOne, TryHackMe, and more; concurrent via `ThreadPoolExecutor(12)` | Zero-key |
| **Person Search** | Generates 12 curated investigative dork links (Google, LinkedIn, news, court records, Nairaland, SEC EDGAR officers, Scholar, Twitter) + up to 8 plausible username guesses to run through Social Search | Zero-key |
| **Company Registry** | Searches **5 jurisdictions in parallel**: US SEC EDGAR (free API), UK Companies House (optional key), CAC Nigeria (public portal), Corporations Canada (public HTML), Cyprus DRCOR (manual link) | Zero-key (UK key optional) |
| **Phone Lookup** | Carrier and country validation via NumVerify | Optional |
| **IMEI Lookup** | Device identification via configurable IMEI service | Optional |

#### Vehicle & Assets
| Tool | Description | Key required? |
|------|-------------|---------------|
| **Vehicle / VIN** | VIN decoding via NHTSA vPIC public API — make, model, year, body class, engine, fuel type, drive type, transmission, plant country, manufacturer | Zero-key |
| **Crypto Lookup** | Bitcoin balance + transaction history via blockchain.info; Ethereum via blockcypher.com | Zero-key |

#### File Intelligence
| Tool | Description | Key required? |
|------|-------------|---------------|
| **File & Document Forensics** | Full metadata extraction for images (EXIF + GPS), audio (ID3/Vorbis), video, PDF, DOCX, XLSX; **MD5 + SHA-256 hashes**, MIME type verification, filesystem timestamps (created/modified/accessed), device make/model/software; **GPS reverse geocoding** via Nominatim OSM (free) | Zero-key |
| **Dark Web Monitor** | Ahmia.fi onion search — indexed dark web content (no Tor required) | Zero-key |

### Visualisation
| Feature | Description |
|---------|-------------|
| **Location Intelligence Map** | OpenStreetMap via Leaflet.js — auto-aggregates GPS coordinates from all IP lookups and image EXIF data; colour-coded markers (blue = IP, green = image GPS) with investigation popups |
| **Network Graph** | vis.js relationship map of all cases and investigations; subdomain scan results expand as child nodes; dark arrow edges visible on both light and dark backgrounds |

### Case Management
- Create cases with title, description, status (`open` / `in_progress` / `closed`), and priority (`low` / `medium` / `high` / `critical`)
- **Mandatory case selection** — every investigation tool requires a case to be selected before running; auto-saves the active case to your session
- Link any investigation result to a case; browse all linked investigations on the case detail page
- **Auto case correlation** — automatically detects and surfaces other cases that share investigation targets (same IP, domain, username, etc.) in a "Related Cases" panel
- **Team Notes** — add comments and observations to any case
- Export full case reports in **PDF, DOCX, HTML, CSV, and XLSX** formats

### UI & UX
- **Mobile-first responsive design** — hamburger sidebar on mobile, full sidebar on desktop
- **Light / Dark / System theme** — persisted in `localStorage`; system theme follows OS preference
- **Active case banner** — active case name + recent investigation history always visible in the sidebar
- Tailwind CSS (CDN) with dark-mode class strategy

### Security
- **Authentication** — Argon2id password hashing with Flask-Login session management
- **CSRF protection** — Flask-WTF on all forms including standalone auth pages
- **Tor / Proxy support** — route all HTTP requests through Tor (`socks5://127.0.0.1:9050`) or any HTTP proxy via the TorProxy setting
- **Ethical guidelines** — built-in reminders on every investigation page

---

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

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_URL` | `sqlite:///./dev.db` | SQLAlchemy database URL |
| `SECRET_KEY` | random (generated at startup) | Flask session signing key — set a fixed value in production |

Example `.env`:

```env
DB_URL=sqlite:///./dev.db
SECRET_KEY=change-me-to-something-long-and-random
```

For MySQL in production:

```env
DB_URL=mysql+pymysql://osint_user:password@localhost/osint_tracker
```

---

## API Services Configuration

Navigate to **Settings → API Settings** in the app to configure external services. No restart required — keys are read at request time.

| Service key | Provider | Required for |
|---|---|---|
| `IPInfo` | ipinfo.io | IP geolocation enrichment (ip-api.com is the free default) |
| `Shodan` | shodan.io | Port scan / open service discovery |
| `VirusTotal` | virustotal.com | IP threat intelligence and malware scoring |
| `HIBP` | haveibeenpwned.com | Email breach detection |
| `Hunter.io` | hunter.io | Email deliverability verification |
| `NumVerify` | numverify.com | Phone number validation |
| `companies_house` | companieshouse.gov.uk | UK Companies House company search |
| `ImageRecognition` | Google Cloud Vision | Face / label detection on uploaded images |
| `IMEIService` | imei.info or similar | IMEI device lookup |
| `TorProxy` | Tor / any HTTP proxy | Route all HTTP through Tor or a proxy (`socks5://127.0.0.1:9050`) |

---

## Project Structure

```
Ethical-OSINT-Tracker/
├── app/
│   ├── __init__.py              # Flask app factory + context processors
│   ├── config.py                # Flask configuration
│   ├── db.py                    # SQLModel engine + init_db()
│   ├── models/
│   │   ├── case.py              # Case (title, status, priority)
│   │   ├── investigation.py     # Investigation (kind, query, result_json, case_id)
│   │   ├── case_comment.py      # Team notes
│   │   ├── user.py
│   │   └── api_config.py        # Encrypted API key storage
│   ├── repositories/            # Data access layer (session_scope pattern)
│   │   ├── base.py
│   │   ├── case_repository.py
│   │   ├── investigation_repository.py  # includes find_related_cases()
│   │   ├── case_comment_repository.py
│   │   └── api_config_repository.py
│   ├── routes/
│   │   ├── auth.py              # /login  /register  /logout
│   │   ├── dashboard.py         # /
│   │   ├── investigation.py     # /investigate/* (all tools + graph + map)
│   │   ├── cases.py             # /cases (CRUD + exports + correlation)
│   │   └── settings.py          # /settings
│   ├── services/                # External API clients (sync httpx)
│   │   ├── cache.py             # TTL in-memory cache decorator
│   │   ├── ip_client.py         # ip-api.com + IPInfo.io
│   │   ├── rdap_client.py       # Public RDAP (rdap.org + IANA fallback)
│   │   ├── subdomain_client.py  # crt.sh CT logs + DNS wordlist
│   │   ├── hibp_client.py       # Have I Been Pwned
│   │   ├── hunter_client.py     # Hunter.io email verification
│   │   ├── email_header_client.py
│   │   ├── social_client.py     # 273-platform concurrent username search
│   │   ├── company_client.py    # EDGAR + Companies House + CAC + Canada + Cyprus
│   │   ├── person_client.py     # Name dork links + username guesses
│   │   ├── vehicle_client.py    # NHTSA vPIC VIN decoder
│   │   ├── file_forensics_client.py  # EXIF + GPS + hashes + geocoding
│   │   ├── numverify_client.py
│   │   ├── virustotal_client.py
│   │   ├── shodan_client.py
│   │   ├── mac_client.py
│   │   ├── crypto_client.py
│   │   ├── imei_client.py
│   │   └── report_exporter.py   # PDF + DOCX + HTML + CSV + XLSX
│   ├── templates/
│   │   ├── base.html            # Mobile sidebar + light/dark/system theme
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── investigation/
│   │   │   ├── ip.html
│   │   │   ├── domain.html
│   │   │   ├── subdomain.html
│   │   │   ├── email.html
│   │   │   ├── email_header.html
│   │   │   ├── social.html
│   │   │   ├── person.html      # Person / full name search
│   │   │   ├── company.html     # Company registry (5 jurisdictions)
│   │   │   ├── vehicle.html     # VIN lookup
│   │   │   ├── phone.html
│   │   │   ├── mac.html
│   │   │   ├── file_forensics.html
│   │   │   ├── crypto.html
│   │   │   ├── imei.html
│   │   │   ├── darkweb.html
│   │   │   ├── graph.html       # vis.js network graph
│   │   │   └── map.html         # Leaflet.js location map
│   │   ├── cases/
│   │   │   ├── index.html       # Mobile cards + desktop table
│   │   │   ├── detail.html      # Investigations + notes + related cases + exports
│   │   │   ├── new.html
│   │   │   └── edit.html
│   │   └── settings/
│   ├── uploads/                 # Uploaded files (gitignored)
│   └── utils/                   # crypto, rate_limiter, key_manager, proxy_config
├── alembic/                     # Database migrations
├── docs/                        # Documentation
├── tests/                       # pytest test suite
├── requirements.txt
├── run.py
├── reset_admin.py
└── start.sh
```

---

## Dependencies

All dependencies are in `requirements.txt`. The table below summarises each package's role:

| Package | Version | Purpose |
|---|---|---|
| `flask` | ≥ 3.0.0 | Web framework |
| `flask-login` | ≥ 0.6.3 | Session management and `@login_required` |
| `flask-wtf` | ≥ 1.2.0 | CSRF protection on all forms |
| `gunicorn` | ≥ 21.0.0 | Production WSGI server |
| `sqlmodel` | ≥ 0.0.21 | ORM built on SQLAlchemy + Pydantic |
| `PyMySQL` | 1.1.1 | MySQL driver (optional; SQLite used by default) |
| `argon2-cffi` | 23.1.0 | Argon2id password hashing |
| `httpx[socks]` | ≥ 0.23 | Async-compatible HTTP client with SOCKS5/Tor support |
| `Pillow` | ≥ 10.4.0 | Image EXIF, GPS, device metadata extraction |
| `mutagen` | ≥ 1.47.0 | Audio file ID3 / Vorbis / AAC tag reading |
| `pypdf` | ≥ 4.0.0 | PDF metadata and page count |
| `hachoir` | ≥ 3.1.3 | Video file metadata extraction |
| `python-docx` | ≥ 1.1.0 | DOCX document property extraction |
| `openpyxl` | ≥ 3.1.0 | XLSX workbook property extraction + XLSX report generation |
| `fpdf2` | ≥ 2.7.0 | PDF report generation |
| `dnspython` | ≥ 2.6.0 | MX / NS / TXT DNS record resolution (optional; falls back to socket) |
| `beautifulsoup4` | ≥ 4.12.0 | HTML parsing for dark web search results |
| `pytest` | ≥ 7.0 | Test runner |

> All other features (company search, VIN decoding, person search, GPS reverse geocoding, social username search) rely only on `httpx` and Python standard-library modules — no additional packages required.

---

## Installation on Android / Termux

See [docs/TERMUX.md](./docs/TERMUX.md) for full instructions. Key system packages:

```bash
pkg install python libxml2 libxslt libjpeg-turbo
pip install -r requirements.txt
```

---

## Security & Ethics

### Ethical Use Policy

This tool is designed **exclusively** for:
- Authorised security research and penetration testing (with written permission)
- Lawful investigations with proper consent or legal authority
- Academic research and education
- OSINT training and awareness

**Prohibited uses**: unauthorised surveillance, stalking, harassment, doxxing, privacy violations, illegal data collection, or any use without proper legal authority.

### Security Best Practices

1. Set a strong `SECRET_KEY` environment variable in production
2. Change the default `admin / changeme` credentials immediately after first login
3. Never commit `.env` or API key files to source control
4. Use HTTPS in production (reverse proxy via nginx or Caddy)
5. API keys are encrypted at rest using a Fernet key derived from `SECRET_KEY`

---

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

---

## Documentation

- [Installation Guide](./docs/INSTALLATION.md)
- [Architecture](./docs/ARCHITECTURE.md)
- [API Integration](./docs/API_INTEGRATION.md)
- [Development Guide](./docs/DEVELOPMENT.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)
- [Termux / Android](./docs/TERMUX.md)

---

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

**WHOIS / RDAP returning no results**

The RDAP client retries against both `rdap.org` and `iana.org` with a 15-second timeout. If both fail, the domain may not exist or RDAP is temporarily unavailable.

**Social search showing all errors**

Some platforms block automated requests. Results depend on network conditions. Errors on individual sites do not affect the others — the tool reports per-site status.

---

## Roadmap

- [x] PDF / DOCX / HTML / CSV / XLSX report exports
- [x] Advanced network graph visualisation with subdomain expansion
- [x] Location intelligence map (OpenStreetMap + Leaflet.js)
- [x] Mobile-first responsive UI with dark / light / system theme
- [x] Social username search across 273 platforms
- [x] Company registry search (US, UK, Nigeria, Canada, Cyprus)
- [x] Person / full name investigation helper
- [x] Vehicle / VIN decoding (NHTSA vPIC)
- [x] Enhanced file forensics (hashes, MIME, timestamps, GPS geocoding)
- [x] Automatic case correlation (detect shared entities across cases)
- [x] Mandatory case selection for all investigation tools
- [x] Real-time collaboration via team notes on cases
- [x] Blockchain address tracking
- [x] Dark web monitoring integration
- [x] Plugin architecture for custom tools
- [ ] Extended social search beyond 300 platforms
- [ ] OpenStreetMap population density heatmap overlay
- [ ] Full-text search across all saved investigation results
- [ ] Multi-user role-based access control (RBAC)

---

## License

Licensed under the **GNU General Public License v3.0** — see [LICENSE](LICENSE).

## Acknowledgments

- [Flask](https://flask.palletsprojects.com/) — Web framework
- [Flask-Login](https://flask-login.readthedocs.io/) — Authentication
- [SQLModel](https://sqlmodel.tiangolo.com/) — Database ORM
- [Tailwind CSS](https://tailwindcss.com/) — Utility-first CSS
- [httpx](https://www.python-httpx.org/) — HTTP client
- [vis.js](https://visjs.org/) — Network graph visualisation
- [Leaflet.js](https://leafletjs.com/) + [OpenStreetMap](https://www.openstreetmap.org/) — Location map
- OSINT community for methodology and best practices

## Support

- **Issues**: [GitHub Issues](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues)
- **Discussions**: [GitHub Discussions](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/discussions)

---

**Built for the ethical OSINT community**
