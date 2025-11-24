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
3. You will see two sections:
    - **Configured Services**: APIs you have already set up.
    - **Available Services**: Pre-configured templates for supported APIs.

4. In the **Available Services** section, find the service you want to enable and click **Configure**.

5. A modal form will appear. Fill in the details:
    - **API Key**: Paste the key you copied. This is a sensitive field and will be displayed as a password input.
    - **Base URL**: This is usually pre-filled. Only change it if you are using a proxy or have a custom enterprise endpoint.
    - **Rate Limit (per hour)**: Set a limit to avoid exceeding your plan's quota. The default is `100`.
    - **Notes**: Add any relevant information, like the renewal date or plan type.
    - **Enabled**: Ensure this switch is turned on.

6. Click **Save Configuration**.

The service will now appear in the **Configured Services** list. The application will automatically start using this service for relevant investigations.

### Step 3: Verify Integration

1. Go to the **Investigate** page.
2. Use a tool that relies on the service you just configured (e.g., use the **IP Address** tool after configuring IPInfo.io).
3. The results should now reflect live data instead of mock data.

## Managing Configurations

From the **Settings** page, you can:

- **Edit a Configuration**: Click the **pencil icon** on a configured service to update its API key, rate limit, or other details.
- **Delete a Configuration**: Click the **trash icon** to remove a service. The application will revert to using mock data for that service.
- **Disable a Service**: Edit a configuration and toggle the **Enabled** switch off. This keeps the configuration saved but temporarily stops the app from using it.

## Adding a New Service (For Developers)

If you want to integrate a service not listed, follow these steps:

### 1. Create a Service Client

- Create a new file in `app/services/`, for example, `app/services/new_api_client.py`.
- Implement an `async` function to fetch data from the new API using `httpx`.
- Include error handling and a fallback to mock data.
- Use the `@cached` decorator from `app/services/cache.py` to cache responses.

**Example Template (`new_api_client.py`):**
```python
import httpx
import random
from app.services.cache import cached
from app.repositories.api_config_repository import get_config

# Helper to generate mock data
def _get_mock_data(input_str: str) -> dict:
    # ... your mock data logic ...
    return {"data": f"mock for {input_str}"}

@cached(ttl=3600)
async def fetch_new_data(input_str: str) -> dict:
    """Fetches data from the new API service."""
    config = get_config("NewAPI") # Match the key in API_SERVICES
    if not config or not config.get("is_enabled") or not config.get("api_key"):
        return _get_mock_data(input_str)

    api_key = config["api_key"]
    base_url = config["base_url"]
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{base_url}/endpoint?query={input_str}&apiKey={api_key}")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"NewAPI Error: {e}")
        return _get_mock_data(input_str)
```

### 2. Add to Service Templates

- Open `app/states/settings_state.py`.
- Add a new entry to the `API_SERVICES` dictionary.

```python
API_SERVICES = {
    # ... existing services ...
    "NewAPI": {
        "name": "New Awesome API",
        "default_url": "https://api.newawesome.com/v1",
        "description": "Provides new awesome data.",
        "docs_url": "https://newawesome.com/docs",
    },
}
```
The key (`"NewAPI"`) must match the one used in `get_config()` in your service client.

### 3. Integrate into Investigation State

- Open `app/states/investigation_state.py`.
- Import your new service client function (`from app.services.new_api_client import fetch_new_data`).
- In the relevant investigation event handler (or a new one), call your function.

```python
class InvestigationState(rx.State):
    # ... other state vars ...
    new_api_result: Optional[dict] = None
    is_loading_new_api: bool = False

    @rx.event
    async def search_new_api(self, query: str):
        self.is_loading_new_api = True
        yield
        
        self.new_api_result = await fetch_new_data(query)
        
        self.is_loading_new_api = False
```

### 4. Create the UI

- Create a new tool component in `app/components/investigation_tools.py` to display the input form and results for your new tool.
- Add the new tool to the tabs in `app/pages/investigation.py`.

## Security Note

- **Never hardcode API keys.** Always load them from the database via the `SettingsState` and `api_config_repository`.
- **API keys are stored encrypted** in the database if `ENCRYPT_API_KEYS=true` is set in your `.env` file (recommended for production).
- The application is designed to prevent API keys from ever being exposed to the client-side frontend.
