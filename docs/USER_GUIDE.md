# User Guide

Complete guide to using Ethical OSINT Tracker for investigations.

## Table of Contents
- [Getting Started](#getting-started)
- [Dashboard](#dashboard)
- [Investigation Tools](#investigation-tools)
- [Case Management](#case-management)
- [Intelligence Reports](#intelligence-reports)
- [Team Collaboration](#team-collaboration)
- [Settings & Configuration](#settings--configuration)
- [Best Practices](#best-practices)

## Getting Started

### First Login

1. Navigate to http://localhost:3000
2. Click **Login** or use `/login` route
3. Enter default credentials:
   - Username: `admin`
   - Password: `changeme`
4. **Important**: Change password after first login

### Dashboard Overview

The dashboard provides:
- **Quick Statistics**: Active investigations, threat alerts, cases closed
- **Recent Activity**: Investigation history timeline
- **Threat Trends**: Visual analytics over time
- **Quick Actions**: One-click access to common tasks

## Investigation Tools

### Domain Intelligence

**Purpose**: Analyze domain ownership, history, and DNS records.

**Steps**:
1. Navigate to **Investigate** → **Domain** tab
2. Enter domain (e.g., `example.com`)
3. Click **Lookup Domain**
4. Review results:
   - Registrar information
   - Creation/expiration dates
   - Name servers
   - DNS record count
   - WHOIS status

**Use Cases**:
- Verify domain legitimacy
- Identify phishing domains
- Track domain ownership changes
- Investigate suspicious websites

### IP Geolocation

**Purpose**: Locate and profile IP addresses.

**Steps**:
1. Go to **Investigate** → **IP Address** tab
2. Enter IP address (e.g., `8.8.8.8`)
3. Click **Lookup IP**
4. Analyze:
   - Geographic location (city, country)
   - ISP and ASN information
   - Threat score (0-100)
   - Proxy/VPN detection

**Use Cases**:
- Identify attack sources
- Verify server locations
- Detect proxy usage
- Map network infrastructure

### Email Analysis

**Purpose**: Validate emails and check breach history.

**Steps**:
1. Select **Investigate** → **Email** tab
2. Enter email address
3. Click **Check Email**
4. Review:
   - Format validity
   - Disposable email detection
   - Breach count
   - Domain reputation
   - Last known breach date

**Use Cases**:
- Verify email authenticity
- Check account compromise
- Identify disposable emails
- Assess sender reputation

### Social Media OSINT

**Purpose**: Find social media profiles by username.

**Steps**:
1. Navigate to **Investigate** → **Social Media** tab
2. Enter username
3. Click **Search Profiles**
4. View discovered profiles:
   - Platform name
   - Account existence
   - Direct profile URLs

**Supported Platforms**:
- Twitter/X
- Instagram
- Facebook
- LinkedIn
- GitHub
- TikTok
- Reddit

**Use Cases**:
- Verify identity across platforms
- Track online presence
- Investigate fake accounts
- Link related accounts

### Phone Intelligence

**Purpose**: Validate and profile phone numbers.

**Steps**:
1. Go to **Investigate** → **Phone** tab
2. Enter phone number (international format: +1234567890)
3. Click **Lookup Phone**
4. Results include:
   - Validation status
   - Number type (mobile/landline)
   - Carrier information
   - Location and timezone
   - Fraud score and risk level

**Risk Levels**:
- 🟢 Low (0-30): Legitimate number
- 🟡 Medium (31-69): Moderate risk
- 🔴 High (70-100): High fraud risk

**Use Cases**:
- Verify caller identity
- Detect spoofed numbers
- Assess fraud risk
- Geographic profiling

### Image Forensics

**Purpose**: Extract metadata and identify persons in images.

**Steps**:
1. Select **Investigate** → **Image Analysis** tab
2. Upload image or provide URL
3. Click **Analyze Image**
4. Review findings:
   - Identified persons (mock recognition)
   - Associated email addresses
   - Social media profiles
   - Media mentions
   - EXIF metadata (camera, location, timestamp)

**Use Cases**:
- Reverse image search
- Identify photo subjects
- Extract geolocation data
- Verify image authenticity

### IMEI/Device Tracking

**Purpose**: Identify mobile devices and check blacklist status.

**Steps**:
1. Navigate to **Investigate** → **IMEI** tab
2. Enter 15-digit IMEI number
3. Click **Lookup IMEI**
4. Analyze:
   - Device validity
   - Brand and model
   - Specifications
   - Blacklist status
   - Theft records
   - Warranty status
   - Carrier lock
   - Risk assessment

**Use Cases**:
- Verify device legitimacy
- Check stolen device databases
- Identify counterfeit devices
- Track device origin

### Network Graph

**Purpose**: Visualize relationships between investigated entities.

**Access**: Available after performing investigations

**Features**:
- **Entity Cards**: Grouped by type (domain, IP, email, person, device)
- **Connection View**: Shows relationships and labels
- **Color Coding**:
  - 🔵 Blue: Domains
  - 🟢 Green: IP addresses
  - 🟣 Purple: Emails
  - 🟠 Orange: Persons
  - 🟣 Indigo: Phone numbers
  - 🔴 Red: Breaches

**Use Cases**:
- Map attack infrastructure
- Identify linked accounts
- Visualize investigation scope
- Generate relationship diagrams

## Case Management

### Creating Cases

1. Navigate to **Cases** page
2. Click **+ New Case**
3. Fill in details:
   - **Title**: Case identifier
   - **Description**: Overview and objectives
   - **Priority**: Low / Medium / High
4. Click **Create Case**

### Managing Cases

**Actions**:
- **Delete**: Remove case permanently
- **Export**: Download case data (JSON/CSV)
- **Status**: Toggle between Open/Closed

**Priority Indicators**:
- 🔴 High: Urgent investigations
- 🟡 Medium: Standard priority
- 🟢 Low: Routine checks

### Linking Investigations

Cases can be linked to:
- Intelligence reports
- Team collaborations
- Specific investigations (via export)

## Intelligence Reports

### Creating Reports

1. Go to **Reports** page
2. Click **+ New Report**
3. Configure:
   - **Title**: Report name
   - **Summary**: Executive summary
   - **Indicators**: Comma-separated IOCs
   - **Related Case**: Link to existing case (optional)
4. Click **Create Report**

### Auto-Enrichment

**Feature**: Automatically pull indicators from recent investigations.

1. Click **Enrich from Investigations**
2. System analyzes last 20 investigations
3. Extracts domains, IPs, emails
4. Fetches additional context via APIs:
   - Domain WHOIS (RDAP)
   - IP geolocation
   - Email breaches
5. Categorizes by threat level:
   - 🟢 Low
   - 🟡 Medium
   - 🔴 High

### Exporting Reports

1. Open desired report
2. Click **Export (JSON)** or **Export (CSV)**
3. Copy formatted data
4. Paste into documentation or SIEM

**JSON Format**:
```json
{
  "title": "Report Title",
  "summary": "Executive summary",
  "indicators": ["domain.com", "1.2.3.4"],
  "created_at": "2025-11-24T..."
}
```

**CSV Format**: Compatible with Excel and data analysis tools.

## Team Collaboration

### Creating Teams

1. Navigate to **Team** page
2. Click **+ Create Team**
3. Enter:
   - **Team Name**: Identifier
   - **Description**: Purpose and scope
4. Click **Create**

### Managing Members

**Add Member**:
1. Select team
2. Click **+ Add Member**
3. Choose user from dropdown
4. Assign role:
   - **Owner**: Full permissions
   - **Admin**: Manage team and members
   - **Member**: View and contribute
   - **Viewer**: Read-only access
5. Click **Add to Team**

**Remove Member**:
- Click trash icon next to member name

**Change Role**:
- Currently requires removing and re-adding (future update)

### Team Use Cases

- **SOC Teams**: Coordinate threat investigations
- **Research Groups**: Share OSINT findings
- **Training**: Supervisor-student collaboration
- **Multi-investigator Cases**: Distribute workload

## Settings & Configuration

### API Service Configuration

**Available Services**:

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| WhoisXML API | Domain WHOIS | 500/mo |
| Have I Been Pwned | Breach data | Limited |
| IPInfo.io | IP geolocation | 50k/mo |
| Shodan | Device search | 100/mo |
| VirusTotal | Threat intel | 4 req/min |
| Hunter.io | Email verification | 25/mo |
| NumVerify | Phone validation | 100/mo |

**Configuration Steps**:
1. Go to **Settings** page
2. Find desired service
3. Click **Configure**
4. Enter:
   - **API Key**: From service provider
   - **Base URL**: (pre-filled)
   - **Rate Limit**: Requests per hour
   - **Notes**: Internal documentation
   - **Enabled**: Toggle on
5. Click **Save**

**Getting API Keys**:
- Click **Docs** link next to each service
- Register for free tier
- Copy API key from dashboard
- Return to Settings and paste

### Data Mode

**Mock Mode** (Default):
- No API keys required
- Instant responses
- Deterministic results
- Perfect for demos and testing

**Live Mode** (With API Keys):
- Real-time external data
- Subject to rate limits
- Requires API configuration
- Caching enabled (1 hour TTL)

## Best Practices

### Ethical Guidelines

✅ **DO**:
- Obtain proper authorization
- Document investigation scope
- Respect privacy laws
- Use for lawful purposes
- Cite data sources
- Secure sensitive findings

❌ **DON'T**:
- Conduct unauthorized surveillance
- Harass or stalk individuals
- Violate platform ToS
- Collect data without consent
- Share confidential information
- Use for illegal activities

### Investigation Workflow

1. **Define Scope**: What are you investigating?
2. **Create Case**: Document objectives
3. **Gather Data**: Use appropriate tools
4. **Analyze Network**: Review entity relationships
5. **Generate Report**: Auto-enrich and export
6. **Share Findings**: Collaborate with team
7. **Archive**: Close case when complete

### Performance Tips

- **Use Mock Mode** for demos and training
- **Enable Caching** for frequently queried data
- **Batch Queries** when possible
- **Set Rate Limits** to avoid API bans
- **Regular Exports** to backup investigation data

### Security Recommendations

1. **Change default password** immediately
2. **Use strong passwords** (12+ characters, mixed case, symbols)
3. **Limit API key scope** where possible
4. **Rotate credentials** regularly
5. **Enable 2FA** on external services
6. **Audit team access** periodically
7. **Review logs** for suspicious activity

## Keyboard Shortcuts

Coming in future release:
- `Ctrl+K`: Quick search
- `Ctrl+N`: New investigation
- `Ctrl+S`: Save report
- `Esc`: Close modals

## Troubleshooting

### No Results Returned

**Cause**: API service unavailable or rate limited

**Solution**:
1. Check Settings → API Configuration
2. Verify API key is correct
3. Check rate limit hasn't been exceeded
4. Review service status page
5. Wait and retry (automatic fallback to mock data)

### Slow Performance

**Cause**: External API latency

**Solution**:
- Use cached data when available
- Reduce concurrent requests
- Switch to mock mode temporarily

### Network Graph Empty

**Cause**: No investigations performed yet

**Solution**:
1. Run at least one investigation tool
2. Wait for results
3. Navigate back to Network tab

## Advanced Features

### Export Formats

**JSON**: Machine-readable, perfect for automation
**CSV**: Spreadsheet-compatible, easy reporting

### Filtering & Search

Coming soon:
- Search investigations by IOC
- Filter reports by date range
- Case status filters

### Custom Integrations

See [Development Guide](./DEVELOPMENT.md) for:
- Adding new OSINT tools
- Custom API integrations
- Webhook notifications

## Getting Help

- **Documentation**: Check other docs in `docs/` folder
- **Issues**: Report bugs on GitHub Issues
- **Community**: Join GitHub Discussions
- **Updates**: Watch repository for new releases

---

**Happy Investigating! Remember: With great OSINT power comes great responsibility.**
