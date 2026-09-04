"""Shared Redis client construction with a portable TLS trust store."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlsplit

import certifi
import redis.asyncio as redis


def create_redis_client(url: str, **kwargs: Any):
    """Create a Redis client and use Certifi for TLS endpoints."""
    if urlsplit(url).scheme.lower() == "rediss":
        kwargs.setdefault("ssl_ca_certs", certifi.where())
    return redis.from_url(url, **kwargs)


async def enqueue_recovery_case(
    redis_client: Any | None, case_id: str, attempts: int = 3
) -> bool:
    """Enqueue a recovery case with bounded retries for transient network errors."""
    if redis_client is None:
        return False
    for attempt in range(attempts):
        try:
            await redis_client.lpush("recovery_queue", case_id)
            return True
        except Exception:
            if attempt == attempts - 1:
                return False
            await asyncio.sleep(0.1 * (2**attempt))
    return False
