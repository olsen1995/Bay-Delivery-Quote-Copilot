from __future__ import annotations

import os
import re
import time
from collections import deque
from dataclasses import dataclass
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass(frozen=True)
class RateLimitRule:
    rule_id: str
    limit: int
    window_seconds: int = 60
    method: str | None = None
    exact_path: str | None = None
    prefix_path: str | None = None
    path_regex: re.Pattern[str] | None = None


@dataclass(frozen=True)
class SizeLimitRule:
    max_bytes: int
    method: str | None = None
    exact_path: str | None = None
    prefix_path: str | None = None
    path_regex: re.Pattern[str] | None = None


def extract_client_ip(request: Request) -> str:
    x_forwarded_for = (request.headers.get("x-forwarded-for") or "").strip()
    if x_forwarded_for:
        first_ip = x_forwarded_for.split(",", 1)[0].strip()
        if first_ip:
            return first_ip

    client = request.client
    if client and client.host:
        return client.host

    return "unknown"


def _match_rule(method: str, path: str, rule) -> bool:
    if rule.method and method != rule.method:
        return False
    if rule.exact_path and path == rule.exact_path:
        return True
    if rule.prefix_path and path.startswith(rule.prefix_path):
        return True
    if rule.path_regex and rule.path_regex.fullmatch(path):
        return True
    return False


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rules: list[SizeLimitRule]):
        super().__init__(app)
        self.rules = rules

    async def dispatch(self, request: Request, call_next):
        method = request.method.upper()
        path = request.url.path

        for rule in self.rules:
            if not _match_rule(method, path, rule):
                continue
            content_length_header = request.headers.get("content-length")
            if not content_length_header:
                break
            try:
                content_length = int(content_length_header)
            except ValueError:
                break
            if content_length > rule.max_bytes:
                return JSONResponse(status_code=413, content={"detail": "payload too large"})
            break

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rules: list[RateLimitRule]):
        super().__init__(app)
        self.rules = rules
        self._buckets: dict[tuple[str, str], deque[float]] = {}
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next):
        method = request.method.upper()
        path = request.url.path

        rule = None
        for candidate in self.rules:
            if _match_rule(method, path, candidate):
                rule = candidate
                break

        if not rule:
            return await call_next(request)

        if os.getenv("PYTEST_CURRENT_TEST") and not request.headers.get("x-enable-rate-limit-tests"):
            return await call_next(request)

        ip = extract_client_ip(request)
        now = time.time()
        window_start = now - rule.window_seconds
        key = (ip, rule.rule_id)

        with self._lock:
            bucket = self._buckets.setdefault(key, deque())

            while bucket and bucket[0] <= window_start:
                bucket.popleft()

            if len(bucket) >= rule.limit:
                return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})

            bucket.append(now)

            empty_keys = [k for k, q in self._buckets.items() if not q]
            for empty_key in empty_keys:
                self._buckets.pop(empty_key, None)

        return await call_next(request)

    def clear_buckets(self) -> None:
        with self._lock:
            self._buckets.clear()
