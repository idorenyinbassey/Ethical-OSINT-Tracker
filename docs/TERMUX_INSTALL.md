# Termux Installation Guide

Complete guide for installing and running Ethical OSINT Tracker on Android using Termux.

## Prerequisites

### Install Termux
- **Recommended**: Install from [F-Droid](https://f-droid.org/en/packages/com.termux/) — the Google Play version is outdated
- Minimum Android 7.0 (API 24); Android 10+ recommended
- 2 GB RAM minimum, 4 GB recommended

### Optional Termux add-ons (from F-Droid)
- **Termux:Boot** — auto-start the app on device boot
- **Termux:Widget** — home screen launch shortcut

## Installation

### Step 1 — Update Termux and install system packages

```bash
pkg update && pkg upgrade -y
pkg install -y python git clang libffi openssl libjpeg-turbo zlib freetype libxml2 libxslt tmux
```

> No Node.js or Rust required — Flask has no frontend build step.

### Step 2 — Grant storage permission (for image uploads)

```bash
termux-setup-storage
```

Press **Allow** when prompted.

### Step 3 — Clone the repository

```bash
cd ~
git clone https://github.com/idorenyinbassey/Ethical-OSINT-Tracker.git
cd Ethical-OSINT-Tracker
```

> **Fastest path:** run `./install_termux.sh` here and skip to
> [Step 7](#step-7--run-the-app). It installs the system packages above,
> prefers `pipx` over a manual venv (falling back automatically if pipx
> isn't available), generates and persists `SECRET_KEY` /
> `API_KEYS_FERNET_KEY` for you, and prompts for the admin password with
> the terminal input hidden — nothing is typed inline or left in shell
> history. Steps 4-6 below are the manual/troubleshooting equivalent of
> what that script does.

### Step 4 — Create a virtual environment and install Python packages

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If Pillow fails to build:
```bash
pkg install libjpeg-turbo zlib freetype libxml2 libxslt
pip install Pillow --no-cache-dir
```

If `cryptography` fails to import (`ImportError: dlopen failed ... _rust.abi3.so`),
its prebuilt wheel is incompatible with your Python. Use Termux's build:
```bash
pkg install python-cryptography rust openssl openssl-tool clang binutils
pip install --no-binary cryptography --force-reinstall cryptography
python -c "from cryptography.fernet import Fernet; print('crypto OK')"
```

Install `tzdata` so the background scheduler can resolve your timezone
(Termux lacks the IANA tz database by default):
```bash
pip install tzdata
```

### Step 5 — Set environment variables

`./start.sh` handles this automatically (recommended): it generates
`SECRET_KEY` and `API_KEYS_FERNET_KEY` once on first run and persists them
to `secrets.env`, loading that file on every subsequent run — so a
restart never logs you out or breaks previously-saved API keys. `.env` is
also auto-loaded if you prefer to manage it yourself (see `.env.example`).

To do it fully by hand instead:
```bash
cat > secrets.env <<'EOF'
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
API_KEYS_FERNET_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
EOF
set -a && source secrets.env && set +a
```

### Step 6 — Initialise the database

There is **no default password**. Running `./start.sh` (or
`./start.sh --reset-admin`) without `ADMIN_PASSWORD` already set prompts
for it interactively — hidden input, confirmed twice, never written to
shell history:

```bash
python reset_admin.py
# Set the admin account password (min. 8 characters).
# Input is hidden and is never written to shell history.
```

For non-interactive/scripted setups the env-var form still works:
```bash
ADMIN_PASSWORD='choose-a-strong-password' python reset_admin.py
```

Creates (or resets) the admin account:
- **Username**: `admin` (fixed)
- **Password**: the value you entered / supplied

### Step 7 — Run the app

```bash
./start.sh                  # preferred — pipx if available, .venv fallback, gunicorn
FLASK_DEV=1 ./start.sh       # development server instead of gunicorn
```

Open Chrome or Firefox on your device and go to:
```
http://localhost:3000
```

Log in with `admin` and the password you set. To change it later, hidden-prompt:
```bash
./start.sh --reset-admin
```

## Running in the Background with tmux

```bash
tmux new -s osint
./start.sh
# Detach (keep running): Ctrl+b then d
# Reattach later:
tmux attach -t osint
```

## Prevent Android from Killing the Process

```bash
termux-wake-lock
./start.sh
```

Release when done: `termux-wake-unlock`

## Access from Other Devices on the Same Wi-Fi

Find your Android IP:
```bash
ip -4 addr show wlan0 | grep inet
```

Flask binds to `0.0.0.0:3000` by default, so other devices on the same network can reach `http://<your-phone-ip>:3000`.

**Only do this on trusted (home) networks.**

## Expose Publicly with a Tunnel (Optional)

Using Cloudflare Tunnel (free, no account required for quick tunnels):
```bash
pkg install cloudflared
cloudflared tunnel --url http://localhost:3000
```

Using ngrok:
```bash
pkg install wget
wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm64.tgz
tar xvzf ngrok-stable-linux-arm64.tgz
./ngrok http 3000
```

## Auto-Start on Boot

Requires Termux:Boot from F-Droid.

```bash
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-osint.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd ~/Ethical-OSINT-Tracker
nohup ./start.sh > /tmp/osint.log 2>&1 &
EOF
chmod +x ~/.termux/boot/start-osint.sh
```

secrets.env and dev.db already exist by boot time (from initial setup), so
`start.sh` starts straight into gunicorn with no interactive prompt.

## Updating

```bash
cd ~/Ethical-OSINT-Tracker
git pull origin main
# Restart the app — start.sh reinstalls/updates dependencies (pipx or .venv) automatically
./start.sh
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Pillow build fails | `pkg install libjpeg-turbo zlib freetype && pip install Pillow` |
| `lxml` / `python-docx` build fails | `pkg install libxml2 libxslt` then retry `pip install -r requirements.txt` |
| `argon2-cffi` compile error | `pkg install clang libffi && pip install argon2-cffi --no-binary=:all:` |
| Port 3000 in use | `fuser -k 3000/tcp` |
| App killed by Android | `termux-wake-lock` before starting |
| httpx timeout | Check internet; timeouts are per-request (5–10 s by default) |
| SSL certificate errors | `pkg install ca-certificates` |
| Permission denied | `chmod -R 755 ~/Ethical-OSINT-Tracker` |

## Performance Expectations

| Device RAM | App startup | Response time |
|-----------|------------|---------------|
| 2 GB | ~3 s | 2–5 s |
| 4 GB | ~2 s | 1–2 s |
| 6 GB+ | ~1 s | < 1 s |

Flask starts in seconds — there is no Node.js build or frontend compilation.

## Uninstall

```bash
deactivate
cd ~
rm -rf Ethical-OSINT-Tracker
```

## FAQ

**Q: Can I use Termux from Google Play?**  
A: No — use F-Droid only.

**Q: Do I need root?**  
A: No.

**Q: Does this work on iOS?**  
A: Not supported. Use a cloud deployment instead.

**Q: Can I run it 24/7 on my phone?**  
A: Not recommended — use a cloud server for 24/7 uptime.

## Security Notes

- Change the default password immediately
- Only expose to the network on trusted Wi-Fi
- Keep Termux packages updated: `pkg upgrade`
- Enable Android device encryption

---

*Last updated for Flask rewrite. Tested on Termux 0.118+, Android 11–14.*
