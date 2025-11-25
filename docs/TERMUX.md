# Termux Usage Guide

This guide explains how to run Ethical OSINT Tracker inside [Termux](https://termux.dev/) on Android. Termux provides a minimal Linux userland with its own package manager, enabling development and security tooling on mobile devices.

## 1. Device & Resource Considerations
- Prefer mid/high tier devices (≥4GB RAM) for smoother frontend builds.
- CPU throttling may slow JS bundling; keep device cool and screen awake during first build.
- SQLite is recommended; avoid heavier databases unless absolutely required.

## 2. Required Packages
Install core dependencies:
```bash
pkg update && pkg upgrade -y
pkg install -y python git nodejs clang rust libffi openssl libjpeg-turbo zlib tmux
```
Optional (only if you plan to use MySQL/MariaDB):
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

## 4. Database Initialization
```bash
alembic upgrade head   # apply migrations (optional; falls back to create_all)
python reset_admin.py  # creates demo admin (admin/changeme)
```

## 5. Running the App
Standard (frontend + backend):
```bash
reflex run --env dev
```
Headless backend only (skip frontend build — useful for constrained devices):
```bash
HEADLESS=1 ./start.sh
```
Or directly:
```bash
reflex run --env prod --backend-only
```
When running `--backend-only`, you can separately serve a previously exported static frontend:
```bash
reflex export
python -m http.server 8080 -d .web/_static
```

## 6. Keeping Process Alive
Use `tmux` so the server continues when the app loses focus:
```bash
tmux new -s osint
reflex run --env prod
# Detach: Ctrl+b then d
# Reattach:
tmux attach -t osint
```

## 7. Storage & Paths
- Internal app path (`$HOME/Ethical-OSINT-Tracker`) is safe for SQLite.
- To access shared storage: `termux-setup-storage` (avoid placing the database on slow external media).

## 8. Performance Tips
| Aspect | Recommendation |
|--------|----------------|
| Frontend build | Use `--env prod` after initial dev iteration for faster runtime |
| Logging | Set `REFLEX_LOG_LEVEL=warning` to reduce output noise |
| Rebuilds | Avoid frequent dependency reinstalls; pin versions |
| Memory | Close other heavy apps during first build |

## 9. Troubleshooting
| Issue | Fix |
|-------|-----|
| `argon2-cffi` compile errors | Ensure `clang`, `rust`, `libffi`, then `pip install argon2-cffi --no-binary=:all:` |
| `ModuleNotFoundError: app` in Alembic | Already mitigated via path injection in `alembic/env.py` |
| Slow frontend rebuild | Switch to headless backend or exported static mode |
| Port access from LAN | Use device Wi‑Fi IP (`ip addr show wlan0`), ensure firewall disabled |

## 10. Headless Mode Explanation
Headless mode uses `reflex run --backend-only` to start only the Python API process. This:
- Skips installing/building node modules for incremental runs.
- Reduces CPU and memory usage on constrained devices.
- Pairs with a previously exported static frontend OR CLI/state inspection tools.

If you need real-time UI updates again, rerun the full `reflex run` without `--backend-only`.

## 11. Optional: Termux Shortcut Script
Create `run_headless.sh` for convenience:
```bash
#!/data/data/com.termux/files/usr/bin/bash
source .venv/bin/activate
export REFLEX_LOG_LEVEL=warning
reflex run --env prod --backend-only
```
Make executable:
```bash
chmod +x run_headless.sh
```

## 12. Future Mobile Optimizations
Planned improvements:
- Responsive layout refinements (reduced horizontal padding on small screens).
- Lightweight read-only audit dashboard mode.
- Prebuilt static asset bundle releases.

## 13. Ethics Reminder
Mobile accessibility does not change acceptable use boundaries. All ethical guidelines in `README.md` still apply.

---
If you encounter Termux-specific issues, open a GitHub issue with device model, Android version, and Termux package versions.
