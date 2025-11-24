# Architecture Overview

This document outlines the technical architecture of the Ethical OSINT Tracker, a web application built with the Reflex framework.

## Core Technologies

- **Framework**: [Reflex](https://reflex.dev/) (v0.8.9) - A pure Python web framework for building reactive web apps.
- **Language**: Python 3.11+
- **Database**: [SQLModel](https://sqlmodel.tiangolo.com/) ORM with SQLite (development) and MySQL (production) support.
- **Frontend**: Reflex components compiled to Next.js/React, styled with [Tailwind CSS](https://tailwindcss.com/).
- **Password Hashing**: [Argon2](https://argon2-cffi.readthedocs.io/) for secure credential storage.
- **HTTP Client**: [HTTPX](https://www.python-httpx.org/) for asynchronous external API calls.

## Project Structure

```
Ethical-OSINT-Tracker/
├── app/
│   ├── components/         # Reusable UI components (layout, widgets, charts)
│   ├── models/            # SQLModel database definitions (User, Case, etc.)
│   ├── pages/             # Page components (Dashboard, Investigation, Settings)
│   ├── repositories/      # Data access layer for CRUD operations
│   ├── services/          # External API clients (HIBP, IPInfo, etc.)
│   ├── states/            # Reflex state management classes
│   └── utils/             # Helper utilities (crypto, rate limiting)
├── alembic/               # Database migration scripts
├── assets/                # Static assets (images, fonts)
├── docs/                  # Project documentation
├── .github/               # GitHub-specific files (workflows, templates)
├── requirements.txt       # Python dependencies
├── rxconfig.py           # Reflex application configuration
├── reset_admin.py        # Admin user setup script
└── start.sh              # Application launch script
```

## Data Flow & State Management

The application follows a reactive, state-driven architecture powered by Reflex.

### 1. State Layer (`app/states/`)

- **Centralized State**: Application state is managed in `rx.State` subclasses. Each major feature (Dashboard, Investigation, Auth, etc.) has its own state class.
- **Reactive Vars**: State variables (`rx.Var`) automatically update the UI when their values change.
- **Computed Vars**: `@rx.var` decorated methods provide derived, cached properties that react to changes in their dependencies.
- **Event Handlers**: `@rx.event` decorated methods handle user interactions (e.g., button clicks, form submissions). They can be synchronous or asynchronous (`async def`).
- **Async Operations**: Async event handlers use `yield` to immediately update the UI (e.g., set a loading flag) before performing long-running tasks like API calls.

**Example (`InvestigationState`):**
```python
class InvestigationState(rx.State):
    domain_query: str = ""
    domain_result: Optional[DomainResult] = None
    is_loading_domain: bool = False

    @rx.event
    async def search_domain(self):
        if not self.domain_query:
            return
        
        # 1. Set loading state and yield to update UI
        self.is_loading_domain = True
        self.domain_result = None
        yield

        # 2. Perform async work (API call or mock)
        await asyncio.sleep(1.0)
        result = self._get_mock_domain_data(self.domain_query)

        # 3. Update result and loading state
        self.domain_result = result
        self.is_loading_domain = False
```

### 2. UI Layer (`app/components/` & `app/pages/`)

- **Component-Based**: The UI is built from small, reusable functions that return `rx.Component` instances.
- **Pure Functions**: Components are pure functions that map state to UI. They do not contain business logic.
- **Styling**: Tailwind CSS utility classes are passed via the `class_name` prop for consistent and responsive styling.
- **Conditional Rendering**: `rx.cond()` is used to show/hide components based on state variables (e.g., showing a spinner when `is_loading` is true).
- **Dynamic Lists**: `rx.foreach()` iterates over a reactive list in the state, rendering a component for each item.

**Example (`domain_tool` component):**
```python
def domain_tool() -> rx.Component:
    return rx.el.div(
        # Input field bound to state
        rx.el.input(
            placeholder="example.com",
            on_change=InvestigationState.set_domain_query,
        ),
        # Button triggers event handler
        rx.el.button(
            "Lookup Domain",
            on_click=InvestigationState.search_domain,
        ),
        # Conditional rendering for loading/results
        rx.cond(
            InvestigationState.is_loading_domain,
            rx.spinner(),
            rx.cond(
                InvestigationState.domain_result,
                domain_result_card(InvestigationState.domain_result),
                rx.el.p("Enter a domain to start.")
            )
        )
    )
```

## Database & Persistence

### Models (`app/models/`)

- **SQLModel**: Combines SQLAlchemy and Pydantic for database models with type validation.
- **Tables**: Each model class (e.g., `User`, `Case`, `Investigation`) maps to a database table.
- **Relationships**: Foreign keys and relationship attributes define connections between tables.

### Repositories (`app/repositories/`)

- **Abstraction Layer**: The repository pattern decouples business logic from data access. State management classes call repository functions instead of directly interacting with the database session.
- **Session Management**: A `session_scope` context manager ensures that database sessions are created and closed correctly for each operation, preventing session leaks.
- **CRUD Operations**: Each repository provides standard Create, Read, Update, Delete functions for its corresponding model.

**Example (`user_repository.py`):**
```python
from app.db import session_scope
from app.models.user import User

def get_user_by_username(username: str) -> Optional[User]:
    with session_scope() as session:
        user = session.query(User).filter(User.username == username).first()
        if user:
            session.expunge(user) # Detach from session
        return user

def create_user(user: User) -> User:
    with session_scope() as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user
```

### Database Initialization (`app/db.py`)

- **`init_db()`**: A function that creates all tables based on the SQLModel metadata. It's called on application startup.
- **`reset_db()`**: Drops and recreates all tables, used for development resets.
- **Migrations**: Alembic is configured for managing schema changes in production environments, though `init_db` is used for simplicity in development.

## External Services (`app/services/`)

- **API Clients**: Each external OSINT service (e.g., HIBP, IPInfo) has its own client module.
- **Asynchronous Calls**: Clients use `httpx.AsyncClient` for non-blocking API requests.
- **Error Handling**: API calls are wrapped in `try...except` blocks to handle network errors, timeouts, and non-2xx responses gracefully.
- **Mocking Fallback**: If a live API call fails (or no API key is provided), the service falls back to a deterministic mock data generator. This ensures the application remains functional.
- **Caching**: A simple time-based decorator (`@cached`) is used to cache API responses, reducing redundant calls and respecting rate limits.

**Example (`ip_client.py`):**
```python
from .cache import cached
import httpx

@cached(ttl=3600) # Cache for 1 hour
async def fetch_ip(ip: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            # ... API call logic ...
            return response.json()
    except Exception:
        # ... Fallback to mock data ...
        return _get_mock_ip_data(ip)
```

## Authentication & Security

### Authentication Flow

1. **Registration**: User provides username/password. Password is hashed with Argon2.
2. **Login**: User provides credentials. Submitted password is hashed and compared to the stored hash.
3. **Session Management**: Upon successful login, the `user_id` is stored in the `AuthState`.
4. **Protected Routes**: Page components check `AuthState.is_authenticated`. If `False`, the user is redirected to the login page using `rx.redirect()`.

### Security Features

- **Password Hashing**: `argon2-cffi` is used for strong, salted password hashing.
- **Input Validation**: Pydantic models and form validation in the state layer prevent invalid data.
- **Ethical Reminders**: Each investigation tool includes a prominent reminder card about legal and ethical use.
- **Rate Limiting**: A utility in `app/utils/rate_limiter.py` tracks API calls per user to prevent abuse.
- **API Key Security**: API keys are stored server-side and are not exposed to the client. The `SettingsState` handles them securely.

## UI/UX Design

- **Layout**: A consistent layout is enforced by the `sidebar` and `header` components in `app/components/layout.py`.
- **Styling**: Tailwind CSS provides a utility-first approach, enabling rapid development of a modern, responsive UI. The color palette and spacing are standardized.
- **Responsiveness**: The UI is designed to be mobile-friendly, with the sidebar collapsing into a menu on smaller screens.
- **User Feedback**: Loading states (spinners), success messages, and error notifications provide clear feedback to the user during operations.
- **Notifications**: A global notification system (`NotificationState`) displays toast-style messages for events like successful saves or API errors.

## Build & Deployment

- **Development**: `reflex run` starts a hot-reloading development server for both frontend and backend.
- **Production**: `reflex export` creates a statically optimized frontend build (`.web/`) and a separate backend server.
- **Deployment Strategy**: See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions on deploying with Gunicorn, Nginx, and Docker.
