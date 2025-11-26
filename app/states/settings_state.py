import reflex as rx
from typing import TypedDict
from app.repositories.api_config_repository import get_all_configs, create_or_update_config, delete_config


class APIConfigItem(TypedDict):
    service_name: str
    api_key: str
    base_url: str
    is_enabled: bool
    rate_limit: int
    notes: str


# Default API service templates
API_SERVICES = {
    "WhoisXML": {
        "name": "WhoisXML API",
        "default_url": "https://www.whoisxmlapi.com/whoisserver/WhoisService",
        "description": "Domain WHOIS and DNS lookup",
        "docs_url": "https://whoisxmlapi.com/documentation",
    },
    "HIBP": {
        "name": "Have I Been Pwned",
        "default_url": "https://haveibeenpwned.com/api/v3",
        "description": "Email breach database",
        "docs_url": "https://haveibeenpwned.com/API/v3",
    },
    "IPInfo": {
        "name": "IPInfo.io",
        "default_url": "https://ipinfo.io",
        "description": "IP geolocation and ASN data",
        "docs_url": "https://ipinfo.io/developers",
    },
    "Shodan": {
        "name": "Shodan",
        "default_url": "https://api.shodan.io",
        "description": "Internet-connected device search",
        "docs_url": "https://developer.shodan.io/api",
    },
    "VirusTotal": {
        "name": "VirusTotal",
        "default_url": "https://www.virustotal.com/api/v3",
        "description": "File and URL threat analysis",
        "docs_url": "https://developers.virustotal.com/reference/overview",
    },
    "Hunter.io": {
        "name": "Hunter.io",
        "default_url": "https://api.hunter.io/v2",
        "description": "Email finder and verifier",
        "docs_url": "https://hunter.io/api-documentation",
    },
    "NumVerify": {
        "name": "NumVerify",
        "default_url": "http://apilayer.net/api",
        "description": "Phone number validation",
        "docs_url": "https://numverify.com/documentation",
    },
}

# Supported service keys (use Option B: allow custom names with a warning)
SUPPORTED_API_SERVICE_KEYS = [
    "WhoisXML",
    "HIBP",
    "IPInfo",
    "Shodan",
    "VirusTotal",
    "Hunter.io",
    "NumVerify",
    "ImageRecognition",
    "IMEIService",
    "SocialSearch",
]

# Additional example templates for image, imei and social services
API_SERVICES.update(
    {
        "ImageRecognition": {
            "name": "Google Cloud Vision AI",
            "default_url": "https://vision.googleapis.com/v1",
            "description": "Image analysis, face detection, OCR, and label detection via Google Cloud",
            "docs_url": "https://cloud.google.com/vision/docs",
            "free_key_notes": "Get your API key from Google Cloud Console. Free tier: 1000 requests/month.",
        },
        "IMEIService": {
            "name": "IMEI.info (example)",
            "default_url": "https://api.imei.info",
            "description": "IMEI / device lookup (example provider)",
            "docs_url": "https://imei.info/docs",
            "free_key_notes": "Some IMEI services provide limited free lookups or demo keys; check provider docs.",
        },
        "SocialSearch": {
            "name": "Multi-Platform Social OSINT",
            "default_url": "https://api.github.com",
            "description": "Multi-platform social media OSINT (GitHub, Twitter, Facebook, Telegram, TikTok). Configure per-platform API keys in Notes field using JSON format.",
            "docs_url": "https://docs.github.com/en/rest",
            "free_key_notes": "Store per-platform keys in Notes field as JSON: {\"github\": \"ghp_xxx\", \"twitter\": \"bearer_xxx\", \"facebook\": \"xxx\", \"telegram\": \"bot_xxx\", \"tiktok\": \"xxx\"}. Falls back to HTTP checks when keys not provided. GitHub: 5000 req/hr (authenticated). Twitter: varies by endpoint. Follow each platform's ToS.",
            "required_fields": ["notes_json"],
        },
    }
)


class SettingsState(rx.State):
    # API Configuration
    api_configs: list[APIConfigItem] = []
    selected_service: str = ""
    
    # Form fields
    form_service_name: str = ""
    form_api_key: str = ""
    form_base_url: str = ""
    form_is_enabled: bool = True
    form_rate_limit: int = 100
    form_notes: str = ""
    # Provider-specific credential fields (e.g., client_id, client_secret)
    form_credentials: dict = {}
    
    # UI state
    is_loading: bool = False
    save_success: bool = False
    save_error: str = ""
    show_add_form: bool = False
    is_testing_api: bool = False
    api_test_result: str = ""

    def set_form_api_key(self, value: str):
        self.form_api_key = value

    def set_form_base_url(self, value: str):
        self.form_base_url = value

    def set_form_credential(self, key: str, value: str):
        creds = dict(self.form_credentials or {})
        creds[key] = value
        self.form_credentials = creds

    def set_form_rate_limit(self, value: int):
        self.form_rate_limit = value

    def set_form_notes(self, value: str):
        self.form_notes = value

    def set_form_is_enabled(self, value: bool):
        self.form_is_enabled = value
    
    @rx.var
    def api_key_validation_message(self) -> str:
        """Real-time validation message for API key input."""
        if not self.form_api_key:
            return ""
        
        # Only validate Google Cloud Vision API keys
        if self.selected_service == "ImageRecognition":
            from app.services.image_client import validate_google_vision_key
            is_valid, error_msg = validate_google_vision_key(self.form_api_key)
            
            if is_valid:
                return "✅ Valid Google Cloud API key format"
            else:
                return f"⚠️ {error_msg}"
        
        # For other services, just show key length
        if len(self.form_api_key) > 0:
            return f"ℹ️ Key length: {len(self.form_api_key)} characters"
        
        return ""
    
    @rx.event
    def load_configs(self):
        """Load all API configurations"""
        try:
            configs = get_all_configs()
            self.api_configs = [
                {
                    "service_name": c.service_name,
                    "api_key": c.api_key,
                    "base_url": c.base_url,
                    "is_enabled": c.is_enabled,
                    "rate_limit": c.rate_limit,
                    "notes": c.notes,
                }
                for c in configs
            ]
        except Exception:
            self.api_configs = []
    
    @rx.event
    def select_service(self, service_key: str):
        """Select a service to configure"""
        self.selected_service = service_key
        service_info = API_SERVICES.get(service_key, {})
        self.form_service_name = service_key
        self.form_base_url = service_info.get("default_url", "")
        # If the template provides notes about free keys, pre-fill the notes field
        self.form_notes = service_info.get("free_key_notes", "")
        self.form_is_enabled = True
        self.form_rate_limit = 100
        self.form_api_key = ""
        # Prepare credentials template if provider defines required fields
        required = service_info.get("required_fields", [])
        creds = {k: "" for k in required}
        self.form_credentials = creds
        self.show_add_form = True
        self.save_success = False
        self.save_error = ""
    
    @rx.event
    def edit_config(self, service_name: str):
        """Edit existing configuration"""
        config = next((c for c in self.api_configs if c["service_name"] == service_name), None)
        if config:
            self.selected_service = service_name
            self.form_service_name = config["service_name"]
            self.form_api_key = config["api_key"]
            self.form_base_url = config["base_url"]
            self.form_is_enabled = config["is_enabled"]
            self.form_rate_limit = config["rate_limit"]
            self.form_notes = config["notes"]
            # load parsed credentials if present
            self.form_credentials = getattr(config, "_credentials", {})
            self.show_add_form = True
            self.save_success = False
            self.save_error = ""
    
    @rx.event
    async def save_config(self):
        """Save API configuration"""
        if not self.form_service_name or not self.form_api_key or not self.form_base_url:
            self.save_error = "Service name, API key, and base URL are required"
            yield
            return
        
        self.is_loading = True
        self.save_error = ""
        self.save_success = False
        yield
        
        try:
            create_or_update_config(
                service_name=self.form_service_name,
                api_key=self.form_api_key,
                base_url=self.form_base_url,
                is_enabled=self.form_is_enabled,
                rate_limit=self.form_rate_limit,
                notes=self.form_notes,
                credentials=self.form_credentials,
            )
            self.save_success = True
            self.show_add_form = False
            self.load_configs()
            # If the user saved a custom/unsupported service name, warn but allow it
            if self.form_service_name not in SUPPORTED_API_SERVICE_KEYS:
                yield rx.toast.warning(
                    f"Saved custom service '{self.form_service_name}'. Consider using a supported key or check docs."
                )
            else:
                yield rx.toast.success(f"API configuration for {self.form_service_name} saved successfully")
            # Final yield to ensure updated list renders
            yield
        except Exception as e:
            self.save_error = str(e)
            yield rx.toast.error("Failed to save configuration")
        finally:
            self.is_loading = False
    
    @rx.event
    def delete_config_action(self, service_name: str):
        """Delete API configuration"""
        try:
            delete_config(service_name)
            self.load_configs()
            yield rx.toast.success(f"API configuration for {service_name} deleted")
        except Exception:
            yield rx.toast.error("Failed to delete configuration")
    
    @rx.event
    async def test_api_connection(self):
        """Test Google Vision API connection with current key."""
        self.is_testing_api = True
        self.api_test_result = ""
        yield
        
        # Only test ImageRecognition service
        if self.selected_service != "ImageRecognition":
            self.api_test_result = "⚠️ API testing only available for Google Cloud Vision AI"
            self.is_testing_api = False
            return
        
        # Get the API key from form or existing config
        api_key = self.form_api_key.strip() if self.form_api_key else None
        
        if not api_key:
            # Try to get from existing config
            from app.repositories.api_config_repository import get_by_service
            cfg = get_by_service("ImageRecognition")
            if cfg and cfg.api_key:
                api_key = cfg.api_key
            else:
                self.api_test_result = "❌ No API key provided"
                self.is_testing_api = False
                return
        
        # Validate format first
        from app.services.image_client import validate_google_vision_key
        is_valid, error_msg = validate_google_vision_key(api_key)
        if not is_valid:
            self.api_test_result = f"❌ Invalid Key Format: {error_msg}"
            self.is_testing_api = False
            return
        
        # Test with minimal request
        try:
            import httpx
            import base64
            
            async with httpx.AsyncClient(timeout=10) as client:
                # Use a tiny 1x1 pixel test image
                # 1x1 red pixel PNG
                test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
                
                request_body = {
                    "requests": [{
                        "image": {"content": test_image},
                        "features": [{"type": "LABEL_DETECTION", "maxResults": 1}]
                    }]
                }
                
                endpoint = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
                headers = {"Content-Type": "application/json"}
                
                response = await client.post(endpoint, headers=headers, json=request_body)
                response.raise_for_status()
                
                self.api_test_result = "✅ Connection Successful! API key is valid and working."
                yield rx.toast.success("API connection test passed!")
                
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401:
                self.api_test_result = "❌ Invalid API Key (401): Key is not recognized by Google Cloud"
            elif status == 403:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get("error", {}).get("message", "")
                    if "billing" in error_message.lower():
                        self.api_test_result = "⚠️ Billing Not Enabled (403): API key is valid but billing must be enabled in Google Cloud Console"
                    else:
                        self.api_test_result = f"❌ Access Denied (403): {error_message[:100]}"
                except:
                    self.api_test_result = "❌ Access Denied (403): API not enabled or quota exceeded"
            elif status == 429:
                self.api_test_result = "⚠️ Rate Limit Exceeded (429): Too many requests. Try again later."
            else:
                self.api_test_result = f"❌ HTTP Error {status}"
                
        except httpx.RequestError as e:
            self.api_test_result = f"❌ Network Error: {str(e)[:100]}"
        except Exception as e:
            self.api_test_result = f"❌ Error: {str(e)[:100]}"
        
        self.is_testing_api = False
    
    @rx.event
    def cancel_form(self):
        """Cancel form editing"""
        self.show_add_form = False
        self.save_success = False
        self.save_error = ""
        self.api_test_result = ""
        self.form_service_name = ""
        self.form_api_key = ""
        self.form_base_url = ""
        self.form_notes = ""
