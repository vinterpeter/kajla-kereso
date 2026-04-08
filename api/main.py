"""Kajla Kereső API - FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .data import get_categories, get_location, get_locations, load_data
from .geo import haversine_km, osrm_drive_info
from .refresh_agent import RefreshAgent
from .scraper_agent import KajlaAgent
from .models import (
    CategoriesResponse,
    CategoryInfo,
    LocationDetail,
    LocationListResponse,
    LocationSummary,
)


kajla_agent = KajlaAgent()


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_data()
    kajla_agent.fetch_all()
    yield


app = FastAPI(
    title="Kajla Kereső API",
    description="API a Kajla családbarát turisztikai program helyszíneihez",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vinterpeter.github.io",
        "http://localhost:8765",
        "http://localhost:8000",
        "http://127.0.0.1:8765",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/locations", response_model=LocationListResponse)
def list_locations(
    category: str | None = Query(None, description="Kategória: trips, stamps, castles, adventures, bringa"),
    county: str | None = Query(None, description="Vármegye neve (részleges, nem kis-nagybetű érzékeny)"),
    city: str | None = Query(None, description="Város neve (részleges, nem kis-nagybetű érzékeny)"),
    search: str | None = Query(None, description="Szabad szöveges keresés a név mezőben"),
    lat: float | None = Query(None, description="Középpont szélesség (sugár kereséshez)"),
    lon: float | None = Query(None, description="Középpont hosszúság (sugár kereséshez)"),
    radius: float | None = Query(None, description="Sugár km-ben (lat + lon szükséges)"),
    drive_time: float | None = Query(None, description="Max autós utazási idő percben (lat + lon szükséges, OSRM alapú)"),
    limit: int = Query(50, ge=1, le=500, description="Max elemszám"),
    offset: int = Query(0, ge=0, description="Eltolás (lapozáshoz)"),
):
    """Helyszínek listázása szűrőkkel. Sugár/autós idő kereséshez lat + lon szükséges."""

    # Validate geo search params
    has_origin = lat is not None and lon is not None
    radius_search = has_origin and radius is not None
    drive_search = has_origin and drive_time is not None

    if (radius is not None or drive_time is not None) and not has_origin:
        raise HTTPException(
            status_code=400,
            detail="Sugár/autós idő kereséshez lat és lon együtt szükséges",
        )

    # Pre-filter by radius (Haversine) to limit OSRM calls
    max_radius = radius if radius else (drive_time * 2.5 if drive_time else None)

    results = []
    for loc in get_locations():
        if category and loc["category"] != category:
            continue
        if county and county.lower() not in loc["county"].lower():
            continue
        if city and city.lower() not in loc["city"].lower():
            continue
        if search and search.lower() not in loc["name"].lower():
            continue

        dist = None
        if has_origin:
            dist = haversine_km(lat, lon, loc["lat"], loc["lon"])
            if max_radius and dist > max_radius:
                continue

        if radius_search and dist is not None and dist > radius:
            continue

        item = LocationSummary(
            id=loc["id"],
            category=loc["category"],
            name=loc["name"],
            lat=loc["lat"],
            lon=loc["lon"],
            city=loc["city"],
            county=loc["county"],
            address=loc["address"],
            distance_km=round(dist, 2) if dist is not None else None,
        )
        results.append(item)

    # OSRM drive time enrichment (only for manageable result sets)
    if drive_search and len(results) <= 200:
        enriched = []
        for item in results:
            info = osrm_drive_info(lat, lon, item.lat, item.lon)
            if info:
                item.drive_distance_km = info["distance_km"]
                item.drive_duration_min = info["duration_min"]
                if item.drive_duration_min <= drive_time:
                    enriched.append(item)
            # If OSRM fails, skip the item in drive_time mode
        results = enriched

    # Sort
    if drive_search:
        results.sort(key=lambda x: x.drive_duration_min or 0)
    elif has_origin:
        results.sort(key=lambda x: x.distance_km or 0)
    else:
        results.sort(key=lambda x: x.name)

    total = len(results)
    page = results[offset : offset + limit]

    return LocationListResponse(total=total, limit=limit, offset=offset, items=page)


@app.get("/api/locations/{location_id}", response_model=LocationDetail)
def get_location_detail(location_id: str):
    """Egy helyszín részletes adatai."""
    loc = get_location(location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Helyszín nem található")
    return LocationDetail(**loc)


@app.get("/api/categories", response_model=CategoriesResponse)
def list_categories():
    """Kategóriák listája darabszámokkal."""
    return CategoriesResponse(
        categories=[CategoryInfo(**c) for c in get_categories()]
    )


@app.get("/api/docs.md", response_class=PlainTextResponse, include_in_schema=False)
def api_docs_md():
    """API dokumentáció markdown formátumban."""
    md_path = Path(__file__).parent / "API.md"
    return md_path.read_text(encoding="utf-8")


# =========== SCRAPER AGENT ENDPOINTS ===========

@app.get("/api/agent/stats")
def agent_stats():
    """Összesítő statisztikák a kajla.hu/ajanlatok friss adataiból."""
    return kajla_agent.get_stats()


@app.get("/api/agent/counties")
def agent_counties():
    """Elérhető vármegyék listája."""
    return {"counties": kajla_agent.get_counties()}


@app.get("/api/agent/cities")
def agent_cities(county: str | None = Query(None, description="Vármegye szűrő")):
    """Elérhető városok (opcionálisan vármegyére szűrve)."""
    return {"cities": kajla_agent.get_cities(county)}


@app.get("/api/agent/trips")
def agent_trips(
    county: str | None = Query(None),
    city: str | None = Query(None),
    search: str | None = Query(None),
    max_duration: float | None = Query(None, description="Max időtartam (óra)"),
    max_length: float | None = Query(None, description="Max táv (km)"),
    max_difficulty: int | None = Query(None, ge=1, le=5, description="Max nehézség (1-5)"),
    parking: bool | None = Query(None),
    toilet: bool | None = Query(None),
    buffet: bool | None = Query(None),
    dog_allowed: bool | None = Query(None),
    carriage: bool | None = Query(None),
    postcard: bool | None = Query(None, description="Van képeslap a helyszínen"),
    statue: bool | None = Query(None, description="Van Kajla szobor a helyszínen"),
    free_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Kajla-körök szűrése a kajla.hu/ajanlatok friss adataiból."""
    results = kajla_agent.filter_trips(
        county=county, city=city, search=search,
        max_duration=max_duration, max_length=max_length, max_difficulty=max_difficulty,
        parking=parking, toilet=toilet, buffet=buffet,
        dog_allowed=dog_allowed, carriage=carriage,
        postcard=postcard, statue=statue, free_only=free_only,
    )
    total = len(results)
    return {"total": total, "limit": limit, "offset": offset, "items": results[offset:offset + limit]}


@app.get("/api/agent/stamps")
def agent_stamps(
    county: str | None = Query(None),
    city: str | None = Query(None),
    search: str | None = Query(None),
    postcard: bool | None = Query(None, description="Képeslapot árul"),
    museum: bool | None = Query(None, description="Múzeum"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Pecsételő helyek szűrése a kajla.hu/ajanlatok friss adataiból."""
    results = kajla_agent.filter_stamps(
        county=county, city=city, search=search,
        postcard=postcard, museum=museum,
    )
    total = len(results)
    return {"total": total, "limit": limit, "offset": offset, "items": results[offset:offset + limit]}


@app.get("/api/agent/discounts")
def agent_discounts(
    county: str | None = Query(None),
    city: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Kedvezmények szűrése a kajla.hu/ajanlatok friss adataiból."""
    results = kajla_agent.filter_discounts(county=county, city=city, search=search)
    total = len(results)
    return {"total": total, "limit": limit, "offset": offset, "items": results[offset:offset + limit]}


@app.post("/api/agent/refresh")
def agent_refresh():
    """Adatok újratöltése a kajla.hu/ajanlatok-ról."""
    counts = kajla_agent.fetch_all()
    return {"status": "ok", "counts": counts}


@app.get("/api/boat-info")
def boat_info():
    """MAHART és BAHART hajó információk - ingyenes utazás Kajla útlevéllel."""
    return {
        "bahart": {
            "name": "BAHART - Balatoni Hajózási Zrt.",
            "url": "https://bahart.hu",
            "kajla_info_url": "https://bahart.hu/hu/dijmentes-hajos-utazas-kajlaval",
            "benefit": "6-11 éves Kajla útlevéllel rendelkező diákok ingyenes utazása menetrend szerinti hajókon",
            "routes": "Települések közötti járatok a Balatonon",
            "ports": ["Siófok", "Balatonfüred", "Tihany", "Keszthely", "Badacsony", "Fonyód", "Balatonboglár", "Balatonlelle", "Balatonföldvár", "Révfülöp", "Szántód"],
            "period": "Tavaszi szünet és nyári szezon",
            "requirements": ["Kajla útlevél (fehér/zöld)", "Diákigazolvány", "6-11 éves kor"],
        },
        "mahart": {
            "name": "MAHART PassNave Kft.",
            "url": "https://mahartpassnave.hu",
            "kajla_info_url": "https://mahartpassnave.hu/hu/hirek/kajla-nyar-a-mahart-fedelzeten",
            "benefit": "Kajla útlevéllel rendelkező gyerekek ingyenes utazása a Dunán",
            "routes": "Budapest-Szentendre, Visegrádi körjárat, Esztergomi sétahajó",
            "ports": ["Budapest - Belgrád rakpart", "Szentendre", "Visegrád", "Esztergom"],
            "period": "Június 21 - augusztus 31",
            "requirements": ["Kajla útlevél (fehér vagy óvodás)"],
        },
    }


@app.post("/api/refresh-all")
def refresh_all_data(save: bool = Query(False, description="Mentse-e a kajla_data.json-t")):
    """TELJES adatfrissítés minden forrásból (kajla.hu/ajanlatok, aprodok, kalandok, bringakörök).

    Ez újratölti az összes adatot és opcionálisan menti a kajla_data.json fájlba.
    """
    agent = RefreshAgent()
    summary = agent.refresh_all()
    if save:
        agent.save()
        load_data()  # reload API data from fresh JSON
    return {"status": "ok", "summary": summary, "saved": save, "report": agent.report}
