# AI Coding Agent Instructions for Ethical-OSINT-Tracker

This is a **Flask** web app for ethical OSINT investigations. The stack is:
- **Flask 3** + **Flask-Login** for routing and authentication
- **SQLModel** (SQLAlchemy) with SQLite (dev) or MySQL (prod)
- **Jinja2** templates with Tailwind CSS (CDN, no build step)
- **httpx** (sync) for all external API calls
- **Argon2** password hashing

## Project Layout

```
app/
├── __init__.py          # create_app() — registers blueprints
├── config.py            # Config class
├── db.py                # engine, init_db(), get_session()
├── models/              # SQLModel table classes
├── repositories/        # Data access (session_scope pattern)
├── routes/              # Flask blueprints
│   ├── auth.py          # /login  /register  /logout
│   ├── dashboard.py     # /
│   ├── investigation.py # /investigate/ip|domain|email|social|phone|image|imei
│   ├── cases.py         # /cases  CRUD
│   └── settings.py      # /settings
├── services/            # External OSINT API clients (all sync)
├── templates/           # Jinja2 templates
│   ├── base.html        # Shared sidebar layout
│   └── ...
└── utils/               # crypto, rate_limiter, key_manager
run.py                   # Entry point: python run.py
reset_admin.py           # Create/reset demo admin user
```

## Core Patterns

### Routes

```python
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

bp = Blueprint("name", __name__, url_prefix="/prefix")

@bp.route("/")
@login_required
def index():
    data = some_repository.list_all()
    return render_template("name/index.html", data=data)
```

Register all blueprints in `app/__init__.py → create_app()`.

### Services (IMPORTANT: sync only)

All service functions must be **synchronous**. Use `httpx.Client`, never `httpx.AsyncClient`:

```python
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service
import httpx

@cached(ttl=3600)
def fetch_something(query: str):
    cfg = get_by_service("ServiceName")
    if not cfg or not cfg.is_enabled or not cfg.api_key:
        return None
    try:
        with httpx.Client(timeout=8) as client:
            r = client.get(cfg.base_url, params={"q": query, "key": cfg.api_key})
            r.raise_for_status()
            return r.json()
    except Exception:
        return None
```

### Repositories

```python
from app.repositories.base import session_scope
from app.models.something import Something
from sqlmodel import select

def get_by_id(item_id: int):
    with session_scope(expire_on_commit=False) as session:
        item = session.get(Something, item_id)
        if item:
            session.refresh(item)
        return item
```

Always return detached instances (or plain copies) to avoid `DetachedInstanceError`.

### Templates

- All authenticated pages extend `base.html`
- Auth pages (login, register) are standalone
- Flash messages rendered automatically by `base.html`
- Use Tailwind utility classes; no custom CSS file

## Authentication

Flask-Login manages sessions. `User` inherits `UserMixin + SQLModel`.

- Login: `login_user(user)` in `routes/auth.py`
- Protect routes: `@login_required`
- Current user: `current_user` (Flask-Login proxy)
- User loader: `load_user(user_id)` in `app/__init__.py`

## Adding a New Investigation Tool

1. Create `app/services/my_client.py` (sync, with `@cached`)
2. Add a route in `app/routes/investigation.py`:
   ```python
   @investigation_bp.route("/mytool", methods=["GET", "POST"])
   @login_required
   def mytool():
       result = None
       if request.method == "POST":
           query = request.form.get("query", "").strip()
           result = my_client.fetch(query)
           create_investigation(kind="mytool", query=query,
                                result_json=json.dumps(result),
                                user_id=current_user.id)
       return render_template("investigation/mytool.html",
                              result=result, cases=list_cases())
   ```
3. Add `app/templates/investigation/mytool.html` (extend `base.html`)
4. Add sidebar link in `app/templates/base.html`

## Development

```bash
# Setup
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python reset_admin.py

# Run (Flask debug mode with hot reload)
python run.py

# Tests
PYTHONPATH=. pytest -q

# Lint / format
black app/
ruff check app/ --fix
```

## Ethics & Safety

- Every investigation tool page includes an ethical reminder (`<p class="text-sm text-yellow-500">`)
- Only investigate targets you have explicit authorization for
- API keys are stored in the database — never commit them to source control
- For production, implement `encrypt_api_key` / `decrypt_api_key` in `app/utils/crypto.py`
