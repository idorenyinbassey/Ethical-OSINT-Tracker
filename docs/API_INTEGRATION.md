# API Integration Guide

This guide explains how to configure and use external OSINT API services within the Ethical OSINT Tracker.

## Supported Services

The application is pre-configured to support the following services. Most offer a generous free tier suitable for personal or small-team use.

| Service | Purpose | Default URL | Docs Link |
|---|---|---|---|
| **WhoisXML API** | Domain WHOIS & DNS | `https://www.whoisxmlapi.com/...` | [Docs](https://whoisxmlapi.com/documentation) |
| **Have I Been Pwned** | Email Breach Database | `https://haveibeenpwned.com/api/v3` | [Docs](https://haveibeenpwned.com/API/v3) |
| **IPInfo.io** | IP Geolocation & ASN | `https://ipinfo.io` | [Docs](https://ipinfo.io/developers) |
| **Shodan** | Device Search Engine | `https://api.shodan.io` | [Docs](https://developer.shodan.io/api) |
| **VirusTotal** | Threat Analysis | `https://www.virustotal.com/api/v3` | [Docs](https://developers.virustotal.com/reference/overview) |
| **Hunter.io** | Email Finder/Verifier | `https://api.hunter.io/v2` | [Docs](https://hunter.io/api-documentation) |
| **NumVerify** | Phone Number Validation | `http://apilayer.net/api` | [Docs](https://numverify.com/documentation) |

## Configuration Modes

### 1. Mock Mode (Default)

- **No API keys required.**
- The application runs in a fully functional mock mode out-of-the-box.
- All API calls are simulated, returning deterministic, plausible data based on the input.
- This is ideal for demos, testing, training, or offline use.

### 2. Live Mode

- **Requires API keys.**
- Connects to external services to fetch real-time data.
- Subject to the rate limits and terms of service of each API provider.
- Caching is enabled to minimize redundant requests.

## How to Enable Live Mode

### Step 1: Obtain API Keys

1. For each service you want to use, click the **Docs** link in the table above or on the **Settings** page in the app.
2. Register for a free account on the service provider's website.
3. Navigate to your account dashboard or API section to find your API key.
4. Copy the API key.

### Step 2: Configure in the App

1. Log in to the Ethical OSINT Tracker.
2. Navigate to the **Settings** page from the sidebar.
3. Find the service card for the API you want to configure.
4. Fill in the fields:
    - **API Key**: Paste the key you copied.
    - **Base URL**: Pre-filled with the correct default. Only change for custom endpoints.
    - **Enabled**: Toggle on.
5. Click **Save**.

The service will now appear in the **Configured Services** list. The application will automatically start using this service for relevant investigations.

### Step 3: Verify Integration

1. Go to the **Investigate** page.
2. Use a tool that relies on the service you just configured (e.g., use the **IP Address** tool after configuring IPInfo.io).
3. The results should now reflect live data instead of mock data.

## Managing Configurations

From the **Settings** page, you can:

- **Update a Configuration**: Change the API Key or Base URL in the service card and click **Save**.
- **Disable a Service**: Uncheck **Enabled** and click **Save**. The configuration stays saved but the app stops using it.

## Adding a New Service (For Developers)

If you want to integrate a service not listed, follow these steps:

### 1. Create a Service Client

- Create a new file in `app/services/`, for example, `app/services/new_api_client.py`.
- Implement a **synchronous** function to fetch data from the new API using `httpx.Client`.
- Include error handling and a fallback to mock data.
- Use the `@cached` decorator from `app/services/cache.py` to cache responses.

**Example Template (`new_api_client.py`):**
```python
import httpx
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service

def _get_mock_data(input_str: str) -> dict:
    return {"data": f"mock for {input_str}"}

@cached(ttl=3600)
def fetch_new_data(input_str: str) -> dict:
    cfg = get_by_service("NewAPI")
    if not cfg or not cfg.is_enabled or not cfg.api_key:
        return _get_mock_data(input_str)
    try:
        with httpx.Client(timeout=8) as client:
            response = client.get(f"{cfg.base_url}/endpoint",
                                  params={"q": input_str, "key": cfg.api_key})
            response.raise_for_status()
            return response.json()
    except Exception:
        return _get_mock_data(input_str)
```

### 2. Add to Service Templates

- Open `app/routes/settings.py`.
- Add the new service name to the `SERVICES` list:

```python
SERVICES = [
    # ... existing services ...
    "NewAPI",
]
```
The string must match the `service_name` value used by `get_by_service()` in your client.

### 3. Add a Route

- Open `app/routes/investigation.py`.
- Import your client and add a route:

```python
from app.services.new_api_client import fetch_new_data

@investigation_bp.route("/newapi", methods=["GET", "POST"])
@login_required
def newapi():
    result = None
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        result = fetch_new_data(query)
        create_investigation(kind="newapi", query=query,
                             result_json=json.dumps(result or {}),
                             user_id=current_user.id)
    return render_template("investigation/newapi.html",
                           result=result, cases=list_cases())
```

### 4. Create the UI

- Create `app/templates/investigation/newapi.html` extending `base.html` with a form and results panel.
- Add a sidebar link in `app/templates/base.html`.

## Security Note

- **Never hardcode API keys.** Always load them from the database via `get_by_service()` in `app/repositories/api_config_repository.py`.
- **API keys are stored encrypted** in the database if `ENCRYPT_API_KEYS=true` is set in your `.env` file (recommended for production).
- The application is designed to prevent API keys from ever being exposed to the client-side frontend.
