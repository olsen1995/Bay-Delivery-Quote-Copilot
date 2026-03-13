#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import sys
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError
from urllib.request import Request, urlopen

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None


def base_url() -> str:
    # Prefer BASE_URL for deploy smoke usage; keep SMOKE_BASE_URL for backwards compatibility.
    return (os.getenv("BASE_URL") or os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000")).rstrip("/")


def admin_headers() -> Dict[str, str]:
    """
    Admin auth is HTTP Basic in production (Render env vars).
    BAYDELIVERY_ADMIN_TOKEN is legacy/optional; keep for backwards-compat smoke checks.
    """
    headers: Dict[str, str] = {}

    token = os.getenv("BAYDELIVERY_ADMIN_TOKEN", "").strip()
    if token:
        headers["X-Admin-Token"] = token

    user = os.getenv("ADMIN_USERNAME", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    if user and password:
        raw = f"{user}:{password}".encode("utf-8")
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")

    return headers


def basic_auth_header(username: str, password: str) -> Dict[str, str]:
    raw = f"{username}:{password}".encode("utf-8")
    return {"Authorization": "Basic " + base64.b64encode(raw).decode("ascii")}


def _req_requests(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[int, Any]:
    assert requests is not None
    url = base_url() + path
    res = requests.request(method, url, json=payload, headers=headers or {}, timeout=20)
    try:
        data = res.json()
    except Exception:
        data = res.text
    return res.status_code, data


def _req_urllib(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[int, Any]:
    url = base_url() + path
    body = None
    req_headers = dict(headers or {})

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    req = Request(url=url, method=method, data=body, headers=req_headers)
    try:
        with urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return int(resp.status), json.loads(raw)
            except Exception:
                return int(resp.status), raw
    except HTTPError as err:
        raw = err.read().decode("utf-8") if err.fp else ""
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return int(err.code), parsed


def api(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[int, Any]:
    if requests is not None:
        return _req_requests(method, path, payload, headers)
    return _req_urllib(method, path, payload, headers)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def error_detail(body: Any) -> str:
    if isinstance(body, dict) and "detail" in body:
        return str(body["detail"])
    return str(body)


def clone_payload(base: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    out = dict(base)
    out.update(kwargs)
    return out


def _admin_creds_configured() -> bool:
    return bool(os.getenv("ADMIN_USERNAME", "").strip() and os.getenv("ADMIN_PASSWORD", "").strip())


def _admin_credentials() -> Tuple[str, str]:
    return os.getenv("ADMIN_USERNAME", "").strip(), os.getenv("ADMIN_PASSWORD", "").strip()


def main() -> int:
    print(f"Smoke test target: {base_url()}")

    status, health = api("GET", "/health")
    require(status == 200, f"GET /health expected 200, got {status}")
    require(isinstance(health, dict) and health.get("ok") is True, "GET /health expected {'ok': true}")
    print("[ok] /health")

    quote_payload = {
        "service_type": "haul_away",
        "customer_name": "Smoke Test",
        "customer_phone": "555-0100",
        "job_address": "123 Demo St",
        "description": "smoke quote",
        "estimated_hours": 1.0,
        "crew_size": 1,
        "garbage_bag_count": 0,
        "mattresses_count": 0,
        "box_springs_count": 0,
        "scrap_pickup_location": "curbside",
    }

    status, quote = api("POST", "/quote/calculate", payload=quote_payload)
    require(status == 200, f"POST /quote/calculate expected 200, got {status}")
    require(isinstance(quote, dict) and bool(quote.get("quote_id")), "POST /quote/calculate expected quote_id")
    require(isinstance(quote, dict) and bool(quote.get("accept_token")), "POST /quote/calculate expected accept_token")
    quote_id = str(quote["quote_id"])
    accept_token = str(quote["accept_token"])
    print(f"[ok] /quote/calculate -> {quote_id}")

    status, missing_routes = api(
        "POST",
        "/quote/calculate",
        payload=clone_payload(quote_payload, service_type="small_move", pickup_address=None, dropoff_address=None),
    )
    require(status in (400, 422), f"small_move without routes expected 400/422, got {status}")
    detail = error_detail(missing_routes).lower()
    require(
        ("pickup_address" in detail) and ("dropoff_address" in detail),
        f"small_move missing-routes error should mention both pickup/dropoff, got: {missing_routes}",
    )
    print("[ok] /quote/calculate small_move missing routes rejected")

    status, small_move_ok = api(
        "POST",
        "/quote/calculate",
        payload=clone_payload(
            quote_payload,
            service_type="small_move",
            pickup_address="111 Pickup Rd",
            dropoff_address="222 Dropoff Ave",
            crew_size=2,
            estimated_hours=4,
        ),
    )
    require(status == 200, f"small_move with routes expected 200, got {status}")
    require(isinstance(small_move_ok, dict) and bool(small_move_ok.get("quote_id")), "small_move expected quote_id")
    print("[ok] /quote/calculate small_move with routes")

    status, delivery_ok = api(
        "POST",
        "/quote/calculate",
        payload=clone_payload(
            quote_payload,
            service_type="item_delivery",
            pickup_address="111 Pickup Rd",
            dropoff_address="222 Dropoff Ave",
            estimated_hours=1,
        ),
    )
    require(status == 200, f"item_delivery with routes expected 200, got {status}")
    require(isinstance(delivery_ok, dict) and bool(delivery_ok.get("quote_id")), "item_delivery expected quote_id")
    print("[ok] /quote/calculate item_delivery with routes")

    # Optional route: customer decision (some deployments may not have it yet)
    status, decision = api(
        "POST",
        f"/quote/{quote_id}/decision",
        payload={"action": "accept", "accept_token": accept_token},
    )
    if status == 404:
        detail = error_detail(decision)
        if "Not Found" in detail:
            print("SKIP: /quote/{quote_id}/decision route missing on this deployment")
        else:
            raise AssertionError(f"POST /quote/{{quote_id}}/decision returned 404: {error_detail(decision)}")
    elif status in (200, 201):
        require(isinstance(decision, dict) and decision.get("ok") is True, "quote decision expected {'ok': true}")
        print("[ok] /quote/{quote_id}/decision accept")
    elif status in (401, 403):
        print("SKIP: decision endpoint requires auth")
    else:
        raise AssertionError(
            f"POST /quote/{{quote_id}}/decision expected 200/201, 401/403, or route-missing 404; got {status} with body: {decision}"
        )

    # --- Admin page and auth behavior ---
    creds_configured = _admin_creds_configured()
    headers = admin_headers()
    admin_user, admin_password = _admin_credentials()

    status, admin_page = api("GET", "/admin")
    require(status == 200, f"GET /admin expected 200, got {status}")
    require(isinstance(admin_page, str), "GET /admin expected HTML response")
    require("Admin Access" in admin_page, "GET /admin missing Admin Access marker")
    require("id=\"refreshBtn\"" in admin_page, "GET /admin missing refresh button marker")
    print("[ok] /admin page marker checks")

    status, admin_uploads_page = api("GET", "/admin/uploads")
    require(status == 200, f"GET /admin/uploads expected 200, got {status}")
    require(isinstance(admin_uploads_page, str), "GET /admin/uploads expected HTML response")
    require("Customer Uploads" in admin_uploads_page, "GET /admin/uploads missing title marker")
    require("id=\"btnSearch\"" in admin_uploads_page, "GET /admin/uploads missing search button marker")
    print("[ok] /admin/uploads page marker checks")

    if creds_configured:
        bad_headers = basic_auth_header(admin_user + "__bad", admin_password)
        status, bad_auth = api("GET", "/admin/api/smoke_uploads", headers=bad_headers)
        require(
            status in (401, 403),
            f"GET /admin/api/smoke_uploads bad auth expected 401/403, got {status} ({bad_auth})",
        )
        print("[ok] /admin/api/smoke_uploads rejects bad credentials")

        status, smoke_ok = api("GET", "/admin/api/smoke_uploads", headers=headers)
        require(status == 200, f"GET /admin/api/smoke_uploads with auth expected 200, got {status} ({smoke_ok})")
        require(isinstance(smoke_ok, dict) and smoke_ok.get("ok") is True, "smoke auth check expected {'ok': true}")
        print("[ok] /admin/api/smoke_uploads accepts correct credentials")

        status, authed_quotes = api("GET", "/admin/api/quotes?limit=1", headers=headers)
        require(status == 200, f"GET /admin/api/quotes?limit=1 with auth expected 200, got {status} ({authed_quotes})")
        require(isinstance(authed_quotes, dict) and isinstance(authed_quotes.get("items"), list), "admin quotes expected items list")
        print("[ok] /admin/api/quotes authed read-only fetch")
    else:
        print("[skip] admin auth pass/fail checks (ADMIN_USERNAME/ADMIN_PASSWORD not configured)")

    status, unauth_uploads = api("GET", "/admin/api/uploads?limit=1")

    # If admin creds are configured, unauth MUST be denied (401/403)
    if creds_configured:
        require(
            status in (401, 403),
            f"GET /admin/api/uploads unauth expected 401/403 when creds configured; got {status} ({unauth_uploads})",
        )
        print("[ok] /admin/api/uploads unauth denied (creds configured)")
    else:
        # If creds are NOT configured, fail-closed is acceptable (503),
        # and some older deployments might allow 200 (warn only).
        require(
            status in (200, 401, 403, 503),
            f"GET /admin/api/uploads unauth expected 200/401/403/503 when creds NOT configured; got {status} ({unauth_uploads})",
        )
        if status == 503:
            print("[ok] /admin/api/uploads locked (503, creds not configured)")
        elif status in (401, 403):
            print("[ok] /admin/api/uploads denied (401/403, creds not configured)")
        else:
            print("[warn] /admin/api/uploads unauth allowed (admin auth not configured)")

    # If we have Basic auth headers, confirm authed access works
    if "Authorization" in headers:
        status, authed_uploads = api("GET", "/admin/api/uploads?limit=1", headers=headers)
        require(status == 200, f"GET /admin/api/uploads with auth expected 200, got {status} ({authed_uploads})")
        print("[ok] /admin/api/uploads authed")

    # Drive check (optional)
    if isinstance(health, dict) and health.get("drive_configured") is True:
        require("Authorization" in headers, "Drive is configured but admin auth env vars are missing for backup check")
        status, backups = api("GET", "/admin/api/drive/backups", headers=headers)
        require(status == 200, f"GET /admin/api/drive/backups expected 200, got {status} ({backups})")
        require(isinstance(backups, dict), "Drive backups response expected JSON object")
        print("[ok] /admin/api/drive/backups")
    else:
        print("[skip] drive backup check (drive_configured=false or not reported)")

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
