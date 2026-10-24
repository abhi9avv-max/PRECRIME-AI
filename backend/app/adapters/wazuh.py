"""Wazuh SIEM integration adapter (read-only, minimal connection tester).

Env vars only:
- WAZUH_API_URL
- WAZUH_API_USER
- WAZUH_API_PASSWORD
- WAZUH_VERIFY_TLS (default true)
Never hardcodes or logs secrets.
"""
import os
from typing import Dict, Any, Tuple
import httpx

def get_wazuh_config() -> Tuple[str, str, str, bool]:
    url = os.getenv("WAZUH_API_URL", "").rstrip("/")
    user = os.getenv("WAZUH_API_USER", "")
    password = os.getenv("WAZUH_API_PASSWORD", "")
    verify_tls = os.getenv("WAZUH_VERIFY_TLS", "true").lower() in ("true", "1", "yes")
    return url, user, password, verify_tls

def test_wazuh_connection() -> Dict[str, Any]:
    """Perform real authentication against the configured Wazuh API endpoint."""
    url, user, password, verify_tls = get_wazuh_config()

    if not url or not user or not password:
        missing = []
        if not url: missing.append("WAZUH_API_URL")
        if not user: missing.append("WAZUH_API_USER")
        if not password: missing.append("WAZUH_API_PASSWORD")
        return {
            "connected": False,
            "message": f"Wazuh connection not configured. Missing environment variables: {', '.join(missing)}.",
        }

    token_endpoint = f"{url}/security/user/authenticate"
    try:
        # Wazuh uses basic auth on security/user/authenticate to obtain a JWT token
        with httpx.Client(verify=verify_tls, timeout=5.0) as client:
            resp = client.post(token_endpoint, auth=(user, password))
            if resp.status_code == 200:
                return {
                    "connected": True,
                    "message": f"Successfully authenticated with Wazuh API at {url}.",
                }
            elif resp.status_code in (401, 403):
                return {
                    "connected": False,
                    "message": f"Authentication failed (HTTP {resp.status_code}). Invalid Wazuh API credentials.",
                }
            else:
                return {
                    "connected": False,
                    "message": f"Wazuh endpoint responded with HTTP {resp.status_code}: {resp.text[:120]}.",
                }
    except httpx.ConnectTimeout:
        return {"connected": False, "message": f"Connection timed out reaching Wazuh endpoint {url}."}
    except httpx.ConnectError as e:
        return {"connected": False, "message": f"Connection error reaching Wazuh server: {str(e)}."}
    except Exception as e:
        err_msg = str(e)
        if "CERTIFICATE_VERIFY_FAILED" in err_msg or "SSLCertVerificationError" in err_msg:
            return {
                "connected": False,
                "message": f"TLS certificate verification failed for {url}. To permit self-signed certificates, set WAZUH_VERIFY_TLS=false.",
            }
        return {"connected": False, "message": f"Failed to connect to Wazuh: {err_msg}."}
