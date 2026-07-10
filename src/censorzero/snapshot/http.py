"""Shared HTTP layer for the one-time snapshot collection.

Politeness rules: bounded per-host concurrency, retry with exponential
backoff on 429/5xx/timeouts, a single shared client per run, and an explicit
per-URL outcome record (no silent drops — v1 lost Jan–Feb 2024 to a silent
`continue`).
"""

import asyncio
import random
from dataclasses import dataclass

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4
BACKOFF_BASE = 2.0  # seconds; attempt n sleeps BACKOFF_BASE * 2**(n-1)


@dataclass
class FetchResult:
    url: str
    status: int | None  # HTTP status, or None on transport error
    final_url: str | None
    text: str | None
    error: str | None
    attempts: int


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8",
        },
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, connect=15.0),
        limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
    )


async def fetch(client: httpx.AsyncClient, sem: asyncio.Semaphore, url: str) -> FetchResult:
    last_error = None
    status = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            async with sem:
                resp = await client.get(url)
            status = resp.status_code
            if status in RETRYABLE_STATUS:
                last_error = f"http {status}"
            else:
                return FetchResult(url, status, str(resp.url), resp.text, None, attempt)
        except httpx.HTTPError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        # jittered backoff (jitter affects pacing only, never data)
        await asyncio.sleep(BACKOFF_BASE * 2 ** (attempt - 1) * (0.5 + random.random()))
    return FetchResult(url, status, None, None, last_error, MAX_ATTEMPTS)
