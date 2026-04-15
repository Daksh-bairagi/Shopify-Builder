import asyncio
import functools
from typing import Callable

import httpx


_DELAYS = [1, 2, 4]  # seconds between attempts 1→2, 2→3, 3→raise
_RETRYABLE_STATUSES = {429, 503}


def async_retry(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        last_exc: Exception | None = None
        for attempt, delay in enumerate([0] + _DELAYS):
            if delay:
                await asyncio.sleep(delay)
            try:
                return await func(*args, **kwargs)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in _RETRYABLE_STATUSES:
                    last_exc = exc
                    continue
                raise
        raise last_exc
    return wrapper
