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
| **Investigate** | IP Lookup, Domain WHOIS, Subdomain Scanner, Email Analysis, Email Header Analyser, Social Search, Phone Lookup, MAC Vendor Lookup, File & Document Forensics, Crypto Lookup, IMEI Lookup |
| **Manage** | Cases, API Settings |

---

## Investigation Tools

Each tool page has a form on the left and results on the right. Results are automatically saved to the database and can optionally be linked to a Case.

### IP Lookup (`/investigate/ip`)

Combines multiple data sources for a complete IP profile:

- **ip-api.com** — city, country, ASN, organisation, coordinates (free, no API key required)
- **IPInfo.io** — additional geolocation enrichment (optional, configure in Settings)
- **VirusTotal** — malicious/suspicious/harmless engine counts, threat categories, community score
- **Shodan** — open ports, detected services, CVE vulnerabilities

Enter an IP address (e.g. `8.8.8.8`) and click **Run Lookup**.

> ip-api.com is the free default geolocation source — no key needed. VirusTotal and Shodan fall back to deterministic mock data when no API key is configured.

### Domain WHOIS (`/investigate/domain`)

Uses the public [RDAP](https://rdap.org/) protocol — no API key required.

Returns: registrar, status, nameservers, registration date, expiry date.

### Subdomain Scanner (`/investigate/subdomain`)

Discovers subdomains of a target domain using two complementary techniques — no API key required:

1. **Certificate Transparency logs** — queries [crt.sh](https://crt.sh/) for all certificates issued for the domain; extracts every subject alternative name (SAN) listed
2. **DNS wordlist bruteforce** — attempts to resolve 75 common subdomain prefixes (e.g. `www`, `mail`, `api`, `staging`, `vpn`) plus any entries discovered from crt.sh, using socket DNS resolution

Results show each discovered subdomain alongside its resolved IP address (if resolvable).

> Install `dnspython` for richer DNS record enumeration. The tool falls back to Python's built-in `socket` module if dnspython is not present.

### Email Analysis (`/investigate/email`)

- **Have I Been Pwned** — lists data breaches the address appeared in, with breach date and exposed data classes
- **Hunter.io** — deliverability, disposable flag, webmail flag, score

Configure API keys for both services in **Settings** for live data.

### Email Header Analyser (`/investigate/email-header`)

Parses a block of raw email headers to trace message routing and flag authentication results — no API key required.

**How to get raw headers:**
- **Gmail** — open the message, click the three-dot menu, choose *Show original*
- **Outlook (web)** — open the message, click the three-dot menu, choose *View* > *View message source*
- **Apple Mail** — open the message, go to *View* > *Message* > *Raw Source*

Paste the full header block into the text area and click **Analyse**.

**What the results show:**

| Field | Meaning |
|---|---|
| **Received chain** | Each mail server hop the message passed through, in reverse chronological order |
| **Originating IP** | The first external IP address in the Received chain — typically the sending mail server |
| **SPF** | Whether the sending server is authorised by the domain's SPF record (Pass / Fail / SoftFail / None) |
| **DKIM** | Whether the message body and headers were cryptographically signed and the signature is valid |
| **DMARC** | Whether the message passed the domain's DMARC policy (alignment of SPF/DKIM with the From domain) |
| **Relay hops** | Count of intermediate servers the message traversed |

> A Fail or missing SPF/DKIM/DMARC result does not by itself confirm a spoofed or malicious email, but it warrants further investigation.

### Social Search (`/investigate/social`)

Sherlock/Maigret-style username enumeration across **36 platforms** simultaneously — no API key required.

Platforms checked include: Twitter/X, GitHub, Instagram, Reddit, LinkedIn, Pinterest, TikTok, Telegram, Facebook, YouTube, Twitch, Discord, Snapchat, Medium, Dev.to, Keybase, GitLab, Bitbucket, Steam, Patreon, Spotify, SoundCloud, Flickr, Vimeo, Behance, Dribbble, Fiverr, HackerNews, ProductHunt, Quora, Substack, Mastodon, Tumblr, WordPress, and Gravatar.

Each platform is checked concurrently using `ThreadPoolExecutor(12)`. The check analyses:
- HTTP response status code
- Page content (presence of username-specific markers)
- Redirect URL detection (profiles that redirect to a generic 404 page)

Results show a table of **Found** / **Not Found** with direct profile URLs for found accounts.

> Previously, Social Search required GitHub and Twitter API keys for reliable results. The new approach uses public HTTP response analysis and requires no API configuration.

### Phone Lookup (`/investigate/phone`)

Uses **NumVerify** to validate a phone number and return carrier, line type, country, and location. Returns an error if the NumVerify API key is not configured in Settings.

### MAC Vendor Lookup (`/investigate/mac`)

Identifies the manufacturer of a network interface from its MAC address OUI (first three octets) — no API key required.

**Accepted formats** (all equivalent):
- `AA:BB:CC:DD:EE:FF`
- `AA-BB-CC-DD-EE-FF`
- `AABBCCDDEEFF`
- First three octets only: `AA:BB:CC`

The lookup queries [macvendors.com](https://macvendors.com/), which maintains a database of IEEE OUI assignments. Results include the registered vendor/manufacturer name and organisation.

> MAC addresses can be randomised by modern operating systems. A result reflects the OUI registrant, not necessarily the physical device owner.

### File & Document Forensics (`/investigate/file`)

Upload a file to extract embedded metadata — no API key required for metadata extraction. Google Cloud Vision AI is optional for image content analysis.

The old `/investigate/image` URL redirects here automatically.

**Supported file types and extracted metadata:**

| File type | Extensions | What is extracted |
|---|---|---|
| Image | JPG, PNG, GIF, BMP, TIFF, WEBP | EXIF fields (camera model, lens, date taken, software), GPS coordinates (latitude/longitude/altitude), image dimensions |
| Audio | MP3, FLAC, OGG, M4A, WAV | ID3 / Vorbis tags: title, artist, album, year, track number, comment, embedded artwork flag |
| Video | MP4, MKV, AVI, MOV, WMV | Container metadata: duration, resolution, frame rate, encoder, creation date |
| PDF | PDF | Title, author, creator application, producer, creation date, modification date, page count |
| Word document | DOCX | Core properties: title, subject, author, last modified by, revision count, creation and modification dates |
| Spreadsheet | XLSX | Workbook properties: title, subject, author, last modified by, creation and modification dates |

**Maximum upload size**: 16 MB.

For images, optionally enable **Google Cloud Vision AI** (configure **ImageRecognition** in Settings) to add face detection, label detection, OCR, web entity detection, and safe-search classification.

### Crypto / Blockchain Lookup (`/investigate/crypto`)

Look up the balance and recent transaction history for a cryptocurrency address — no API key required.

**Supported networks:**

| Network | Data source | What is returned |
|---|---|---|
| Bitcoin (BTC) | blockchain.info | Address balance (BTC and USD equivalent), total received, total sent, transaction count, last 10 transactions |
| Ethereum (ETH) | blockcypher.com | Address balance (ETH and USD equivalent), total received, total sent, transaction count, last 10 transactions |

Enter the wallet address and select the network, then click **Look Up**.

> This tool queries public blockchain data only. It cannot identify the real-world owner of an address. Always comply with relevant financial regulations when investigating cryptocurrency activity.

### IMEI Lookup (`/investigate/imei`)

Queries a configurable IMEI service (e.g. imei.info). Returns device details if the **IMEIService** is configured in Settings. Shows an error with a link to Settings if not configured.

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
| IPInfo | IP Lookup — optional geolocation enrichment (ip-api.com is the free default) |
| Shodan | IP Lookup — port scan |
| VirusTotal | IP Lookup — threat intel |
| HIBP | Email Analysis — breach check |
| Hunter.io | Email Analysis — deliverability |
| NumVerify | Phone Lookup |
| ImageRecognition | File & Document Forensics — Google Cloud Vision AI (optional) |
| IMEIService | IMEI Lookup |
| TorProxy | Tor / proxy routing for all HTTP requests |

### How to Configure a Service

1. Go to **Settings** from the sidebar
2. Find the service card
3. Enter your **API Key**
4. Confirm or update the **Base URL** (pre-filled with the correct default)
5. Toggle **Enabled** on
6. Click **Save**

### Tor / Proxy Routing

To route all investigation HTTP requests through Tor or an HTTP proxy:

1. Go to **Settings** and find the **TorProxy** service card
2. Enter the proxy URL in the **API Key** / URL field:
   - Tor: `socks5://127.0.0.1:9050`
   - HTTP proxy: `http://proxy.example.com:8080`
3. Toggle **Enabled** on and click **Save**

When TorProxy is enabled, every outbound HTTP request made by the service layer is routed through the specified proxy. This requires the `httpx[socks]` package (included in `requirements.txt`) for SOCKS5 support.

> Running requests through Tor will significantly increase response times (typically 5–30 seconds per call). Disable TorProxy when speed is more important than anonymity.

### Without API Keys

- **IP Lookup** — ip-api.com provides geolocation with no key; VirusTotal and Shodan show mock data; IPInfo is skipped
- **Domain WHOIS** — always works (public RDAP, no key needed)
- **Subdomain Scanner** — always works (crt.sh + socket DNS, no key needed)
- **Email Analysis** — HIBP and Hunter.io show a configuration notice
- **Email Header Analyser** — always works (local parsing, no key needed)
- **Social Search** — always works (HTTP response analysis, no key needed)
- **MAC Vendor Lookup** — always works (macvendors.com, no key needed)
- **File & Document Forensics** — metadata extraction always works; Vision AI requires ImageRecognition key
- **Crypto Lookup** — always works (public blockchain APIs, no key needed)
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
External API calls take 1–10 seconds depending on the service. Results are cached for 1–6 hours per query, so repeated lookups are instant. Requests routed through Tor will be slower still (5–30 seconds).

**File upload fails**
Check the file type and size (max 16 MB). Supported types: JPG, PNG, GIF, BMP, TIFF, WEBP, MP3, FLAC, OGG, M4A, WAV, MP4, MKV, AVI, MOV, WMV, PDF, DOCX, XLSX.

**Database reset**
```bash
rm dev.db
python reset_admin.py
```
