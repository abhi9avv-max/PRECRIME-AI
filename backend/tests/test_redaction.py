"""Unit tests for secret redaction utility."""
from app.redaction import redact_payload

def test_redact_sensitive_keys():
    raw = {
        "user": "analyst1",
        "api_key": "super-secret-123",
        "nested": {
            "password": "mypassword",
            "auth_token": "token-abc",
            "normal": "value",
        },
        "list": [
            {"token": "xyz", "safe": 123}
        ]
    }
    redacted = redact_payload(raw)
    assert redacted["user"] == "analyst1"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["nested"]["auth_token"] == "[REDACTED]"
    assert redacted["nested"]["normal"] == "value"
    assert redacted["list"][0]["token"] == "[REDACTED]"
    assert redacted["list"][0]["safe"] == 123
