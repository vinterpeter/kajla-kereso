# Kajla Kereso API

A "Hol vagy, Kajla?" turisztikai program helyszineinek API-ja.

## Base URL

```
http://localhost:8080
```

## Vegpontok

### GET /api/categories

Kategoriak listaja darabszamokkal.

**Valasz:**
```json
{
  "categories": [
    {"key": "trips", "label": "Kajla-korok", "count": 42},
    {"key": "stamps", "label": "Pecsetelo helyek", "count": 889},
    {"key": "castles", "label": "Varak es kastelyok", "count": 22},
    {"key": "adventures", "label": "Kalandok", "count": 298},
    {"key": "bringa", "label": "Bringakorok", "count": 10}
  ]
}
```

---

### GET /api/locations

Helyszinek listazasa szurokkel.

**Query parameterek:**

| Parameter | Tipus | Leiras |
|-----------|-------|--------|
| `category` | string | Kategoria: `trips`, `stamps`, `castles`, `adventures`, `bringa` |
| `county` | string | Varmegye neve (reszleges, nem kis-nagybetu erzekeny) |
| `city` | string | Varos neve (reszleges, nem kis-nagybetu erzekeny) |
| `search` | string | Szabad szoveges kereses a nev mezoben |
| `lat` | float | Kozeppont szelesseg (sugar/autos kereshez) |
| `lon` | float | Kozeppont hosszusag (sugar/autos kereshez) |
| `radius` | float | Sugar km-ben (`lat` + `lon` szukseges) |
| `drive_time` | float | Max autos utazasi ido percben (`lat` + `lon` szukseges, OSRM alapu) |
| `limit` | int | Max elemszam (alapertelmezett: 50, max: 500) |
| `offset` | int | Eltolas lapozashoz |

**Peldak:**

Pecsetelo helyek Baranya varmegyeben:
```
GET /api/locations?category=stamps&county=baranya
```

Budapest Keleti kozeleben 5 km-en belul:
```
GET /api/locations?lat=47.497&lon=19.083&radius=5
```

Autoval 30 percen belul elerhetok Egerbol:
```
GET /api/locations?lat=47.902&lon=20.377&drive_time=30&category=trips
```

Kereses nev szerint:
```
GET /api/locations?search=arboretum
```

**Valasz:**
```json
{
  "total": 134,
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "id": "stamps-1089",
      "category": "stamps",
      "name": "Rendormuzeum",
      "lat": 47.49834,
      "lon": 19.083274,
      "city": "Budapest",
      "county": "Budapest varmegye",
      "address": "1087 Budapest, Mosonyi u. 5.",
      "distance_km": 0.15,
      "drive_distance_km": null,
      "drive_duration_min": null
    }
  ]
}
```

Sugar vagy autos ido kereses eseten az eredmenyek tavolsag/ido szerint rendezettek.

---

### GET /api/locations/{id}

Egy helyszin reszletes adatai.

**Pelda:**
```
GET /api/locations/castles-1
```

**Valasz:**
```json
{
  "id": "castles-1",
  "category": "castles",
  "name": "Esterhazy-kastely",
  "lat": 47.6210097,
  "lon": 16.8706548,
  "city": "Fertod",
  "county": "",
  "address": "9431 Fertod, Joseph Haydn utca 2.",
  "distance_km": null,
  "drive_distance_km": null,
  "drive_duration_min": null,
  "details": {
    "id": 1,
    "name": "Esterhazy-kastely",
    "popup_image_desktop": "https://kajla.hu/img/kastelyok-es-varak/popup-content/1-castle.png",
    "...": "..."
  }
}
```

---

### GET /api/docs

Interaktiv Swagger UI dokumentacio.

---

## ID formatum

Az ID-k kategoriaval prefixaltak az egyediseg erdekeben:
- `trips-{id}` - Kajla-korok
- `stamps-{id}` - Pecsetelo helyek
- `castles-{id}` - Varak
- `adventures-{slug}-{station_id}` - Kaland allomas
- `bringa-{id}` - Bringakorok

## Megjegyzesek

- Az autos ido kereses (`drive_time`) az OSRM nyilvanos routing szolgaltatast hasznalja. Max 200 elemre kerul kiszamitasra teljesitmeny okokbol.
- A sugar kereses Haversine formulaval szamol (legvonalbeli tavolsag).
- Az adatok a kajla.hu-rol szarmaznak es a `scrape.py`-vel frissithetok.
- Az API Swagger UI-ja elerheto a `/docs` vegponton.
