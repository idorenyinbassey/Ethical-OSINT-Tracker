import hashlib
from app.plugins.base import BasePlugin


class HashPlugin(BasePlugin):
    name = "hash"
    label = "Hash Generator"
    description = "Compute MD5, SHA-1, SHA-256 and SHA-512 hashes of any input — useful for evidence integrity checking."
    input_label = "Text or hex value"
    input_placeholder = "Enter text to hash"
    category = "Forensics"

    def run(self, query: str) -> dict:
        data = query.encode("utf-8")
        return {
            "query": query,
            "md5":    hashlib.md5(data).hexdigest(),
            "sha1":   hashlib.sha1(data).hexdigest(),
            "sha256": hashlib.sha256(data).hexdigest(),
            "sha512": hashlib.sha512(data).hexdigest(),
        }
