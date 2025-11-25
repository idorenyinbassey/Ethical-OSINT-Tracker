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
            "name": "DeepAI Image Recognition (example)",
            "default_url": "https://api.deepai.org/api",
            "description": "Image analysis and reverse image search (example provider)",
            "docs_url": "https://deepai.org",
            "free_key_notes": "DeepAI offers a free-tier API key for testing; replace with your provider key.",
        },
        "IMEIService": {
            "name": "IMEI.info (example)",
            "default_url": "https://api.imei.info",
            "description": "IMEI / device lookup (example provider)",
            "docs_url": "https://imei.info/docs",
            "free_key_notes": "Some IMEI services provide limited free lookups or demo keys; check provider docs.",
        },
        "SocialSearch": {
            "name": "SocialSearch (GitHub/Reddit example)",
            "default_url": "https://api.github.com",
            "description": "Social profile and public post lookups (example providers)",
            "docs_url": "https://docs.github.com",
            "free_key_notes": "Use platform public APIs (GitHub, Reddit) or aggregator services; follow each ToS.",
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
    
    # UI state
    is_loading: bool = False
    save_success: bool = False
    save_error: str = ""
    show_add_form: bool = False

    def set_form_api_key(self, value: str):
        self.form_api_key = value

    def set_form_base_url(self, value: str):
        self.form_base_url = value

    def set_form_rate_limit(self, value: int):
        self.form_rate_limit = value

    def set_form_notes(self, value: str):
        self.form_notes = value

    def set_form_is_enabled(self, value: bool):
        self.form_is_enabled = value
    
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
        self.form_is_enabled = True
        self.form_rate_limit = 100
        self.form_notes = ""
        self.form_api_key = ""
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
    def cancel_form(self):
        """Cancel form editing"""
        self.show_add_form = False
        self.save_success = False
        self.save_error = ""
        self.form_service_name = ""
        self.form_api_key = ""
        self.form_base_url = ""
        self.form_notes = ""
