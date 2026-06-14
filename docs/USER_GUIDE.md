# User Guide

Complete guide to using Ethical OSINT Tracker.

## Getting Started

### First Login

1. Start the app: `python run.py`
2. Open [http://localhost:3000](http://localhost:3000)
3. Log in with the demo credentials:
   - Username: `admin`
   - Password: `changeme`
4. **Change this password immediately** — go to Settings after your first login.

### Navigation

The sidebar on the left gives access to everything:

| Section | Pages |
|---------|-------|
| **Dashboard** | Overview, recent history, stats |
| **Investigate** | IP Lookup, Domain WHOIS, Email Analysis, Social Search, Phone Lookup, Image Forensics, IMEI Lookup |
| **Manage** | Cases, API Settings |

---

## Investigation Tools

Each tool page has a form on the left and results on the right. Results are automatically saved to the database and can optionally be linked to a Case.

### IP Lookup (`/investigate/ip`)

Combines three data sources for a complete IP profile:

- **IPInfo.io** — city, country, ASN, organisation, coordinates
- **VirusTotal** — malicious/suspicious/harmless engine counts, threat categories, community score
- **Shodan** — open ports, detected services, CVE vulnerabilities

Enter an IP address (e.g. `8.8.8.8`) and click **Run Lookup**.

> Shodan and VirusTotal fall back to deterministic mock data when no API key is configured — you will always see results.

### Domain WHOIS (`/investigate/domain`)

Uses the public [RDAP](https://rdap.org/) protocol — no API key required.

Returns: registrar, status, nameservers, registration date, expiry date.

### Email Analysis (`/investigate/email`)

- **Have I Been Pwned** — lists data breaches the address appeared in, with breach date and exposed data classes
- **Hunter.io** — deliverability, disposable flag, webmail flag, score

Configure API keys for both services in **Settings** for live data.

### Social Media Search (`/investigate/social`)

Checks for public profiles across 10 platforms simultaneously (Twitter, GitHub, Instagram, Reddit, LinkedIn, Pinterest, TikTok, Telegram, Facebook, YouTube).

Returns a table of found/not-found results with direct profile URLs.

Authenticated API calls for GitHub and Twitter can be enabled by adding keys to the **SocialSearch** service in Settings as JSON in the Notes field:
```json
{"github": "ghp_xxx", "twitter": "Bearer AAA..."}
```

### Phone Lookup (`/investigate/phone`)

Uses **NumVerify** to validate a phone number and return carrier, line type, country, and location. Returns an error if the NumVerify API key is not configured.

### Image Forensics (`/investigate/image`)

Upload an image file (JPG, PNG, GIF, BMP, TIFF, WEBP — up to 16 MB).

Two layers of analysis:

1. **EXIF extraction** (always runs, no API needed) — camera model, date taken, GPS coordinates, dimensions, software
2. **Google Cloud Vision AI** (optional) — face detection, label detection, OCR, web entity detection, safe-search

Configure the **ImageRecognition** service in Settings to enable Vision AI.

### IMEI Lookup (`/investigate/imei`)

Queries a configurable IMEI service (e.g. imei.info). Returns device details if the **IMEIService** is configured. Shows an error with a link to Settings if not configured.

---

## Case Management (`/cases`)

Cases let you group related investigations together.

### Creating a Case

1. Click **+ New Case** from the Cases page
2. Enter a title, optional description, and priority (Low / Medium / High / Critical)
3. Click **Create Case**

### Linking Investigations to a Case

On any investigation tool page, select a case from the **Link to Case** dropdown before running the lookup. The result will be stored against that case.

### Case Statuses

| Status | Meaning |
|--------|---------|
| Open | Active investigation |
| In Progress | Being worked on |
| Closed | Resolved |

### Editing and Deleting Cases

From the Cases list, click **Edit** to change title, description, status, or priority. Click **Delete** to permanently remove a case.

---

## API Settings (`/settings`)

Configure external OSINT service credentials. No restart is needed — keys are read from the database on every request.

### Available Services

| Service | Used by |
|---------|---------|
| IPInfo | IP Lookup — geolocation |
| Shodan | IP Lookup — port scan |
| VirusTotal | IP Lookup — threat intel |
| HIBP | Email Analysis — breach check |
| Hunter.io | Email Analysis — deliverability |
| NumVerify | Phone Lookup |
| SocialSearch | Social Search (GitHub/Twitter authenticated) |
| ImageRecognition | Image Forensics (Google Cloud Vision) |
| IMEIService | IMEI Lookup |

### How to Configure a Service

1. Go to **Settings** from the sidebar
2. Find the service card
3. Enter your **API Key**
4. Confirm or update the **Base URL** (pre-filled with the correct default)
5. Toggle **Enabled** on
6. Click **Save**

### Without API Keys

- **IP Lookup** — VirusTotal and Shodan show mock data; IPInfo returns nothing
- **Domain WHOIS** — always works (public RDAP, no key needed)
- **Email Analysis** — HIBP and Hunter.io show a configuration notice
- **Social Search** — falls back to HTTP HEAD checks (no auth, less reliable)
- **Phone / IMEI** — show a configuration notice

---

## Best Practices

### Ethical Guidelines

Only use this tool for:
- Investigations you are explicitly authorised to conduct
- Legitimate security research with proper scope
- Academic or educational purposes

Never use it for stalking, harassment, doxxing, or any unauthorized surveillance.

### Recommended Workflow

1. **Create a Case** — document the investigation objective
2. **Run the relevant tools** — link each result to the case
3. **Review results** — check the Dashboard for a history summary
4. **Archive** — close the case when complete

### Security

- Change the default `admin / changeme` password immediately
- Never commit API keys to source control
- Use HTTPS (see [Deployment Guide](./DEPLOYMENT.md)) for any non-local deployment
- Rotate API keys if they may have been exposed

---

## Troubleshooting

**No results / empty response**  
Check that the relevant API key is configured and enabled in Settings. Most tools show a yellow notice with a link to Settings if the service is not configured.

**Slow responses**  
External API calls take 1–10 seconds depending on the service. Results are cached for 1–6 hours per query, so repeated lookups are instant.

**Image upload fails**  
Check file type (JPG/PNG/GIF/BMP/TIFF/WEBP) and size (max 16 MB).

**Database reset**  
```bash
rm dev.db
python reset_admin.py
```
