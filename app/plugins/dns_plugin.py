import socket
from app.plugins.base import BasePlugin


class DNSPlugin(BasePlugin):
    name = "dns"
    label = "DNS Resolver"
    description = "Resolve a hostname to its IP address(es) and perform a reverse lookup."
    input_label = "Hostname or IP"
    input_placeholder = "hostname.example.com"
    category = "Network"

    def run(self, query: str) -> dict:
        query = query.strip()
        result = {"query": query, "forward": [], "reverse": None}
        try:
            infos = socket.getaddrinfo(query, None)
            ips = list({info[4][0] for info in infos})
            result["forward"] = ips
        except socket.gaierror as e:
            result["error"] = str(e)
            return result
        if result["forward"]:
            try:
                result["reverse"] = socket.gethostbyaddr(result["forward"][0])[0]
            except socket.herror:
                result["reverse"] = None
        return result
