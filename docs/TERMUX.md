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
pkg install -y python git clang libffi openssl python-cryptography libjpeg-turbo zlib freetype libxml2 libxslt tmux
```

Optional (MySQL instead of SQLite):
```bash
pkg install -y mariadb
```

## 3. Clone & Setup

```bash
git clone https://github.com/idorenyinbassey/Ethical-OSINT-Tracker.git
cd Ethical-OSINT-Tracker
./install_termux.sh
```

`install_termux.sh` installs the packages from step 2 for you (including
`python-cryptography` — PyPI's `cryptography` can't be used on Termux,
see below), then hands off to `start.sh`. On Termux specifically,
`start.sh` always uses a `--system-site-packages` venv rather than pipx,
so the app can see that system-installed `python-cryptography`. Prefer
to do it by hand instead?
```bash
python -m venv --system-site-packages .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Database Initialisation

There is no default admin password. `./start.sh` prompts for one
interactively on first run — hidden input, confirmed twice, never written
to shell history:

```bash
./start.sh
# Set the admin account password (min. 8 characters).
# Input is hidden and is never written to shell history.
```

`SECRET_KEY` and `API_KEYS_FERNET_KEY` are generated once and saved to
`secrets.env` automatically at the same time, so they stay stable across
restarts — no manual export needed.

For scripted/non-interactive setups, `ADMIN_PASSWORD` can still be
supplied via the environment instead:
```bash
ADMIN_PASSWORD='choose-a-strong-password' ./start.sh
```

If `cryptography` won't import (only possible doing it by hand without
`--system-site-packages`) or the scheduler reports a timezone error, see
[TERMUX_INSTALL.md](./TERMUX_INSTALL.md#step-4--create-a-virtual-environment-and-install-python-packages)
(`pkg install python-cryptography` + `tzdata`).

## 5. Running the App

```bash
./start.sh
```

Open Chrome/Firefox on your device and go to `http://localhost:3000`.

To keep the server running when Termux loses focus, use `tmux`:

```bash
tmux new -s osint
./start.sh
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
| `cryptography` import fails (`dlopen ... PyModule_Type`) | PyPI's build is incompatible with Termux's Python — `pkg install python-cryptography` and make sure your venv has `--system-site-packages` (already handled if installed via `start.sh`). Never `pip install cryptography` on Termux — it shadows the working system package. |
| Pillow build fails | `pkg install libjpeg-turbo zlib freetype && pip install Pillow` |
| `lxml` / `python-docx` build fails | `pkg install libxml2 libxslt` then retry `pip install -r requirements.txt` |
| Port 3000 in use | `fuser -k 3000/tcp` |
| App killed by Android | Run `termux-wake-lock` before starting |
| SSL errors from httpx | `pkg install ca-certificates` |
| Case reports have no map/graph images | Expected on Termux — `playwright` (used to render those snapshots) ships no Android wheels, so `requirements.txt` skips it there. Everything else about report generation is unaffected. |
| Scan (e.g. Social Search) shows "This page isn't working" / empty response | Gunicorn killed the worker for taking too long — Social Search checks up to 273 sites and can exceed the default 120s timeout on slow mobile data. Raise it further: `GUNICORN_TIMEOUT=300 ./start.sh`. |

## 10. Keeping the App Alive

```bash
termux-wake-lock
./start.sh
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
nohup ./start.sh > /tmp/osint.log 2>&1 &
EOF
chmod +x ~/.termux/boot/start-osint.sh
```

secrets.env and dev.db already exist by boot time, so this starts straight
into gunicorn with no interactive prompt.

## 12. Updating

```bash
cd ~/Ethical-OSINT-Tracker
git pull origin main
./start.sh   # reinstalls/updates dependencies (always .venv on Termux) automatically
```

## 13. Ethics Reminder

Mobile accessibility does not change acceptable use boundaries. All ethical guidelines in `README.md` still apply — only investigate targets you are authorised to query.

---

Issues? Open a GitHub issue with device model, Android version, and Termux package versions (`pkg list-installed`).
