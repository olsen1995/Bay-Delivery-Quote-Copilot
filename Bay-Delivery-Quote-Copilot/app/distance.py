from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlencode

import requests


class DistanceError(Exception):
    """Raised when Google Distance Matrix cannot return a valid distance."""


def resolve_distance_km(
    origin_address: str,
    destination_address: str,
    api_key: str,
    timeout_seconds: int = 12,
) -> float:
    """
    Resolve driving distance in KM using Google Distance Matrix API.

    Returns:
        float: distance in kilometers (km)

    Raises:
        DistanceError: if response is invalid, missing fields, or not OK.
    """

    origin_address = (origin_address or "").strip()
    destination_address = (destination_address or "").strip()
    api_key = (api_key or "").strip()

    if not origin_address:
        raise DistanceError("Missing origin_address.")
    if not destination_address:
        raise DistanceError("Missing destination_address.")
    if not api_key:
        raise DistanceError("Missing Google Maps API key.")

    params = {
        "origins": origin_address,
        "destinations": destination_address,
        "units": "metric",
        "key": api_key,
    }

    url = (
        "https://maps.googleapis.com/maps/api/distancematrix/json?"
        + urlencode(params)
    )

    try:
        resp = requests.get(url, timeout=timeout_seconds)
    except requests.RequestException as e:
        raise DistanceError(f"Distance Matrix request failed: {e}") from e

    if resp.status_code != 200:
        raise DistanceError(
            f"Distance Matrix HTTP {resp.status_code}: {resp.text[:200]}"
        )

    try:
        data: Dict[str, Any] = resp.json()
    except ValueError as e:
        raise DistanceError("Distance Matrix returned non-JSON response.") from e

    top_status = str(data.get("status", "")).upper()
    if top_status != "OK":
        err = data.get("error_message")
        msg = f"Distance Matrix status={top_status}"
        if err:
            msg += f" error_message={err}"
        raise DistanceError(msg)

    try:
        elem0 = data["rows"][0]["elements"][0]
        elem_status = str(elem0.get("status", "")).upper()

        if elem_status != "OK":
            raise DistanceError(f"Distance element status={elem_status}")

        meters = elem0["distance"]["value"]
        km = float(meters) / 1000.0

    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise DistanceError(
            "Distance Matrix response missing expected fields."
        ) from e

    if km <= 0:
        raise DistanceError(f"Resolved distance is invalid: {km} km")

    return km
