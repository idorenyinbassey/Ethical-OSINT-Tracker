# AI Coding Agent Instructions for Ethical-OSINT-Tracker

Purpose: Reflex (Python) web app for ethical OSINT investigations. CURRENTLY uses deterministic synthetic mock data only (no external calls). ROADMAP: introduce live data ingestion from vetted open security/OSINT APIs, persist investigations in MySQL, and add authenticated login before exposing real feeds.

## Architecture Overview
- Entry: `app/app.py` builds `rx.App`, registers pages (`index`, `investigation_page`, `auth_page`, `register_page`, `settings_page`). Tailwind plugin enabled in `rxconfig.py`.
- UI Composition: Pure function components returning `rx.Component` via `rx.el.*` primitives and higher-level helpers (`rx.icon`, `rx.recharts.*`). Styling via Tailwind classes passed as `class_name`.
- Pages vs Components: Pages in `app/pages/` compose layout + domain-specific tool sections. Reusable UI blocks live in `app/components/` (layout, widgets, charts, investigation tools, network_tree).
- State Layer: Primary `rx.State` subclasses in `app/states/`:
  - `DashboardState`: real-time metrics from DB, activity list, chart datasets, sidebar toggle, `load_metrics()`/`load_activities()`.
  - `InvestigationState`: multi-tool state (domain/ip/email/social/phone/image/imei/network graph) + async lookup events with rate limiting + persistence.
  - `AuthState`: login/logout/registration with Argon2 password hashing, current_user_id tracking, demo user creation.
  - `NotificationState`: notification drawer with add/mark_read/clear operations, unread count tracking.
  - `SettingsState`: API configuration management (add/edit/delete), form validation.
- Data Flow: Components read reactive attributes (e.g. `DashboardState.active_investigations`) and trigger mutations through `@rx.event` methods (e.g. `toggle_sidebar`). Asynchronous events yield once to propagate loading flags, then await work (mock or live API).
- Graph Model: `_add_to_graph` ensures unique nodes/edges. Improved tree visualization in `network_tree.py` groups entities by category (domain/ip/email/person/device) with color-coded cards and connection lists.
- Database: SQLModel with SQLite (dev) or MySQL (production). Models: User, Investigation, APIConfig. Repositories handle CRUD with `session_scope()` context manager.

## Core Patterns & Conventions
- Component Functions: Named by purpose (`stat_card`, `threat_trends_chart`, `domain_tool`). Return a single composed `rx.el.div` or similar. Keep pure: no side effects.
- Conditional Rendering: `rx.cond(condition, component_if_true, component_if_false?)` and `rx.match` used for tab switching.
- Lists: `rx.foreach(state_list, item_renderer)` for reactive iteration.
- State Mutation: Methods decorated with `@rx.event`; async events often:
  1. Validate input; set `is_loading_* = True`; clear previous result; `yield`.
  2. `await asyncio.sleep(...)` (simulated latency).
  3. Compute deterministic pseudo-data using `random.Random(seed)` where seed derives from `sha256` of user input (`_get_seed`).
- Computed Fields: `@rx.var` for derived dictionaries (e.g. category grouping) that reactively update.
- Uniqueness Guards: Node/edge addition checks existing IDs before append—preserve this pattern when extending.
- Styling: Centralized via Tailwind utility classes; prefer consistent spacing (`p-6`, `rounded-2xl`, `shadow-sm`). Match existing palette (orange accent `text-orange-500`, neutral grays).
- Loading UX: Each tool has `is_loading_<resource>` boolean; button content switches to `rx.spinner(size="1")` using `rx.cond`.

## Adding a New Investigation Tool (Pattern Example)
1. Extend `InvestigationState`: add query field, result field, loading flag.
2. Implement async `@rx.event` similar to existing ones (validate → set loading → yield → await → compute → set result → loading false).
3. Create `<resource>_tool()` component in `investigation_tools.py` following: ethical reminder card → input + action button → conditional result panel.
4. Add `tab_button("Label", "value", "icon")` and extend `rx.match` list inside `tools_tabs()`.
5. If contributing to graph, call `_add_to_graph` from event.

## Deterministic Mock Data Strategy
- Use `_get_seed(input)` + `random.Random(seed)` for reproducible outputs per input—preserve this for testability & stable UI diffs.
- Where categorization matters (risk levels, breaches, carrier), restrict random choice sets and reuse color semantics (green for safe, red/orange for risk).

## Ethical / Domain Context
- Each tool begins with `ethical_reminder_card` articulating allowed use—maintain this pattern for new intelligence features.
- Risk / score fields capped (e.g. `fraud_score`, `risk_score`) and visually emphasized; treat thresholds consistently (>=70 high risk).

## Developer Workflow
```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run (hot reload)
reflex run  # builds & serves; relies on rxconfig.py (app_name="app")

# (Optional) Export static build
reflex export
```
- No tests yet; verify changes by launching app and exercising tool tabs.
- Tailwind classes are injected via Reflex plugin; avoid manual CSS unless necessary.

## Chart Extensions
- Charts use `rx.recharts.*` primitives with dataset from state. To add a series, append data keys and create matching `rx.recharts.area` / `bar` / `line` component with consistent stroke colors.

## Safety & Extension Guidelines
- Keep current mock isolation until auth + rate limiting are in place.
- External API integration MUST live in a dedicated service module (e.g. `app/services/<api>_client.py`) with: input validation, timeout, error mapping to safe defaults.
- Preserve deterministic seeding for mock fallback paths; wrap live calls with a failover using seeded pseudo data if the API fails.
- Keep new state fields type-annotated with `TypedDict` for structured results.
- NEVER store raw PII beyond what is necessary; hash sensitive identifiers (e.g. email) before long-term persistence if feasible.

## Planned Live Data Integration (Roadmap)
Add only after login + consent flows are implemented:
- Domain WHOIS / DNS: consider `https://api.dev/whoisxml` (WhoisXML API), or `https://rdap.org/` RDAP endpoints (free). Cache results with TTL.
- Breach Data: `https://haveibeenpwned.com/api/v3/breachedaccount/{email}` (requires key, strict rate limits). Use hash of email (k-anonymity via prefix if adopting HIBP range model) before request.
- IP Intelligence: `https://ipinfo.io/{ip}` or `https://api.ipdata.co/{ip}` (geo + ASN). Store minimal subset (ASN, country, threat flags).
- Social Signals: Prefer platform public APIs (GitHub REST, Twitter/X if available) or HTML metadata scraping only where ToS permits—gate behind explicit “research mode”.
- Image / Face: Replace mock recognition with a pluggable module; DO NOT integrate non-compliant facial recognition services without verifying legal use.

Service Pattern Example:
```python
# app/services/ip_client.py
import httpx, random
from .cache import cached

BASE_URL = "https://ipinfo.io"  # or configurable via env

@cached(ttl=3600)
async def fetch_ip(ip: str) -> dict:
  try:
    async with httpx.AsyncClient(timeout=5) as client:
      r = await client.get(f"{BASE_URL}/{ip}?token={API_TOKEN}")
      r.raise_for_status()
      data = r.json()
      return {
        "city": data.get("city"),
        "country": data.get("country"),
        "asn": data.get("org", "").split()[0],
        "isp": data.get("org"),
      }
  except Exception:
    seed = _get_seed(ip)
    rng = random.Random(seed)
    return _mock_ip(ip, rng)
```

## Persistence (MySQL) Guidelines
- Introduce MySQL via environment variables (`DB_URL=mysql+pymysql://user:pass@host/dbname`).
- Leverage existing SQLModel/SQLAlchemy from Reflex: create models in `app/models/` (e.g. `Investigation`, `DomainRecord`, `IpRecord`).
- Use async session factory with scoped lifespan per request/event; never hold sessions in State objects.
- Implement thin repository layer (`app/repositories/*.py`) for CRUD; keep State methods calling repositories, not raw sessions.
- Migration: use native Alembic already installed; create `alembic/` env and autogenerate revisions for new tables.

Minimal Model Example:
```python
# app/models/investigation.py
from sqlmodel import SQLModel, Field
class Investigation(SQLModel, table=True):
  id: int | None = Field(default=None, primary_key=True)
  kind: str  # 'domain' | 'ip' | 'email' | ...
  query: str
  created_at: datetime.datetime
  result_json: str  # store serialized structured result
```

## Authentication & Login Screen
- ✅ IMPLEMENTED: `User` model with Argon2 password hashing.
- ✅ IMPLEMENTED: Login page (`pages/auth.py`) and registration page (`pages/register.py`).
- ✅ IMPLEMENTED: Session via `AuthState.current_user_id`; demo user "admin"/"changeme" auto-created.
- ✅ IMPLEMENTED: Investigation pages gated behind `AuthState.is_authenticated`.
- NEVER expose external API keys to the client; keep them server-side in env.

## API Settings Page
- ✅ IMPLEMENTED: Settings page at `/settings` for managing OSINT API integrations.
- ✅ MODEL: `APIConfig` stores service_name, api_key, base_url, is_enabled, rate_limit, notes.
- ✅ REPOSITORY: `api_config_repository.py` with get_all_configs, create_or_update_config, delete_config.
- ✅ STATE: `SettingsState` manages form fields, validation, CRUD operations.
- ✅ UI: Card-based layout with 7 pre-configured services (WhoisXML, HIBP, IPInfo, Shodan, VirusTotal, Hunter.io, NumVerify).
- Modal form for add/edit with password field for API keys.
- Direct documentation links for each service.
- **TODO**: Encrypt API keys at rest using `cryptography.fernet` before production.

## Improved Network Visualization
- ✅ IMPLEMENTED: Spiderfoot-inspired tree/map view in `components/network_tree.py`.
- `network_tree_view()`: Category-grouped entity display with stats summary.
- `connections_list_view()`: Relationship arrows showing source → label → target.
- Color-coded entity types: blue (domain), green (IP), purple (email), orange (person), indigo (phone), red (breach).
- Icon badges for each entity type with hover effects.
- Empty state guidance for first-time users.
- Replaces old category_section approach with cleaner, more visual layout.

## Refactoring Steps to Introduce Live Features Safely
1. Add auth & user model + login page.
2. Create service modules + caching layer.
3. Add repository + persistence for investigation history.
4. Swap each mock event to: validate → live call → fallback to mock on error → graph update.
5. Add rate limiting (per user & global) before enabling high-volume endpoints.
6. Update instructions removing “mock only” disclaimers when fully migrated.

## Environment & Dependencies (Future Additions)
Add to `requirements.txt` when implementing:
```
PyMySQL==1.1.1  # or mysqlclient if system libs available
argon2-cffi==23.1.0  # password hashing
httpx==0.28.1  # already present via reflex (reuse)
``` 
Keep versions pinned; run `alembic revision --autogenerate -m "init"` after model creation.

## Quick Reference Examples
```python
@rx.event
async def search_domain(self):
    if not self.domain_query: return
    self.is_loading_domain = True; self.domain_result = None; yield
    await asyncio.sleep(1.0)
    # deterministic mock
    seed = self._get_seed(self.domain_query)
    rng = random.Random(seed)
    ...
    self.is_loading_domain = False
```
```python
rx.cond(InvestigationState.domain_result, result_panel())
rx.foreach(InvestigationState.social_results, social_card)
```

## When Unsure
- Mirror closest existing tool structure for new features before large abstractions.
- Confirm compliance: validate API ToS & legal boundaries prior to enabling new feeds.
- Ask to clarify if introducing persistence, auth, or real OSINT data feeds.

---
Feedback welcome: Identify unclear workflow steps, missing patterns, or needed test guidance.
