"""Distance and routing calculations."""

import math
import urllib.request
import json


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def osrm_drive_info(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> dict | None:
    """Get driving distance and duration via OSRM public API.

    Returns {"distance_km": float, "duration_min": float} or None on error.
    OSRM uses lon,lat order.
    """
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}?overview=false"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "KajlaKeresoAPI/1.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            return {
                "distance_km": round(route["distance"] / 1000, 1),
                "duration_min": round(route["duration"] / 60, 0),
            }
    except Exception:
        pass
    return None
