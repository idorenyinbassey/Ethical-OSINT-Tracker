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
| **Email Analysis** | Breach detection (free via XposedOrNot by default, richer detail with an optional paid HIBP key) + deliverability check (Hunter.io) | Zero-key (enrichment optional) |
| **Email Header Analyser** | Parse raw email headers: full Received chain, originating IP extraction, SPF/DKIM/DMARC detection, relay hop visualisation | Zero-key |
| **Breach & Password Check** | Standalone breach lookup (free via XposedOrNot, or HIBP if a paid key is configured) + k-anonymity password check via pwnedpasswords.com — password never leaves the server in full | Zero-key |
| **MAC Vendor Lookup** | OUI prefix to manufacturer resolution via macvendors.com | Zero-key |

#### People & Entities
| Tool | Description | Key required? |
|------|-------------|---------------|
| **Social Search** | Sherlock/Maigret-style username enumeration across **273+ platforms** — social networks, dev tools, gaming, art, music, Nigerian sites (Nairaland, Jobberman), NFT/crypto, Bluesky, Threads, HackerOne, TryHackMe, and more; concurrent via `ThreadPoolExecutor(12)` | Zero-key |
| **Person Search** | Generates 12 curated investigative dork links (Google, LinkedIn, news, court records, Nairaland, SEC EDGAR officers, Scholar, Twitter) + up to 8 plausible username guesses | Zero-key |
| **Company Registry** | Searches **11 jurisdictions in parallel**: US SEC EDGAR, UK Companies House, CAC Nigeria, Corporations Canada, Cyprus DRCOR, Singapore ACRA, Estonia e-Business Register, Ireland CRO, Brazil CNPJ, Australia ABN Lookup, New Zealand NZBN | Zero-key (UK/AU/NZ keys optional) |
| **Phone Lookup** | Carrier and country validation via NumVerify | Optional |
| **IMEI Lookup** | Brand/model via a bundled 255k-entry offline TAC database (free, no key, never runs out); optional dash.imei.info key adds blacklist/stolen/warranty status | Zero-key |

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
| **Network Graph** | vis.js relationship map across all cases; entity hub nodes link shared IPs/emails/domains/orgs/crypto addresses across multiple investigations (including bio-scraped social contacts, crypto transaction counterparties, subdomain-resolved IPs, Shodan-discovered orgs/hostnames, dark web `.onion` domains, and company registry contact info) and Link Tracker (IP Grabber) hits; star-shaped hub nodes in purple |

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

### 2. Run

```bash
./start.sh
```

That's it — no manual virtualenv or `pip install -r requirements.txt`
needed. `start.sh` prefers [pipx](https://pipx.pypa.io) (installs it
automatically if missing, isolated from your system Python) and falls
back to a local `.venv` on its own if pipx isn't available. It also
generates `SECRET_KEY` and `API_KEYS_FERNET_KEY` once and persists them to
`secrets.env` — so restarts never invalidate sessions or break previously
saved API keys.

On a brand-new database it prompts you for the admin account password
(minimum 8 characters) with the terminal input **hidden** — nothing is
echoed to the screen, and it's never written to shell history:

```
Set the admin account password (min. 8 characters).
Input is hidden and is never written to shell history.
  Admin password:
  Confirm password:
```

- **Username**: `admin` (fixed)
- **Password**: whatever you enter at the prompt

For non-interactive/scripted setups (CI, Docker) you can still supply it
via the environment instead, which skips the prompt:
```bash
ADMIN_PASSWORD='choose-a-strong-password' ./start.sh
```

> To change the password later, run `./start.sh --reset-admin` — see
> [Resetting the admin password](#resetting-the-admin-password).

**Prefer to do it by hand?** The manual venv method still works:
```bash
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
ADMIN_PASSWORD='choose-a-strong-password' python reset_admin.py
```

**Development server** (Werkzeug, debug off unless enabled) — set `FLASK_DEV=1`:

```bash
FLASK_DEV=1 ./start.sh            # debug stays OFF
FLASK_DEV=1 FLASK_DEBUG=1 python run.py   # debug ON (never in production)
```

Open [http://localhost:3000](http://localhost:3000) and log in as `admin`.

> **Note:** `start.sh` only auto-creates the admin when the database file does
> **not** yet exist. If `dev.db` is already present, admin creation is skipped —
> use `./start.sh --reset-admin` (see below) to (re)set the password.

---

## CLI Commands

`./start.sh` (or a manual `pipx install .`) installs four console-script
commands onto your `PATH`. `start.sh` wraps `osint-tracker` with secrets
persistence and interactive admin-password setup — calling these commands
directly skips that, so read the caveats below before relying on them
standalone.

| Command | Does |
|---|---|
| `osint-tracker` | Launches the server. Honors `FLASK_DEV`, `FLASK_HOST`, `FLASK_PORT`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT` — same environment variables `start.sh` uses. |
| `osint-tracker-reset-admin` | Creates the `admin` user if absent, or resets its password. Requires `ADMIN_PASSWORD` in the environment — no interactive prompt (use `./start.sh --reset-admin` for that). |
| `osint-tracker-init-db` | Creates database tables without touching credentials. |
| `osint-tracker-gen-fernet-key` | Prints a fresh Fernet key, for `API_KEYS_FERNET_KEY`. |
| `osint-tracker-update-tac-db` | Forces an immediate refresh of the offline IMEI/TAC database, bypassing the scheduler's normal once-a-day rate limit. |
| `osint-tracker-check-scrapers` | Runs canary health checks against the app's web-scraping-based data sources (AHMIA, Sherlock's site list, Company Registry's Canada scraper) and exits non-zero if any fail — useful in a cron job or CI. |

**Calling `osint-tracker` directly (without `start.sh`) skips three things
it normally handles for you:**
- No persisted `SECRET_KEY` — a random one is generated every start, which
  invalidates all sessions (and logs everyone out) on restart.
- No `API_KEYS_FERNET_KEY` — saving an API key in Settings fails until one
  is set.
- No admin account — `osint-tracker` only creates database tables; it
  never creates the `admin` user.

A one-off manual launch that avoids all three:
```bash
export SECRET_KEY='...'
export API_KEYS_FERNET_KEY="$(osint-tracker-gen-fernet-key)"
ADMIN_PASSWORD='choose-a-strong-password' osint-tracker-reset-admin
osint-tracker
```

Prefer `./start.sh` for anything beyond a quick smoke test — it does all
of the above for you, persists the secrets between restarts, and prompts
for the admin password interactively instead of requiring it in
plaintext in your shell history.

---

## Environment Variables

| Variable | Required? | Default | Description |
|---|---|---|---|
| `ADMIN_PASSWORD` | No | — | Admin password (min 8 chars). Only needed for non-interactive/scripted setups — `start.sh` (or `reset_admin.py` run directly) prompts for it (hidden input) if unset. |
| `SECRET_KEY` | No | generated once, persisted | Flask session/CSRF signing key. `start.sh` generates and saves this to `secrets.env` on first run so it stays stable — set your own to pin a specific value. |
| `API_KEYS_FERNET_KEY` | No | generated once, persisted | Fernet key used to encrypt stored API keys at rest. Same auto-generate-and-persist behavior as `SECRET_KEY`. Saving an API key in Settings fails until this is set (via start.sh or manually). |
| `DB_URL` | No | `sqlite:///./dev.db` | SQLAlchemy database URL |
| `REGISTRATION_ENABLED` | No | `False` | Set to `true` to allow public self-registration (rate-limited). Off by default. |
| `RETENTION_DAYS` | No | `90` | Investigations older than this are purged by the daily job. Set `0` to disable. |
| `CACHE_MAX_SIZE` | No | `1000` | Max entries in the in-memory service cache (LRU eviction). |
| `FLASK_DEV` | No | `0` | `1` runs the dev server instead of gunicorn (via `start.sh`). |
| `FLASK_DEBUG` | No | `0` | `1` enables debug mode (dev only — never in production). |
| `GUNICORN_WORKERS` | No | `1` | Number of gunicorn worker processes. Keep at `1` for the default SQLite database (only one writer at a time) — raise it only if `DB_URL` points at a real multi-connection database. |
| `GUNICORN_TIMEOUT` | No | `120` | Seconds before gunicorn kills and restarts a worker stuck on one request. Raised above gunicorn's own 30s default because some scans legitimately take longer (e.g. Social Search checks up to 273 sites) — too low a value drops the connection mid-scan with an empty response instead of a proper error. |
| `TAC_DB_AUTO_UPDATE` | No | `true` | Set to `false` to disable the background weekly refresh of the offline IMEI/TAC database (e.g. on limited mobile data). |
| `OSINT_TRACKER_DATA_DIR` | No | `~/.local/share/osint-tracker` | Where the refreshed offline TAC database is written. The read-only bundled snapshot is never touched. |

Generate a Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> **`.env` is not auto-loaded.** These variables must be present in the
> environment (there is no `python-dotenv` integration yet). Export them in your
> shell, your process manager (systemd/Docker), or a file you `source`. Generate
> `SECRET_KEY` and `API_KEYS_FERNET_KEY` **once** and keep them stable —
> rotating `SECRET_KEY` logs everyone out, and rotating `API_KEYS_FERNET_KEY`
> makes previously-stored API keys undecryptable.

Example: keep stable keys in a sourced file (do not commit it):

```bash
cat > secrets.env <<'EOF'
export SECRET_KEY="<paste a fixed random 64-hex value>"
export API_KEYS_FERNET_KEY="<paste a fixed generated Fernet key>"
EOF

source secrets.env
ADMIN_PASSWORD='choose-a-strong-password' ./start.sh
```

---

## API Services Configuration

Navigate to **Settings → API Settings** to configure external services. No restart required.

| Service key | Provider | Required for |
|---|---|---|
| `IPInfo` | ipinfo.io | IP geolocation enrichment |
| `Shodan` | shodan.io | Port scan / open service discovery |
| `VirusTotal` | virustotal.com | IP threat intelligence |
| `HIBP` | haveibeenpwned.com | Email breach detection — optional paid key for richer detail; free via XposedOrNot when left unconfigured |
| `Hunter.io` | hunter.io | Email deliverability verification |
| `NumVerify` | numverify.com | Phone number validation |
| `IMEIService` | dash.imei.info | IMEI device lookup — optional; brand/model works free offline without it (base URL: `https://dash.imei.info/api`) |
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
│   │   ├── company_client.py    # EDGAR + Companies House + CAC + Canada + Cyprus + SG/EE/IE/BR/AU/NZ
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

1. Set a strong, **fixed** `SECRET_KEY` in production (never rely on the random per-start fallback)
2. Set `API_KEYS_FERNET_KEY` so stored API keys are encrypted at rest
3. Choose a strong `ADMIN_PASSWORD` (min 8 chars) at setup; there is no default password
4. Keep `REGISTRATION_ENABLED=False` unless you intend to allow public sign-ups
5. Use HTTPS in production (reverse proxy via nginx or Caddy)
6. Never commit `.env`, `secrets.env`, or API key files to source control
7. Rotate API keys (and `API_KEYS_FERNET_KEY`) if they may have been exposed

---

## Troubleshooting

**Port 3000 already in use**
```bash
lsof -ti:3000 | xargs kill -9
```

<a id="resetting-the-admin-password"></a>
**"Invalid username or password" / forgot the admin password**

The username is always `admin`. Reset its password (works whether or not the
database already exists):
```bash
./start.sh --reset-admin
# prompts for the new password (hidden input, confirmed twice)
# non-interactive form: ADMIN_PASSWORD='new-strong-password' ./start.sh --reset-admin
```
A successful reset prints `✅ Admin account reset successfully / Username: admin`.
Note that `./start.sh` (without `--reset-admin`) only creates the admin when
`dev.db` does **not** already exist, so on an existing database you must use
`--reset-admin`. Also confirm the password is exactly what you typed (no
surrounding quotes or trailing spaces).

**Getting logged out after every restart**

This shouldn't happen anymore if you're using `start.sh` — it generates
`SECRET_KEY` once and persists it to `secrets.env`. If you're managing
`SECRET_KEY` yourself (e.g. running `python run.py` directly without
`start.sh`), make sure it's a fixed value, not regenerated per run.

**Database reset (wipes all data)**
```bash
rm dev.db
./start.sh   # prompts for a new admin password (hidden input) since dev.db is gone
```

**IMEI lookup only shows brand/model, no blacklist/stolen status**
- Brand/model comes from a bundled offline TAC database and always works free, with no key and no account balance.
- Blacklist, stolen, and warranty status require a paid IMEIService key (dash.imei.info) in Settings — once its credits run out, IMEI Lookup automatically falls back to the free offline data instead of failing outright.

**Keeping the offline TAC database up to date**
- It self-updates in the background: once shortly after each app start (skipped if already refreshed within the last day) and weekly thereafter for long-running processes, via the same APScheduler job as the watchlist rescan.
- The refreshed copy is written to `~/.local/share/osint-tracker/tac_database.csv.gz` (override with `OSINT_TRACKER_DATA_DIR`), leaving the read-only bundled snapshot untouched — a failed or skipped refresh always falls back to the last good copy, never to nothing.
- Set `TAC_DB_AUTO_UPDATE=false` to disable it entirely (e.g. on limited mobile data / Termux).
- Force an immediate refresh any time with `osint-tracker-update-tac-db`.

**Scraper canary checks**
- The app's web-scraping-based data sources (AHMIA dark web search, Sherlock's site list, Company Registry's Canada scraper) depend on third-party markup staying stable, and have broken silently before (e.g. the AHMIA anti-bot token issue). A daily background job runs a real, known-good query against each and sends a Notifications webhook alert if one returns nothing — a strong signal the site changed and the scraper needs updating.
- A weekly [GitHub Actions workflow](.github/workflows/scraper-canary.yml) runs the same checks and opens (or updates) a tracking issue on failure.
- Run it manually any time with `osint-tracker-check-scrapers` — exits non-zero if any check fails, so it's usable in your own cron job too.

**Scheduler fails to start: `No time zone found with key ...`**

Common on Termux/minimal systems that lack the IANA timezone database. Install
the fallback data:
```bash
pip install tzdata
```
The scheduler failure is non-fatal (the app keeps running), but the watchlist
auto-rescan and the data-retention purge job will not run until it is fixed.

**Watchlist auto-rescan not running**
```bash
pip install APScheduler>=3.10.0
```
The scheduler starts automatically when the app starts. Logs appear as `APScheduler started — watchlist rescan every 6h, retention purge daily`.

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
