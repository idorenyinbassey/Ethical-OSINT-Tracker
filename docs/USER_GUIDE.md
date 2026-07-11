# User Guide

Complete guide to using Ethical OSINT Tracker.

## Contents

1. [Getting Started](#getting-started)
2. [Investigation Tools](#investigation-tools)
3. [Link Tracker (IP Grabber)](#link-tracker-ip-grabber)
4. [Case Management](#case-management)
5. [Watchlist](#watchlist)
6. [Report Generation & Exports](#report-generation--exports)
7. [Global Search](#global-search)
8. [Audit Log](#audit-log)
9. [Admin Panel](#admin-panel)
10. [Account Settings & Change Password](#account-settings--change-password)
11. [API Settings](#api-settings)
12. [Best Practices](#best-practices)
13. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First Login

1. Start the app (see the installation guide for environment setup):
   `FLASK_DEV=1 python run.py`, or `ADMIN_PASSWORD='...' ./start.sh` for gunicorn.
2. Open [http://localhost:3000](http://localhost:3000)
3. Log in with:
   - **Username**: `admin` (fixed)
   - **Password**: the `ADMIN_PASSWORD` you set when initialising the database
4. You can change it any time via **Settings → Change Password**, or reset it from
   the CLI: `ADMIN_PASSWORD='new-password' python reset_admin.py`.

### Navigation

The sidebar gives access to all sections:

| Section | Pages |
|---------|-------|
| **Dashboard** | Overview, recent history, stats |
| **Investigate** | All 17+ core tools + plugin investigations |
| **Cases** | Case list, new case, case detail |
| **Link Tracker** | IP grabber / tracking link management |
| **Search** | Global full-text search bar (top of every page) |
| **Audit Log** | Activity log for all users |
| **Admin — Users** | User management (admin only) |
| **Settings** | API keys, change password |

---

## Investigation Tools

Each tool requires an **active case** to be selected before running. Choose a case from the header dropdown, then run any investigation — results are automatically saved to that case.

### IP Lookup (`/investigate/ip`)

Combines multiple data sources for a complete IP profile:

- **ip-api.com** — city, country, ASN, organisation, coordinates (free, no key required)
- **IPInfo.io** — additional geolocation enrichment (configure in Settings)
- **VirusTotal** — malicious/suspicious engine counts, threat categories, community score
- **Shodan** — open ports, detected services, CVE vulnerabilities

### Domain WHOIS (`/investigate/domain`)

Public RDAP protocol — no API key required. Returns registrar, status, nameservers, registration date, expiry date.

### Subdomain Scanner (`/investigate/subdomain`)

Discovers subdomains using two techniques — no API key required:

1. **Certificate Transparency logs** — queries crt.sh for every certificate issued for the domain
2. **DNS wordlist bruteforce** — resolves 75 common prefixes (`www`, `mail`, `api`, `staging`, `vpn`, …) plus any names from crt.sh

### Email Analysis (`/investigate/email`)

- **Have I Been Pwned** — lists breaches the address appeared in
- **Hunter.io** — deliverability, disposable flag, webmail flag, score

### Breach & Password Check (`/investigate/breach`)

Standalone breach checker with two inputs:

- **Email address** — queries HIBP for all known data breaches
- **Password (optional)** — k-anonymity check via pwnedpasswords.com; only the first 5 characters of the SHA-1 hash are sent — the full password never leaves your server

### Email Header Analyser (`/investigate/email-header`)

Parses a block of raw email headers to trace routing and flag SPF/DKIM/DMARC results — no API key required.

**How to get raw headers:**
- **Gmail** — three-dot menu → *Show original*
- **Outlook (web)** — three-dot menu → *View* → *View message source*
- **Apple Mail** — *View* → *Message* → *Raw Source*

### Social Search (`/investigate/social`)

Username enumeration across **273+ platforms** simultaneously — no API key required. Each platform is checked concurrently (12 threads). Results show Found / Not Found with direct profile URLs.

Platforms include: Twitter/X, GitHub, Instagram, Reddit, LinkedIn, TikTok, Telegram, Twitch, Discord, Steam, Medium, Dev.to, HackerNews, Substack, Nairaland, Jobberman, Bluesky, Threads, HackerOne, TryHackMe, and many more.

### Person Search (`/investigate/person`)

- Generates 12 curated Google dork / public records links (LinkedIn, news, court records, Nairaland, SEC EDGAR, Google Scholar)
- Produces up to 8 likely usernames from the name input to run through Social Search

### Company Registry (`/investigate/company`)

Searches 5 jurisdictions in parallel — no keys required except for UK Companies House:

| Jurisdiction | Source |
|---|---|
| United States | SEC EDGAR |
| United Kingdom | Companies House (optional key) |
| Nigeria | CAC portal |
| Canada | Corporations Canada |
| Cyprus | DRCOR (manual link) |

### Phone Lookup (`/investigate/phone`)

Uses NumVerify to return carrier, line type, country, and location. Requires a NumVerify API key in Settings.

### MAC Vendor Lookup (`/investigate/mac`)

Identifies the manufacturer from the OUI prefix — no key required. Accepted formats: `AA:BB:CC:DD:EE:FF`, `AA-BB-CC-DD-EE-FF`, `AABBCCDDEEFF`, or just the first three octets.

### File & Document Forensics (`/investigate/file`)

Upload a file (max 16 MB) to extract metadata — no key required for metadata extraction.

| File type | Metadata extracted |
|---|---|
| Image (JPG, PNG, TIFF, WEBP, …) | EXIF fields, GPS coordinates, camera model, software |
| Audio (MP3, FLAC, OGG, M4A) | ID3 / Vorbis tags: title, artist, album, year |
| Video (MP4, MKV, AVI, MOV) | Duration, resolution, frame rate, encoder, creation date |
| PDF | Title, author, creator, page count, creation date |
| DOCX | Author, last modified by, revision count, dates |
| XLSX | Author, last modified by, dates |

Also extracts: MD5 + SHA-256 file hash, MIME type, filesystem timestamps (created / modified / accessed). GPS coordinates auto-appear on the Location Map.

Optional: configure **ImageRecognition** (Google Cloud Vision) for face detection, labels, OCR, and safe-search.

### Vehicle / VIN (`/investigate/vehicle`)

Decodes a VIN using the NHTSA vPIC public API — no key required. Returns make, model, year, body class, engine, fuel type, drive type, transmission, plant country.

### Crypto / Blockchain Lookup (`/investigate/crypto`)

| Network | Source | What is returned |
|---|---|---|
| Bitcoin (BTC) | blockchain.info | Balance, total received/sent, transaction count, last 10 transactions |
| Ethereum (ETH) | blockcypher.com | Balance, total received/sent, transaction count, last 10 transactions |

### IMEI Lookup (`/investigate/imei`)

Queries dash.imei.info for device identification. Requires the **IMEIService** key and base URL `https://dash.imei.info/api` configured in Settings. The imei.info API requires a funded account balance.

### Dark Web Monitor (`/investigate/darkweb`)

Searches Ahmia.fi (indexed dark web search) — no Tor or API key required.

### Location Map (`/investigate/map`)

OpenStreetMap / Leaflet.js map that auto-plots GPS coordinates gathered from all IP lookups and image EXIF data in your active case. Blue markers = IP geolocation, green markers = image GPS.

### Network Graph (`/investigate/graph`)

vis.js graph showing relationships between all cases and investigations. Purple star-shaped hub nodes appear where the same IP, email, domain, or username appears in multiple cases. Subdomain scan results expand as child nodes from the domain.

### Plugin Investigations (`/investigate/plugins`)

Run modular investigation plugins without modifying core route code.

- Open **Investigate → Plugins** to view available plugins
- Select a plugin and provide a query value
- Choose a case and run; results are saved to the case like other tools

Built-in plugins include:
- DNS plugin
- WHOIS plugin
- Hash plugin

---

## Link Tracker (IP Grabber)

The Link Tracker generates unique URLs and email pixels to silently collect intelligence on whoever visits them. All collection is passive and server-side — no malware is installed on the visitor's device.

### Creating a Tracking Link

1. Go to **Link Tracker → New Link** in the sidebar
2. Fill in:
   - **Label** — a name for this link (your reference only)
   - **Link to case** — the case to record hits under
   - **Decoy mode** — what the visitor sees after their info is captured:
     - *404 Not Found* — looks like a broken link
     - *Blank page* — empty white screen
     - *Redirect* — forward to any URL you specify
   - **Notes** — optional investigation context
3. Click **Create Link**

### What Is Captured Per Hit

| Data point | How it is captured |
|---|---|
| IP address | Server-side from the HTTP request |
| Country, city, ISP | ip-api.com geolocation (server-side) |
| Browser / platform | User-Agent header (server-side) |
| Screen resolution | JavaScript `screen.width × screen.height` |
| Timezone | JavaScript `Intl.DateTimeFormat().resolvedOptions().timeZone` |
| Language | `navigator.language` |
| Plugin list | `navigator.plugins` enumeration |
| GPS coordinates | `navigator.geolocation.getCurrentPosition()` — browser shows its own permission dialog; stored only if the user grants it |

### Email Tracking Pixel

On the link detail page, copy the `<img>` tag:

```html
<img src="https://your-host/t/TOKEN/px.gif" width="1" height="1" style="display:none">
```

Paste it into any HTML email. When the recipient opens the email, the pixel fires — recording their IP, ISP, geolocation, and timestamp.

### Live Hit Feed

The detail page polls for new hits every 3 seconds using JavaScript. New hits slide in at the top with a highlight ring without reloading the page. When additional fingerprint/GPS data arrives on a known hit, the existing card updates in-place.

---

## Case Management

### Creating a Case

1. Click **+ New Case** from the Cases page
2. Enter title, optional description, and priority (Low / Medium / High / Critical)
3. Click **Create Case**

### Case Statuses

| Status | Meaning |
|--------|---------|
| Open | Active investigation |
| In Progress | Being worked on |
| Closed | Resolved |

### Threat Scoring

Each case is automatically assigned a threat score (0–100) based on linked investigation confidence levels, dark web hits, and HIBP breach counts. The badge on the case list is colour-coded:

| Score | Badge |
|-------|-------|
| 0–30 | Green (Low) |
| 31–60 | Yellow (Medium) |
| 61–80 | Orange (High) |
| 81–100 | Red (Critical) |

### Evidence Tagging

On the case detail page, tag any investigation result as:
- `key_evidence` — primary indicator
- `corroborated` — confirmed by a second source
- `follow_up` — needs further investigation
- `disputed` — reliability in question

### Investigator Journal

The Investigator Journal provides structured notes on a case (distinct from informal team comments). Each note has a kind:
- `observation` — a factual finding
- `lead` — a thread to investigate
- `key_evidence` — a significant finding
- `follow_up` — a pending action

### Auto Case Correlation

A "Related Cases" panel on the case detail page lists other cases that share investigation targets (same IP, domain, username, email, crypto address, etc.) — surfaced automatically without any manual linking.

### Bulk CSV Import

Upload a CSV file from the case detail page to batch-run investigation targets. The CSV must have a column named `target` and optionally a `kind` column (defaults to `ip`).

### Team Comments

Add informal observations to any case using the **Add Comment** form at the bottom of the case detail page.

---

## Watchlist

The Watchlist lets you monitor IPs, domains, emails, social handles, or crypto addresses for changes.

### Adding a Target

From the Watchlist section, enter:
- **Target** — the value to monitor (e.g. `192.0.2.1`, `example.com`)
- **Kind** — ip, domain, email, username, or crypto

### Auto-Rescan

The APScheduler background job rescans all watchlist targets every 6 hours. If a new investigation result differs from the previous one (hash comparison), the target gets an **alert badge** in the UI and a new investigation record is created automatically.

> APScheduler must be installed (`pip install APScheduler>=3.10.0`). The scheduler starts with the app; a log line confirms: `APScheduler started — watchlist rescan every 6h`.

### Alert Badges

Targets with changed results show a red alert badge. Click the target to review the new investigation result.

---

## Report Generation & Exports

From any case detail page, click **Export** to open the format selector.

### Formats

| Format | Best for |
|--------|---------|
| PDF | Professional printed reports |
| DOCX | Editable Microsoft Word |
| HTML | Shareable web page |
| CSV | Spreadsheet / data analysis |
| XLSX | Excel workbook |

### Async Generation

Large cases with many investigations are generated in a background thread. A progress bar appears while generation is running. When complete, a **Download** button appears. The file is cleaned up automatically after download.

### Report Content

All formats include: case metadata, threat score, all linked investigations, evidence tags, investigator journal entries, team comments, timestamps, and a SHA-256 integrity fingerprint.

### STIX 2.1 Export

Click **STIX 2.1 Export** on the case detail page to download a full STIX bundle (`stix_case_<id>.json`). The bundle includes:

- **Report** object with case metadata
- Observable objects: `ipv4-addr`, `domain-name`, `email-addr`, `user-account`, `url`, `file`, and custom types for phone numbers, crypto wallets, and IMEI devices
- **Indicator** objects for each observable
- **Relationship** objects linking indicators to the report

Compatible with MISP, OpenCTI, TheHive, and any STIX 2.1-aware platform.

---

## Global Search

The search bar at the top of every page queries all content simultaneously:

- **Investigation queries and results** — e.g. search `8.8.8.8` to find all IP lookups for that address
- **Case titles and descriptions**
- **Case notes** (journal entries and team comments)

Results are grouped by type. Click any result to navigate directly to the investigation or case.

---

## Audit Log

The Audit Log at `/audit` records every significant action across all users:

| Event | What is recorded |
|-------|------------------|
| Login | Username, IP, timestamp |
| Case create / delete | Case ID, username, IP |
| Investigation run | Kind, query, case ID |
| Report export | Format, case ID |
| STIX export | Case ID |
| Admin actions | Target user, action type |
| Password change | Username |
| Watchlist alert | Target, new result hash |

**Filter by action type** using the dropdown at the top of the page (e.g. show only `case.create` events).

---

## Admin Panel

Available at `/admin/users` — visible only to users with admin status.

### User Cards

Each user card shows: username, admin badge, disabled badge, join date, and action buttons.

### Actions

| Action | Description |
|--------|-------------|
| **Make Admin / Revoke Admin** | Grants or removes admin flag |
| **Disable / Enable** | Blocks login without deleting the account |
| **Delete** | Permanently removes the user (confirmation required) |
| **Reset Password** | Expand the arrow to set a new password (min. 6 chars, must match confirmation) |

All actions are recorded in the Audit Log. Admins cannot modify their own admin status, disable, or delete their own account from this panel.

---

## Account Settings & Change Password

Go to **Settings** in the sidebar.

### Change Password

1. Scroll to the **Change Password** section
2. Enter your **current password**
3. Enter and confirm the **new password** (min. 6 characters)
4. Click **Change Password**

The change is recorded in the Audit Log. Admins can also reset any user's password from the Admin Panel.

---

## API Settings

Navigate to **Settings → API Settings**. Keys are stored encrypted in the database and read at request time — no restart required.

| Service | Used by | Required? |
|---------|---------|-----------|
| `IPInfo` | IP Lookup — enrichment | Optional |
| `Shodan` | IP Lookup — port scan | Optional |
| `VirusTotal` | IP Lookup — threat intel | Optional |
| `HIBP` | Email Analysis, Breach Check | Optional |
| `Hunter.io` | Email Analysis | Optional |
| `NumVerify` | Phone Lookup | Yes |
| `IMEIService` | IMEI Lookup (URL: `https://dash.imei.info/api`) | Yes |
| `ImageRecognition` | File Forensics — Google Cloud Vision | Optional |
| `TorProxy` | Route all HTTP through Tor / a proxy | Optional |

### Configuring a Service

1. Find the service card in Settings
2. Enter your **API Key**
3. Confirm or update the **Base URL** (pre-filled)
4. Toggle **Enabled** on
5. Click **Save**

### Tor / Proxy Routing

Set TorProxy key to the proxy URL:
- Tor: `socks5://127.0.0.1:9050`
- HTTP proxy: `http://proxy.example.com:8080`

When enabled, all outbound HTTP requests route through the proxy. Disable it when speed matters more than anonymity.

---

## Best Practices

### Ethical Guidelines

Only use this tool for investigations you are explicitly authorised to conduct. Never use it for stalking, harassment, doxxing, or unauthorised surveillance.

### Recommended Workflow

1. **Create a Case** — document the objective and priority
2. **Set it as active** — select it in the header dropdown
3. **Run the relevant tools** — all results auto-save to the case
4. **Tag evidence** — mark key findings and disputed results
5. **Add journal entries** — record observations and leads as you discover them
6. **Correlate** — check the Related Cases panel for shared entities
7. **Export** — generate a PDF or STIX bundle for handoff
8. **Close the case** — change status to Closed when complete

### Security

- Use a strong `ADMIN_PASSWORD` (there is no default password) and rotate it if exposed
- Never commit API keys, `secrets.env`, or `.env` files to source control
- Use HTTPS (see [Deployment Guide](./DEPLOYMENT.md)) for any network-accessible deployment
- Rotate API keys if they may have been exposed

---

## Troubleshooting

**No results / empty response**
Check that the relevant API key is configured and enabled in Settings. Most tools show a yellow notice with a Settings link if the service is missing.

**Watchlist not auto-rescanning**
```bash
pip install APScheduler>=3.10.0
```
Restart the app. The scheduler logs `APScheduler started — watchlist rescan every 6h` on startup.

**Slow responses**
Results are cached 1–6 hours per query, so repeated lookups are instant. Tor routing adds 5–30 seconds per request. Disable TorProxy if speed matters.

**File upload fails**
Max 16 MB. Supported: JPG, PNG, GIF, BMP, TIFF, WEBP, MP3, FLAC, OGG, M4A, WAV, MP4, MKV, AVI, MOV, WMV, PDF, DOCX, XLSX.

**IMEI lookup fails**
Verify base URL in Settings is `https://dash.imei.info/api`. The API requires a funded account balance on dash.imei.info.

**Report generation stuck**
Reload the page — if the job ID is gone, the server restarted and lost the in-memory job. Re-generate.

**Database reset**
```bash
rm dev.db
python reset_admin.py
```
