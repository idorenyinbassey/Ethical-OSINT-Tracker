# Ethical OSINT Tracker

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.0+](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Copyright (C) 2025 Idorenyin Bassey](https://img.shields.io/badge/copyright-©%202025%20Idorenyin%20Bassey-lightgrey.svg)](https://github.com/idorenyinbassey)

A comprehensive ethical Open Source Intelligence (OSINT) investigation platform built with **Flask** (Python). Perform legally compliant investigations with domain analysis, IP geolocation, subdomain enumeration, email forensics, social media reconnaissance, company registry lookups, person search, vehicle identification, file metadata extraction, optional AI image recognition, blockchain analysis, phone verification, IMEI lookup, dark web monitoring, and interactive location mapping — all under one roof with full case management, professional report generation, a built-in plugin framework, and a live link tracker.

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
| **Breach & Password Check** | Standalone HIBP email breach lookup + k-anonymity password check via pwnedpasswords.com — password never leaves the server in full | HIBP key for email; Zero-key for passwords |
| **MAC Vendor Lookup** | OUI prefix to manufacturer resolution via macvendors.com | Zero-key |

#### People & Entities
| Tool | Description | Key required? |
|------|-------------|---------------|
| **Social Search** | Sherlock/Maigret-style username enumeration across **273+ platforms** — social networks, dev tools, gaming, art, music, Nigerian sites (Nairaland, Jobberman), NFT/crypto, Bluesky, Threads, HackerOne, TryHackMe, and more; concurrent via `ThreadPoolExecutor(12)` | Zero-key |
| **Person Search** | Generates 12 curated investigative dork links (Google, LinkedIn, news, court records, Nairaland, SEC EDGAR officers, Scholar, Twitter) + up to 8 plausible username guesses | Zero-key |
| **Company Registry** | Searches **5 jurisdictions in parallel**: US SEC EDGAR, UK Companies House, CAC Nigeria, Corporations Canada, Cyprus DRCOR | Zero-key (UK key optional) |
| **Phone Lookup** | Carrier and country validation via NumVerify | Optional |
| **IMEI Lookup** | Device identification via dash.imei.info API | Optional |

#### Vehicle & Assets
| Tool | Description | Key required? |
|------|-------------|---------------|
| **Vehicle / VIN** | VIN decoding via NHTSA vPIC public API — make, model, year, body class, engine, fuel type | Zero-key |
| **Crypto Lookup** | Bitcoin balance + transaction history via blockchain.info; Ethereum via blockcypher.com | Zero-key |
| **Dark Web Monitor** | Ahmia.fi onion search — indexed dark web content (no Tor required) | Zero-key |

#### File Intelligence
| Tool | Description | Key required? |
|------|-------------|---------------|
| **File & Document Forensics** | Full metadata extraction for images (EXIF + GPS), audio (ID3/Vorbis), video, PDF, DOCX, XLSX; MD5 + SHA-256 hashes, MIME type verification, filesystem timestamps; GPS reverse geocoding via Nominatim OSM; optional Google Vision enrichment (labels, OCR, safe-search) | Zero-key (Google Vision optional) |

### Extensible Investigations (Plugins)

- **Built-in plugin framework** at `/investigate/plugins` for modular checks without changing core routes
- **Built-in plugins** include DNS lookups, WHOIS checks, and hash utilities
- **Plugin run history** is stored like other investigations (`kind=plugin_<name>`) and links to cases

### Link Tracker (IP Grabber)

Generate unique tracking links and 1×1 email pixels that silently capture:

| Signal | Method |
|--------|--------|
| **IP address + ISP + geolocation** | Captured server-side on every hit |
| **Browser fingerprint** | Screen resolution, timezone, language, platform, browser name, plugin list — collected via JS, POSTed silently |
| **GPS coordinates** | Browser shows its native permission prompt; lat/lon/accuracy stored if granted |
| **Email open tracking** | `GET /t/<token>/px.gif` — 1×1 transparent GIF embeds in HTML email |

- **Decoy modes**: show a 404 page, a blank screen, or redirect to any URL after logging
- **Live hit feed**: detail page polls `/tracker/<token>/hits.json` every 3 seconds — new hits slide in with a highlight ring without a page reload
- **Copy helpers**: one-click copy of tracking URL and HTML `<img>` tag for email embedding

### Case Management

- Create cases with title, description, status (`open` / `in_progress` / `closed`), and priority (`low` / `medium` / `high` / `critical`)
- **Threat scoring** — each case gets an automatic threat score (0–100) based on linked investigation confidence, dark web hits, and HIBP breaches; colour-coded badges on the case list
- **Evidence tagging** — tag any investigation as `key_evidence`, `follow_up`, `disputed`, or `corroborated`
- **Investigator Journal** — structured case notes with kinds (`observation`, `lead`, `key_evidence`, `follow_up`)
- **Watchlist** — add IPs, domains, emails, social handles, or crypto addresses; auto-rescanned every 6 hours by APScheduler; alert badge set when results change
- **Bulk CSV import** — import multiple investigation targets at once from a CSV file
- **Auto case correlation** — automatically surfaces other cases sharing the same investigation targets in a "Related Cases" panel
- **Team comments** — add threaded observations to any case

### Report Generation

- **Formats**: PDF, DOCX, HTML, CSV, XLSX
- **Async generation**: background thread with progress bar on the case detail page — no request timeout on large cases
- **SHA-256 fingerprint** embedded in PDF/DOCX/HTML footers for report integrity verification
- **Parallel image prefetch** — profile photos fetched concurrently before rendering (up to 12 workers)
- **STIX 2.1 export** — full bundle with observables, indicators, and relationships for every investigation kind; compatible with MISP, OpenCTI, and other threat intel platforms

### Visualisation

| Feature | Description |
|---------|-------------|
| **Location Intelligence Map** | OpenStreetMap via Leaflet.js — auto-aggregates GPS from IP lookups and EXIF; colour-coded markers |
| **Network Graph** | vis.js relationship map across all cases; entity hub nodes link shared IPs/emails/domains across multiple investigations; star-shaped hub nodes in purple |

### Search & Audit

| Feature | Description |
|---------|-------------|
| **Global Search** | Header search bar queries all investigations, cases, and case notes simultaneously |
| **Audit Log** | Every login, case create/delete, investigation run, and report export is recorded with username, IP, and timestamp; filterable by action type at `/audit` |

### Admin & User Management

- **Admin panel** (`/admin/users`) — list all users, reset passwords, grant/revoke admin, enable/disable accounts, delete users
- **Change password** — available to every user from the Settings page
- **Role-based access** — admin nav link and panel hidden from non-admin users; all admin actions protected by `@admin_required` decorator

### Security

- **Authentication** — Argon2id password hashing with Flask-Login
- **CSRF protection** — Flask-WTF on all forms; public tracking endpoints explicitly exempted
- **Tor / Proxy support** — route all HTTP requests through Tor (`socks5://127.0.0.1:9050`) or any HTTP proxy via the TorProxy setting

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

### 4. Initialise the database & create admin

```bash
python reset_admin.py
```

Creates:
- **Username**: `admin`
- **Password**: `changeme`

> Change this password immediately after first login via **Settings → Change Password** or via the **Admin panel**.

### 5. Run

```bash
python run.py
```

Open [http://localhost:3000](http://localhost:3000).

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

---

## API Services Configuration

Navigate to **Settings → API Settings** to configure external services. No restart required.

| Service key | Provider | Required for |
|---|---|---|
| `IPInfo` | ipinfo.io | IP geolocation enrichment |
| `Shodan` | shodan.io | Port scan / open service discovery |
| `VirusTotal` | virustotal.com | IP threat intelligence |
| `HIBP` | haveibeenpwned.com | Email breach detection |
| `Hunter.io` | hunter.io | Email deliverability verification |
| `NumVerify` | numverify.com | Phone number validation |
| `IMEIService` | dash.imei.info | IMEI device lookup (base URL: `https://dash.imei.info/api`) |
| `ImageRecognition` | Google Cloud Vision | Face / label detection on images |
| `TorProxy` | Tor / any HTTP proxy | Route all HTTP through Tor (`socks5://127.0.0.1:9050`) |

---

## Project Structure

```
Ethical-OSINT-Tracker/
├── app/
│   ├── __init__.py              # Flask app factory + blueprint registration + CSRF + scheduler
│   ├── config.py                # Flask configuration
│   ├── db.py                    # SQLModel engine + init_db() + idempotent ALTER TABLE migrations
│   ├── models/
│   │   ├── user.py              # User (username, password_hash, is_active, is_admin)
│   │   ├── case.py              # Case (title, status, priority)
│   │   ├── investigation.py     # Investigation (kind, query, result_json, tags, case_id)
│   │   ├── case_note.py         # Investigator Journal entries
│   │   ├── case_comment.py      # Team comments
│   │   ├── watchlist.py         # WatchlistTarget (has_alert, alert_message)
│   │   ├── tracking_link.py     # Tracking link (token, decoy_mode)
│   │   ├── tracking_hit.py      # Hit record (IP, fingerprint, GPS)
│   │   ├── audit_log.py         # Audit log (action, user, IP, timestamp)
│   │   └── api_config.py        # API key storage
│   ├── repositories/            # Data access layer (session_scope pattern)
│   ├── routes/
│   │   ├── auth.py              # /login  /register  /logout
│   │   ├── dashboard.py         # /
│   │   ├── investigation.py     # /investigate/* (all tools + graph + map + watchlist)
│   │   ├── cases.py             # /cases (CRUD + exports + async report + STIX)
│   │   ├── tracker.py           # /t/<token> (public hits) + /tracker (management UI)
│   │   ├── search.py            # /search (global full-text search)
│   │   ├── audit.py             # /audit (audit log viewer)
│   │   ├── admin.py             # /admin/users (admin panel)
│   │   └── settings.py          # /settings (API keys + change password)
│   ├── services/
│   │   ├── cache.py             # TTL in-memory cache decorator
│   │   ├── ip_client.py         # ip-api.com + IPInfo.io
│   │   ├── rdap_client.py       # Public RDAP
│   │   ├── subdomain_client.py  # crt.sh CT logs + DNS wordlist
│   │   ├── hibp_client.py       # Have I Been Pwned + k-anonymity password check
│   │   ├── hunter_client.py     # Hunter.io email verification
│   │   ├── social_client.py     # 273-platform concurrent username search
│   │   ├── company_client.py    # EDGAR + Companies House + CAC + Canada + Cyprus
│   │   ├── person_client.py     # Name dork links + username guesses
│   │   ├── vehicle_client.py    # NHTSA vPIC VIN decoder
│   │   ├── file_forensics_client.py
│   │   ├── crypto_client.py
│   │   ├── imei_client.py       # dash.imei.info API
│   │   ├── stix_export.py       # STIX 2.1 bundle builder
│   │   └── report_exporter.py   # PDF + DOCX + HTML + CSV + XLSX (async-capable)
│   ├── plugins/                 # Extensible investigation plugins (DNS, WHOIS, hash, ...)
│   ├── templates/
│   │   ├── base.html            # Sidebar + search bar + dark/light/system theme
│   │   ├── admin/users.html
│   │   ├── audit/index.html
│   │   ├── search/results.html
│   │   ├── tracker/             # index, new, detail, land (decoy page)
│   │   ├── investigation/       # All tool pages + breach.html
│   │   ├── cases/               # index, detail (async export + STIX), new, edit
│   │   └── settings/index.html  # API keys + change password
│   └── utils/
│       ├── audit.py             # log() helper — callable from any Flask route
│       ├── scheduler.py         # APScheduler watchlist rescan job (every 6h)
│       └── proxy_config.py      # get_http_client() with Tor/proxy support
├── docs/                        # Documentation
├── requirements.txt
├── run.py
├── reset_admin.py
└── start.sh
```

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `flask` | ≥ 3.0.0 | Web framework |
| `flask-login` | ≥ 0.6.3 | Session management |
| `flask-wtf` | ≥ 1.2.0 | CSRF protection |
| `gunicorn` | ≥ 21.0.0 | Production WSGI server |
| `APScheduler` | ≥ 3.10.0 | Watchlist auto-rescan background job |
| `sqlmodel` | ≥ 0.0.21 | ORM (SQLite / MySQL) |
| `PyMySQL` | 1.1.1 | MySQL driver (optional) |
| `argon2-cffi` | 23.1.0 | Argon2id password hashing |
| `httpx[socks]` | ≥ 0.23 | HTTP client with SOCKS5/Tor support |
| `Pillow` | ≥ 10.4.0 | Image EXIF + GPS metadata |
| `mutagen` | ≥ 1.47.0 | Audio file tag extraction |
| `pypdf` | ≥ 4.0.0 | PDF metadata |
| `hachoir` | ≥ 3.1.3 | Video metadata |
| `python-docx` | ≥ 1.1.0 | DOCX metadata + report generation |
| `openpyxl` | ≥ 3.1.0 | XLSX metadata + report generation |
| `fpdf2` | ≥ 2.7.0 | PDF report generation |
| `dnspython` | ≥ 2.6.0 | DNS record enumeration (optional) |
| `beautifulsoup4` | ≥ 4.12.0 | HTML parsing for dark web results |
| `alembic` | ≥ 1.13.0 | Database migrations |
| `pytest` | ≥ 7.0 | Test runner |

---

## Security & Ethics

### Ethical Use Policy

This tool is designed **exclusively** for:
- Authorised security research and penetration testing (with written permission)
- Lawful investigations with proper consent or legal authority
- Academic research and education
- OSINT training and awareness

**Prohibited uses**: unauthorised surveillance, stalking, harassment, doxxing, privacy violations, or any use without proper legal authority.

### Security Best Practices

1. Set a strong `SECRET_KEY` environment variable in production
2. Change the default `admin / changeme` credentials immediately after first login
3. Use HTTPS in production (reverse proxy via nginx or Caddy)
4. Never commit `.env` or API key files to source control
5. Rotate API keys if they may have been exposed

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

**IMEI lookup fails**
- Ensure the base URL in Settings is `https://dash.imei.info/api`
- The imei.info API requires a funded account balance (minimum $5) to process requests

**Watchlist auto-rescan not running**
```bash
pip install APScheduler>=3.10.0
```
The scheduler starts automatically when the app starts. Logs appear as `APScheduler started — watchlist rescan every 6h`.

---

## Roadmap

### Completed
- [x] 17+ investigation tools (IP, domain, subdomain, email, breach/password, email header, social, phone, IMEI, MAC, file forensics, crypto, dark web, person, company, vehicle)
- [x] Extensible plugin investigation framework (DNS, WHOIS, hash plugins)
- [x] PDF / DOCX / HTML / CSV / XLSX report exports with SHA-256 fingerprint
- [x] Async report generation with progress bar
- [x] STIX 2.1 threat intel export
- [x] Network graph with cross-case entity hub nodes
- [x] Location intelligence map (OpenStreetMap + Leaflet.js)
- [x] Mobile-first responsive UI with dark / light / system theme
- [x] Case management with threat scoring, evidence tagging, investigator journal
- [x] Watchlist with 6-hour auto-rescan (APScheduler)
- [x] Bulk CSV import for investigation targets
- [x] Link tracker — IP grabber with browser fingerprint, GPS, email pixel, live feed
- [x] Global search across investigations, cases, and notes
- [x] Audit log with filterable viewer
- [x] Standalone breach & k-anonymity password check
- [x] Admin panel (user management, password reset, role management)
- [x] Change password for all users

### Planned
- [ ] Extended social search beyond 300 platforms
- [ ] HaveIBeenPwned paste search integration
- [ ] OpenStreetMap population density heatmap overlay
- [ ] Multi-factor authentication (TOTP)
- [ ] Email / webhook notifications on watchlist alerts
- [ ] Scheduled report delivery

---

## Documentation

- [Installation Guide](./docs/INSTALLATION.md)
- [User Guide](./docs/USER_GUIDE.md)
- [Architecture](./docs/ARCHITECTURE.md)
- [API Integration](./docs/API_INTEGRATION.md)
- [Development Guide](./docs/DEVELOPMENT.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)
- [Termux / Android](./docs/TERMUX.md)

---

## License

Licensed under the **GNU General Public License v3.0** — see [LICENSE](LICENSE).

## Support

- **Issues**: [GitHub Issues](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues)
- **Discussions**: [GitHub Discussions](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/discussions)

---

**Built for the ethical OSINT community · © 2025 Idorenyin Bassey**
