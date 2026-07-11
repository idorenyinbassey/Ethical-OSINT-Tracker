"""Validation utilities for user input and configuration."""
from urllib.parse import urlparse
from ipaddress import ip_address


def validate_base_url(url: str) -> tuple[bool, str]:
    """Validate base URL for API configuration.

    Rejects URLs pointing to private IP ranges (RFC 1918, loopback, link-local)
    to prevent SSRF attacks.

    Args:
        url: URL string to validate

    Returns:
        (is_valid, error_message) tuple
            - (True, "") if URL is valid
            - (False, error_message) if URL is invalid
    """
    if not url:
        return True, ""  # Empty URL is valid (use default)

    if not url.startswith(("http://", "https://")):
        return False, "URL must start with http:// or https://"

    try:
        parsed = urlparse(url)
        if not parsed.hostname:
            return False, "URL must include a hostname"

        try:
            # Try to parse as IP address. Note: ip_address() raises a plain
            # ValueError (not AddressValueError) for non-IP strings such as
            # hostnames, so we must catch ValueError here.
            ip_obj = ip_address(parsed.hostname)
            # Reject private IP ranges
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                return False, (
                    f"Cannot use private IP address {ip_obj}. "
                    "URLs must point to public services (SSRF prevention)."
                )
        except ValueError:
            # It's a hostname, not an IP - check against known problematic names
            hostname_lower = parsed.hostname.lower()
            blocked_hosts = {
                "localhost", "127.0.0.1", "::1", "0.0.0.0",
                "169.254.169.254",  # AWS metadata
                "metadata.google.internal",  # GCP metadata
            }
            if hostname_lower in blocked_hosts:
                return False, (
                    f"Cannot use reserved hostname {parsed.hostname}. "
                    "URLs must point to public services (SSRF prevention)."
                )

        return True, ""

    except Exception as e:
        return False, f"Invalid URL: {str(e)}"
