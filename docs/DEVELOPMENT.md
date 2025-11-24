# Development Guide

This guide provides instructions for developers who want to contribute to the Ethical OSINT Tracker project.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Running Tests](#running-tests)
- [Adding a New Investigation Tool](#adding-a-new-investigation-tool)
- [Database Migrations](#database-migrations)
- [Submitting Contributions](#submitting-contributions)

## Prerequisites

- All requirements from the [Installation Guide](./INSTALLATION.md).
- A good understanding of Python, Reflex, and SQLModel.
- Familiarity with OSINT techniques and ethical considerations.
- A code editor like VS Code with Python support.

### Development Dependencies

Install these packages for linting, formatting, and testing:
```bash
pip install black ruff pytest pytest-asyncio
```

## Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Ethical-OSINT-Tracker.git
   cd Ethical-OSINT-Tracker
   ```
3. **Set up the upstream remote**:
   ```bash
   git remote add upstream https://github.com/idorenyinbassey/Ethical-OSINT-Tracker.git
   ```
4. **Create a virtual environment** and install dependencies as described in the [Installation Guide](./INSTALLATION.md).

## Development Workflow

1. **Sync your fork**:
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/my-new-feature
   ```
3. **Run the app in development mode**:
   ```bash
   reflex run
   ```
   The app will hot-reload as you make changes to the code.

4. **Make your changes**. Follow the architectural patterns outlined in [ARCHITECTURE.md](./ARCHITECTURE.md).
   - Add new state logic in `app/states/`.
   - Create new UI components in `app/components/`.
   - Implement new pages in `app/pages/`.
   - Add database models in `app/models/`.
   - Create repositories for data access in `app/repositories/`.

5. **Write tests** for your new features (see [Running Tests](#running-tests)).

6. **Format and lint** your code:
   ```bash
   black .
   ruff check . --fix
   ```

7. **Commit your changes** with a descriptive message:
   ```bash
   git add .
   git commit -m "feat: Add my new feature"
   ```

8. **Push to your fork**:
   ```bash
   git push origin feature/my-new-feature
   ```

9. **Open a Pull Request** on the main repository.

## Coding Standards

### Python

- **Style**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/). We use `black` for formatting and `ruff` for linting to enforce this.
- **Type Hinting**: All functions and methods must have type hints.
- **Docstrings**: Use Google-style docstrings for all public modules, classes, and functions.
- **Imports**: Group imports in the following order:
  1. Standard library imports
  2. Third-party imports
  3. Local application imports

### Reflex

- **State Management**: Keep state logic separate from UI components. State classes should be the single source of truth.
- **Componentization**: Break down the UI into small, reusable components.
- **Reactivity**: Use `rx.cond` and `rx.foreach` for conditional and dynamic rendering. Avoid standard Python `if/else` or `for` loops on reactive variables within component functions.
- **Events**: Event handlers should be clearly named and, where possible, handle a single responsibility.

## Running Tests

We use `pytest` for testing.

1. **Create a test file**: For a module `app/utils/my_util.py`, create a test file `tests/utils/test_my_util.py`.
2. **Write your tests**:

   ```python
   # tests/utils/test_my_util.py
   from app.utils.my_util import my_function

   def test_my_function():
       assert my_function(2, 2) == 4
       assert my_function(-1, 1) == 0
   ```
   For async functions, use `pytest-asyncio`:
   ```python
   import pytest

   @pytest.mark.asyncio
   async def test_my_async_function():
       result = await my_async_function()
       assert result is True
   ```

3. **Run tests**:
   ```bash
   pytest
   ```

## Adding a New Investigation Tool

Follow this pattern to add a new tool (e.g., for "Username" lookup):

1. **Extend `InvestigationState`** (`app/states/investigation_state.py`):
   - Add state variables for the query, result, and loading status.
   ```python
   class InvestigationState(rx.State):
       # ...
       username_query: str = ""
       username_results: list[dict] = []
       is_loading_username: bool = False
   ```
   - Create an `async` event handler to perform the lookup.
   ```python
   @rx.event
   async def search_username(self):
       if not self.username_query:
           return
       self.is_loading_username = True
       self.username_results = []
       yield

       # Call your service client (or mock data function)
       self.username_results = await fetch_username_data(self.username_query)
       
       # Add to graph
       self._add_to_graph(
           node_id=self.username_query, 
           node_type="person", 
           label=self.username_query
       )

       self.is_loading_username = False
   ```

2. **Create a Service Client** (`app/services/`):
   - Create `username_client.py` to handle the API call and mocking logic.

3. **Create the UI Component** (`app/components/investigation_tools.py`):
   - Create a function `username_tool()` that returns an `rx.Component`.
   - Follow the existing structure: ethical reminder card, input form, and conditional result panel.
   ```python
   def username_tool() -> rx.Component:
       return rx.el.div(
           ethical_reminder_card(...),
           rx.el.input(on_change=InvestigationState.set_username_query),
           rx.el.button("Search", on_click=InvestigationState.search_username),
           rx.cond(
               InvestigationState.is_loading_username,
               rx.spinner(),
               rx.foreach(
                   InvestigationState.username_results,
                   username_result_card
               )
           )
       )
   ```

4. **Add to Investigation Page** (`app/pages/investigation.py`):
   - Add a new tab button in the `tools_tabs()` component.
   ```python
   tools_tabs():
       # ...
       tab_button("Username", "username", "user"),
       # ...
   ```
   - Add a case to the `rx.match()` to render your new tool.
   ```python
   rx.match(
       InvestigationState.active_tab,
       # ...
       ("username", username_tool()),
       # ...
   )
   ```

## Database Migrations

We use **Alembic** directly (not Reflex wrapper commands) for schema migrations. The migration environment lives in the `alembic/` directory and is configured via `alembic.ini` and `alembic/env.py`.

### Why sys.path Injection?

Alembic executes `env.py` from its own context; depending on how it's invoked, the project root might not be on `sys.path`. We inject the project root at the top of `alembic/env.py` so that imports like `from app.models.user import User` are reliable across environments (CI, local shells, container runs). This prevents `ModuleNotFoundError: No module named 'app'` during migration operations.

### When to Create a Migration
Create a migration whenever you modify models in `app/models/`:
1. Adding or removing a table/model.
2. Changing column definitions (type, nullable, constraints, indexes).
3. Adding/removing relationships or foreign keys.

### Preparing for Autogenerate
Alembic only sees models that are imported in `alembic/env.py`. Always add new model imports there before generating a revision to avoid false positives (e.g., unintended table drop operations).

### Generating a Migration
```bash
source .venv/bin/activate
export DB_URL=sqlite:///./dev.db   # or mysql+pymysql://user:pass@host/db
alembic revision --autogenerate -m "add audit_log table"
```
Review the generated file in `alembic/versions/`. Ensure only intended changes appear (create/drop/alter). Remove accidental operations before committing.

### Applying Migrations
```bash
alembic upgrade head            # Apply all pending migrations
alembic upgrade <revision_id>   # Apply up to a specific revision
```

### Downgrading (Use Sparingly)
```bash
alembic downgrade -1            # Step back one revision
alembic downgrade <revision_id> # Downgrade to a specific revision
```
Downgrades can be destructive—avoid running them in production unless absolutely necessary.

### Adding a Test/Demo Migration
Example: Adding an `auditlog` table for event tracking (see model in `app/models/audit_log.py`). After adding the model and importing it in `env.py`, the revision was generated:
```bash
alembic revision --autogenerate -m "add audit_log table"
alembic upgrade head
```
Resulting migration creates the `auditlog` table with fields `id`, `event`, `detail`, `created_at`.

### Common Pitfalls
- Missing imports in `env.py` → Alembic thinks tables were removed.
- Forgetting to set `DB_URL` → Falls back to default SQLite; unexpected environment.
- Manual edits introducing syntax errors (e.g., leaving plain text in migration body). Always keep migration body valid Python.

### Production Recommendations
1. Use **MySQL/PostgreSQL** for multi-user deployments (set `DB_URL`).
2. Run migrations as part of deployment pipeline (CI/CD step before app start).
3. Keep migration messages concise but descriptive (e.g. `add team member table`).
4. Never autogenerate inside a dirty working directory (uncommitted model changes cause confusion).

### Inspect Current Revision State
```bash
alembic current      # Show current applied revision
alembic history      # List all revisions
```
Include output in PRs when submitting schema changes.

## Submitting Contributions

- **Create a Pull Request (PR)** from your feature branch to the `main` branch of the upstream repository.
- **Provide a clear title and description** for your PR, explaining the "what" and "why" of your changes.
- **Link to any relevant issues** (e.g., "Closes #123").
- **Ensure all automated checks (CI/CD) pass**. If they fail, review the logs and push fixes to your branch.
- **Be responsive** to feedback and review comments.

Thank you for contributing to the Ethical OSINT Tracker!
