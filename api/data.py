"""Load and normalize kajla_data.json into a flat list of locations."""

import json
import os
from pathlib import Path


CATEGORY_LABELS = {
    "trips": "Kajla-korök",
    "stamps": "Pecsételo helyek",
    "castles": "Várak és kastélyok",
    "adventures": "Kalandok",
    "bringa": "Bringakörök",
}

_locations: list[dict] = []
_index: dict[str, dict] = {}
_categories: list[dict] = []


def _parse_float(val, default=None):
    if val is None:
        return default
    try:
        s = str(val).split(",")[0].strip()
        v = float(s)
        return v if not (v != v) else default  # NaN check
    except (ValueError, TypeError):
        return default


def _parse_lon(item):
    lat_str = str(item.get("lat", ""))
    if "," in lat_str:
        parts = lat_str.split(",")
        if len(parts) >= 2:
            v = _parse_float(parts[1].strip())
            if v is not None:
                return v
    return _parse_float(item.get("lon") or item.get("trip_lon"))


def _valid_coords(lat, lon):
    return (
        lat is not None
        and lon is not None
        and 44 < lat < 50
        and 15 < lon < 24
    )


def _normalize_county(county: str) -> str:
    if not county:
        return ""
    county = county.strip()
    if county and "vármegye" not in county.lower() and "kraj" not in county.lower():
        county = county + " vármegye"
    return county


def load_data(data_path: str | None = None):
    global _locations, _index, _categories

    if data_path is None:
        data_path = os.environ.get(
            "KAJLA_DATA_PATH",
            str(Path(__file__).resolve().parent.parent / "kajla_data.json"),
        )

    with open(data_path, encoding="utf-8") as f:
        raw = json.load(f)

    locations = []

    # Trips
    for t in raw.get("tripsData", []):
        if t.get("active") != 1 or t.get("status") != 1:
            continue
        lat = _parse_float(t.get("lat") or t.get("trip_lat"))
        lon = _parse_float(t.get("trip_lon")) or _parse_lon(t)
        if not _valid_coords(lat, lon):
            continue
        locations.append({
            "id": f"trips-{t['id']}",
            "category": "trips",
            "name": t.get("name") or t.get("trip_name") or "",
            "lat": lat,
            "lon": lon,
            "city": t.get("city", ""),
            "county": _normalize_county(t.get("county", "")),
            "address": f"{t.get('zip', '')} {t.get('city', '')}, {t.get('address', '')}".strip(", "),
            "details": {
                k: v
                for k, v in t.items()
                if k not in ("active", "status")
            },
        })

    # Stamps
    for s in raw.get("stampsData", []):
        if s.get("active") != 1 or s.get("status") != 1:
            continue
        lat = _parse_float(s.get("lat"))
        lon = _parse_lon(s) or _parse_float(s.get("lon"))
        if not _valid_coords(lat, lon):
            continue
        locations.append({
            "id": f"stamps-{s['id']}",
            "category": "stamps",
            "name": s.get("name", ""),
            "lat": lat,
            "lon": lon,
            "city": s.get("city", ""),
            "county": _normalize_county(s.get("county", "")),
            "address": s.get("full_address") or f"{s.get('zip', '')} {s.get('city', '')}, {s.get('address', '')}".strip(", "),
            "details": {
                k: v
                for k, v in s.items()
                if k not in ("active", "status")
            },
        })

    # Castles
    for c in raw.get("castlesData", []):
        lat = _parse_float(c.get("lat"))
        lon = _parse_float(c.get("lon"))
        if not _valid_coords(lat, lon):
            continue
        locations.append({
            "id": f"castles-{c['id']}",
            "category": "castles",
            "name": c.get("name", ""),
            "lat": lat,
            "lon": lon,
            "city": c.get("city", ""),
            "county": "",
            "address": f"{c.get('postal_code', '')} {c.get('city', '')}, {c.get('address', '')}".strip(", "),
            "details": dict(c),
        })

    # Adventures (each adventure's stations as individual locations)
    for adv in raw.get("adventuresData", []):
        for i, st in enumerate(adv.get("stations", [])):
            lat = _parse_float(st.get("lat"))
            lon = _parse_float(st.get("lng"))
            if not _valid_coords(lat, lon):
                continue
            slug = adv.get("unique_slug") or adv.get("slug", "")
            locations.append({
                "id": f"adventures-{slug}-{st.get('id', i)}",
                "category": "adventures",
                "name": st.get("station_name", ""),
                "lat": lat,
                "lon": lon,
                "city": "",
                "county": "",
                "address": "",
                "details": {
                    "adventure_name": adv.get("name", ""),
                    "adventure_slug": slug,
                    "quest_name": st.get("quest_name", ""),
                    **st,
                },
            })

    # Bringa
    for i, b in enumerate(raw.get("bringaData", [])):
        sc = b.get("start_coordinates", {})
        lat = _parse_float(sc.get("lat"))
        lon = _parse_float(sc.get("lng"))
        if not _valid_coords(lat, lon):
            continue
        details = {k: v for k, v in b.items() if k != "route_geometry"}
        locations.append({
            "id": f"bringa-{b.get('id', i)}",
            "category": "bringa",
            "name": b.get("title", ""),
            "lat": lat,
            "lon": lon,
            "city": "",
            "county": "",
            "address": "",
            "details": details,
        })

    _locations = locations
    _index = {loc["id"]: loc for loc in locations}

    # Category counts
    counts: dict[str, int] = {}
    for loc in locations:
        counts[loc["category"]] = counts.get(loc["category"], 0) + 1
    _categories = [
        {"key": k, "label": CATEGORY_LABELS.get(k, k), "count": counts.get(k, 0)}
        for k in ["trips", "stamps", "castles", "adventures", "bringa"]
        if counts.get(k, 0) > 0
    ]


def get_locations() -> list[dict]:
    return _locations


def get_location(location_id: str) -> dict | None:
    return _index.get(location_id)


def get_categories() -> list[dict]:
    return _categories
