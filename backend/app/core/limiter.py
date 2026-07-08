"""
app/core/limiter.py

Shared slowapi limiter instance. Defined in its own module to avoid circular
imports - route files need to decorate endpoints with @limiter.limit(...),
but main.py imports route files, so the limiter can't live in main.py.

Rate limit conventions:
    100/minute - dashboard read endpoints (frequent polls expected)
     60/minute - manual writes (single-user actions like ad-hoc predictions)
     30/minute - sensitive writes (alert creation, routing rule edits)

Intentionally NOT rate-limited:
    POST /metrics       - scapy publishes at 20-50/sec, would saturate any limit
    GET /health/*       - health checks should never be throttled
    GET /metrics/prometheus - scrapers need consistent access
    WebSocket endpoints - slowapi is REST-only
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
