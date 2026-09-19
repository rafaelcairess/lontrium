"""Small privacy helpers that do not import the browser automation stack."""

from __future__ import annotations


def mask_account(name) -> str:
    """Mask an e-mail address while leaving non-email account labels readable."""
    text = str(name or "")
    local, at, domain = text.partition("@")
    if not at:
        return text
    return f"{local[:1]}***@{domain}"
