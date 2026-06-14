# Development Guide

Contributing to Ethical OSINT Tracker.

## Prerequisites

- All requirements from [INSTALLATION.md](./INSTALLATION.md)
- Python 3.11+
- Familiarity with Flask, SQLModel, and Jinja2
- Understanding of OSINT techniques and ethical considerations

### Dev dependencies

```bash
pip install black ruff pytest
```

## Getting Started

1. **Fork** the repo on GitHub
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Ethical-OSINT-Tracker.git
   cd Ethical-OSINT-Tracker
   git remote add upstream https://github.com/idorenyinbassey/Ethical-OSINT-Tracker.git
   ```
3. **Create a virtual environment** and install dependencies (see [INSTALLATION.md](./INSTALLATION.md))

## Development Workflow

```bash
# Keep your fork up to date
git fetch upstream
git checkout main
git merge upstream/main

# Start a feature branch
git checkout -b feature/my-new-feature

# Run the app (hot-reloads with Flask debug mode)
python run.py

# Format and lint before committing
black app/
ruff check app/ --fix

# Run tests
PYTHONPATH=. pytest -q

# Commit
git add app/
git commit -m "feat: describe the change"
git push origin feature/my-new-feature
```

Then open a Pull Request against `main`.

## Coding Standards

- **Style**: PEP 8, enforced with `black` (formatter) and `ruff` (linter)
- **Type hints**: required on all function signatures
- **Docstrings**: one-line for simple functions; skip if the name is self-explanatory
- **Comments**: only where the *why* is non-obvious
- **Imports**: stdlib → third-party → local, one blank line between groups

## Project Conventions

### Routes (app/routes/)

Each blueprint follows this pattern:

```python
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

my_bp = Blueprint("my", __name__, url_prefix="/my")

@my_bp.route("/")
@login_required
def index():
    data = some_repository.list_all()
    return render_template("my/index.html", data=data)
```

Register new blueprints in `app/__init__.py`.

### Templates (app/templates/)

- Extend `base.html` for all authenticated pages
- Auth pages (login, register) are standalone (no `base.html`)
- Use Tailwind utility classes directly in templates; no custom CSS file needed
- Flash messages are rendered automatically by `base.html`

### Services (app/services/)

All service functions are **synchronous** and follow this structure:

```python
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service
import httpx

@cached(ttl=3600)
def fetch_something(query: str):
    cfg = get_by_service("ServiceName")
    if not cfg or not cfg.is_enabled or not cfg.api_key:
        return None   # or return mock data

    try:
        with httpx.Client(timeout=8) as client:
            r = client.get(cfg.base_url, params={"q": query, "key": cfg.api_key})
            r.raise_for_status()
            return r.json()
    except Exception:
        return None
```

Never use `async def` or `httpx.AsyncClient` in services — the Flask dev server and Gunicorn run synchronously.

### Repositories (app/repositories/)

Use `session_scope` for all DB access:

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

Always return detached instances (or explicit copies) so callers don't hit `DetachedInstanceError`.

## Adding a New Investigation Tool

1. **Create a service client** in `app/services/my_tool_client.py`
2. **Add a route** in `app/routes/investigation.py`:
   ```python
   @investigation_bp.route("/mytool", methods=["GET", "POST"])
   @login_required
   def mytool():
       result = None
       if request.method == "POST":
           query = request.form.get("query", "").strip()
           result = my_tool_client.fetch(query)
           create_investigation(kind="mytool", query=query,
                                result_json=json.dumps(result),
                                user_id=current_user.id)
       return render_template("investigation/mytool.html", result=result,
                              cases=list_cases())
   ```
3. **Add a template** at `app/templates/investigation/mytool.html` (extend `base.html`)
4. **Add a sidebar link** in `app/templates/base.html`

## Running Tests

```bash
PYTHONPATH=. pytest -q
```

Tests live in `tests/`. Name files `test_*.py` and functions `test_*`.

Example:

```python
# tests/test_my_util.py
from app.utils.my_util import my_function

def test_my_function_returns_expected():
    assert my_function("input") == "expected output"
```

## Database Migrations

We use Alembic for schema changes.

```bash
# Set DB URL
export DB_URL=sqlite:///./dev.db

# Create a migration after editing a model
alembic revision --autogenerate -m "add new column to case"

# Review alembic/versions/<hash>_add_new_column_to_case.py before committing

# Apply
alembic upgrade head
```

Always import new models in `alembic/env.py` before generating autogenerate revisions — otherwise Alembic may generate DROP TABLE operations for unimported tables.

### Key commands

```bash
alembic current    # Current applied revision
alembic history    # All revisions
alembic upgrade head          # Apply all pending
alembic downgrade -1          # Roll back one revision
```

## Submitting Contributions

- Open a Pull Request from your feature branch to `main`
- Write a clear title and description (what + why)
- Link to related issues (`Closes #123`)
- Ensure CI passes before requesting review
- Be responsive to review comments

Thank you for contributing!
