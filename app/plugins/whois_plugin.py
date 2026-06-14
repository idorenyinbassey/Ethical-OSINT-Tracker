from app.plugins.base import BasePlugin


class WhoisPlugin(BasePlugin):
    name = "whois"
    label = "WHOIS / RDAP Lookup"
    description = "Look up domain registration details using the public RDAP network. No API key required."
    input_label = "Domain"
    input_placeholder = "example.com"
    category = "Network"

    def run(self, query: str) -> dict:
        from app.services.rdap_client import fetch_domain
        domain = query.strip().lower().removeprefix("http://").removeprefix("https://").split("/")[0]
        data = fetch_domain(domain)
        if data is None:
            return {"error": f"No RDAP data found for {domain}. The domain may not exist or the registry does not support RDAP."}
        return {"result": data, "domain": domain}
