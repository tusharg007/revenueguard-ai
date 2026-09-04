"""Shared Redis client construction with a portable TLS trust store."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

import certifi
import redis.asyncio as redis


def create_redis_client(url: str, **kwargs: Any):
    """Create a Redis client and use Certifi for TLS endpoints."""
    if urlsplit(url).scheme.lower() == "rediss":
        kwargs.setdefault("ssl_ca_certs", certifi.where())
    return redis.from_url(url, **kwargs)
