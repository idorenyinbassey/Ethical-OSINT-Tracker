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
pkg install -y python git clang libffi openssl libjpeg-turbo zlib freetype tmux
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

### Step 4 — Create a virtual environment and install Python packages

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If Pillow fails to build:
```bash
pkg install libjpeg-turbo zlib freetype
pip install Pillow --no-cache-dir
```

### Step 5 — Initialise the database

```bash
python reset_admin.py
```

Creates the SQLite database and a demo admin account:
- **Username**: `admin`
- **Password**: `changeme`

### Step 6 — Run the app

```bash
python run.py
```

Open Chrome or Firefox on your device and go to:
```
http://localhost:3000
```

Log in with `admin` / `changeme` and **change the password immediately**.

## Running in the Background with tmux

```bash
tmux new -s osint
python run.py
# Detach (keep running): Ctrl+b then d
# Reattach later:
tmux attach -t osint
```

## Prevent Android from Killing the Process

```bash
termux-wake-lock
python run.py
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
source .venv/bin/activate
nohup python run.py > /tmp/osint.log 2>&1 &
EOF
chmod +x ~/.termux/boot/start-osint.sh
```

## Updating

```bash
cd ~/Ethical-OSINT-Tracker
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt --upgrade
# Restart the app
python run.py
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Pillow build fails | `pkg install libjpeg-turbo zlib freetype && pip install Pillow` |
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
