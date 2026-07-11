# Termux Usage Guide

This guide explains how to run Ethical OSINT Tracker inside [Termux](https://termux.dev/) on Android. Flask starts in seconds — no Node.js, no frontend build step.

## 1. Device & Resource Considerations

- Minimum 2 GB RAM recommended
- SQLite is used by default (no separate database server needed)
- Flask is lightweight — even low-end devices handle it fine
- Keep device charging during extended investigation sessions

## 2. Required Packages

```bash
pkg update && pkg upgrade -y
pkg install -y python git clang libffi openssl libjpeg-turbo zlib freetype libxml2 libxslt tmux
```

Optional (MySQL instead of SQLite):
```bash
pkg install -y mariadb
```

## 3. Clone & Setup

```bash
git clone https://github.com/idorenyinbassey/Ethical-OSINT-Tracker.git
cd Ethical-OSINT-Tracker
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Database Initialisation

The admin password comes from `ADMIN_PASSWORD` (min 8 chars); there is no
default. Username is always `admin`.

```bash
ADMIN_PASSWORD='choose-a-strong-password' python reset_admin.py  # creates tables + admin
```

If `cryptography` won't import or the scheduler reports a timezone error, see
[TERMUX_INSTALL.md](./TERMUX_INSTALL.md) (install `python-cryptography` and
`tzdata`).

## 5. Running the App

```bash
python run.py
```

Open Chrome/Firefox on your device and go to `http://localhost:3000`.

To keep the server running when Termux loses focus, use `tmux`:

```bash
tmux new -s osint
python run.py
# Detach: Ctrl+b then d
# Reattach later:
tmux attach -t osint
```

## 6. Access from Other Devices on the Same Network

Find your device IP:
```bash
ip -4 addr show wlan0 | grep inet
```

Flask already binds to `0.0.0.0` by default, so other devices on the same Wi-Fi can reach the app at `http://<device-ip>:3000`.

**Only do this on trusted networks.**

## 7. Storage for Image Uploads

```bash
termux-setup-storage   # grants storage permission
```

Uploaded images are saved to `app/uploads/` inside the project directory.

## 8. Performance Tips

| Aspect | Recommendation |
|--------|---------------|
| Startup | Flask starts in ~2s — no frontend build needed |
| Memory | Flask uses ~60–80 MB RAM at idle |
| Battery | Use `termux-wake-lock` to prevent background kill |
| Database | Keep SQLite on internal storage, not SD card |

## 9. Troubleshooting

| Issue | Fix |
|-------|-----|
| `argon2-cffi` compile errors | `pkg install clang libffi` then `pip install argon2-cffi --no-binary=:all:` |
| Pillow build fails | `pkg install libjpeg-turbo zlib freetype && pip install Pillow` |
| `lxml` / `python-docx` build fails | `pkg install libxml2 libxslt` then retry `pip install -r requirements.txt` |
| Port 3000 in use | `fuser -k 3000/tcp` |
| App killed by Android | Run `termux-wake-lock` before starting |
| SSL errors from httpx | `pkg install ca-certificates` |

## 10. Keeping the App Alive

```bash
termux-wake-lock
python run.py
```

Release when done:
```bash
termux-wake-unlock
```

## 11. Auto-Start on Boot

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

## 12. Updating

```bash
cd ~/Ethical-OSINT-Tracker
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt --upgrade
python run.py
```

## 13. Ethics Reminder

Mobile accessibility does not change acceptable use boundaries. All ethical guidelines in `README.md` still apply — only investigate targets you are authorised to query.

---

Issues? Open a GitHub issue with device model, Android version, and Termux package versions (`pkg list-installed`).
