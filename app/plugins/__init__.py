"""Plugin registry — auto-discovers BasePlugin subclasses."""
from typing import Dict
from app.plugins.base import BasePlugin

_registry: Dict[str, BasePlugin] = {}


def register(cls):
    """Class decorator — adds plugin to the registry."""
    instance = cls()
    _registry[instance.name] = instance
    return cls


def get_all():
    return list(_registry.values())


def get_plugin(name: str):
    return _registry.get(name)


def _autodiscover():
    """Import all built-in plugins and register their classes."""
    from app.plugins import whois_plugin, dns_plugin, hash_plugin  # noqa: F401
    for cls in (
        whois_plugin.WhoisPlugin,
        dns_plugin.DNSPlugin,
        hash_plugin.HashPlugin,
    ):
        instance = cls()
        _registry[instance.name] = instance


_autodiscover()
