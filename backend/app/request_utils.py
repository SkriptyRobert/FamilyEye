"""Shared request helpers (e.g. client IP) used by middleware, auth, pairing."""
import os
from starlette.requests import Request


def get_client_ip(request: Request) -> str:
    """Client IP. Use X-Forwarded-For only when TRUST_PROXY=1 (behind nginx etc.)."""
    trust_proxy = os.environ.get("TRUST_PROXY", "").lower() in ("1", "true", "yes")
    if trust_proxy:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
