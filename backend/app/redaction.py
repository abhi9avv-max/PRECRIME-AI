"""Secret redaction utility for telemetry payloads."""
from typing import Any, Dict, List

REDACT_KEYS = {"password", "token", "secret", "api_key", "authorization", "auth_token", "access_token"}

def redact_payload(payload: Any) -> Any:
    """Recursively redacts values for sensitive keys in dictionaries or lists."""
    if isinstance(payload, dict):
        redacted = {}
        for k, v in payload.items():
            if any(s in k.lower() for s in REDACT_KEYS):
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = redact_payload(v)
        return redacted
    elif isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    return payload
