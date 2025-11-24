"""Helpers for hashing sensitive identifiers before persistence."""
import hashlib


def hash_identifier(value: str) -> str:
    """Hash sensitive identifier (email, phone) using SHA256."""
    return hashlib.sha256(value.encode()).hexdigest()


def hash_if_sensitive(kind: str, query: str) -> str:
    """
    Hash query if it's a sensitive resource type.
    
    Args:
        kind: Type of investigation (email, phone, etc.)
        query: User input query
    
    Returns:
        Hashed or original query based on kind
    """
    sensitive_kinds = {"email", "phone"}
    if kind in sensitive_kinds:
        return hash_identifier(query)
    return query
