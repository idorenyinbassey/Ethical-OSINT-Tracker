# Ethical OSINT Tracker

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Reflex 0.8+](https://img.shields.io/badge/reflex-0.8+-orange.svg)](https://reflex.dev/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Copyright (C) 2025 Idorenyin Bassey](https://img.shields.io/badge/copyright-©%202025%20Idorenyin%20Bassey-lightgrey.svg)](https://github.com/idorenyinbassey)

A comprehensive ethical Open Source Intelligence (OSINT) investigation platform built with Reflex (Python). Perform legally compliant investigations with domain analysis, IP geolocation, email validation, social media reconnaissance, phone number verification, and more.

## 🌟 Features

### Investigation Tools
- **Domain Intelligence**: WHOIS lookups, DNS records, registration history
- **IP Geolocation**: ASN mapping, ISP identification, threat scoring
- **Email Analysis**: Format validation, breach detection, domain reputation
- **Social Media OSINT**: Username enumeration across platforms
- **Phone Intelligence**: Carrier lookup, fraud scoring, location data
- **Image Forensics**: Facial recognition, EXIF metadata extraction
- **IMEI/Device Tracking**: Device identification, blacklist checks

### Collaboration & Management
- **Case Management**: Organize investigations by priority and status
- **Team Collaboration**: Multi-user teams with role-based access
- **Intelligence Reports**: Auto-enrichment from investigation data with export
- **Network Graph Visualization**: Spiderfoot-style entity relationship mapping

### Security & Compliance
- **Authentication**: Argon2 password hashing with secure session management
- **Rate Limiting**: Per-user and global API throttling
- **Audit Logging**: Investigation history and data persistence
- **Ethical Guidelines**: Built-in reminders for legal OSINT practices
- **API Configuration**: Centralized management of external OSINT services

### Technical Highlights
- **Reactive UI**: Built with Reflex for seamless real-time updates
- **Deterministic Mock Data**: Reproducible results for testing/demos
- **Graceful Degradation**: Fallback to mock data when APIs unavailable
- **Modern Stack**: SQLModel, SQLite/MySQL, Tailwind CSS styling

## 📋 Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git
- Linux/macOS/WSL (recommended)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/idorenyinbassey/Ethical-OSINT-Tracker.git
cd Ethical-OSINT-Tracker
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Database

```bash
python reset_admin.py
```

This creates a demo admin user:
- **Username**: `admin`
- **Password**: `changeme`

⚠️ **Change this password immediately in production!**

### 5. Run the Application

```bash
reflex run
```

Or use the convenience script:

```bash
chmod +x start.sh
./start.sh
```

The app will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000

## 📖 Documentation

Detailed documentation is available in the [`docs/`](./docs/) directory:

- [Installation Guide](./docs/INSTALLATION.md) - Detailed setup instructions
- [User Guide](./docs/USER_GUIDE.md) - Complete feature walkthrough
- [Architecture](./docs/ARCHITECTURE.md) - Technical design and patterns
- [API Integration](./docs/API_INTEGRATION.md) - External service configuration
- [Development Guide](./docs/DEVELOPMENT.md) - Contributing and extending
- [Deployment](./docs/DEPLOYMENT.md) - Production deployment strategies
- [Termux Guide](./docs/TERMUX.md) - Running on Android (Termux), headless mode

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database (optional, defaults to SQLite)
DB_URL=sqlite:///./reflex.db
# For MySQL:
# DB_URL=mysql+pymysql://user:password@localhost/osint_tracker

# API Keys (optional for live data)
WHOISXML_API_KEY=your_key_here
HIBP_API_KEY=your_key_here
IPINFO_TOKEN=your_token_here
HUNTER_API_KEY=your_key_here
NUMVERIFY_KEY=your_key_here
```

### API Services Configuration

Navigate to **Settings** page in the app to configure:
- WhoisXML API (domain WHOIS)
- Have I Been Pwned (breach data)
- IPInfo.io (IP geolocation)
- Shodan (device search)
- VirusTotal (threat analysis)
- Hunter.io (email verification)
- NumVerify (phone validation)

## 🗂️ Project Structure

```
Ethical-OSINT-Tracker/
├── app/
│   ├── components/         # Reusable UI components
│   ├── models/            # SQLModel database models
│   ├── pages/             # Page components
│   ├── repositories/      # Data access layer
│   ├── services/          # External API clients
│   ├── states/            # Reflex state management
│   └── utils/             # Helper utilities
├── alembic/               # Database migrations
├── assets/                # Static assets
├── docs/                  # Documentation
├── requirements.txt       # Python dependencies
├── rxconfig.py           # Reflex configuration
├── reset_admin.py        # Admin user setup
└── start.sh              # Launch script
```

## 🔒 Security & Ethics

### Ethical Use Policy

This tool is designed **exclusively** for:
✅ Authorized security research  
✅ Lawful investigations with proper consent  
✅ Academic research and education  
✅ Penetration testing with written permission  

**Prohibited Uses**:
❌ Unauthorized surveillance or stalking  
❌ Harassment or doxxing  
❌ Privacy violations  
❌ Illegal data collection  

### Security Best Practices

1. **Change default credentials** immediately
2. **Never commit** API keys or `.env` files
3. **Use HTTPS** in production (reverse proxy recommended)
4. **Enable rate limiting** for public deployments
5. **Encrypt API keys** at rest (see `app/utils/crypto.py`)
6. **Regular updates** to dependencies for security patches

## 🛠️ Development

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

### Code Style

```bash
# Format with black
black app/

# Lint with ruff
ruff check app/
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [DEVELOPMENT.md](./docs/DEVELOPMENT.md) for detailed guidelines.

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Kill existing Reflex processes
pkill -f "reflex run"

# Or specify different ports in rxconfig.py
```

### Database Locked Error

```bash
# Reset database
rm reflex.db
python reset_admin.py
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📊 Performance

- **Mock Mode**: Instant responses with deterministic data
- **Live APIs**: 1-5 second response times (depends on external services)
- **Rate Limits**: Configurable per-service (default: 100/hour)
- **Caching**: 1-hour TTL for domain/IP lookups

## 🗺️ Roadmap

- [ ] Advanced graph analytics and clustering
- [ ] PDF/DOCX report exports
- [ ] Real-time collaboration features
- [ ] Blockchain address tracking
- [ ] Dark web monitoring integration
- [ ] Mobile app (React Native)
- [ ] Plugin architecture for custom tools

## 📜 License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details.

This means:
- ✅ You can use this software for any purpose
- ✅ You can modify and distribute it
- ✅ You must share modifications under GPL v3
- ✅ You must include the original copyright notice

## 🙏 Acknowledgments

- [Reflex](https://reflex.dev/) - Pure Python web framework
- [SQLModel](https://sqlmodel.tiangolo.com/) - Database ORM
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS
- Lucide Icons via Reflex icon library
- OSINT community for methodology and best practices

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/issues)
- **Documentation**: [docs/](./docs/)
- **Discussions**: [GitHub Discussions](https://github.com/idorenyinbassey/Ethical-OSINT-Tracker/discussions)

## ⚠️ Disclaimer

This software is provided for **educational and lawful purposes only**. Users are solely responsible for ensuring their use complies with all applicable laws and regulations. The authors assume no liability for misuse or illegal activities conducted with this tool.

---

**Built with ❤️ for the ethical OSINT community**

Star ⭐ this repo if you find it useful!
