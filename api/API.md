# Kajla Kereso API

A "Hol vagy, Kajla?" turisztikai program helyszineinek API-ja.
Swagger UI: `/docs`

## Helyszin vegpontok

### GET /api/categories
Kategoriak darabszamokkal.

### GET /api/locations
Helyszinek listazasa szurokkel.

| Parameter | Tipus | Leiras |
|-----------|-------|--------|
| `category` | string | `trips`, `stamps`, `castles`, `adventures`, `bringa` |
| `county` | string | Varmegye (reszleges, case-insensitive) |
| `city` | string | Varos (reszleges, case-insensitive) |
| `search` | string | Kereses nevben |
| `lat` | float | Kozeppont szelesseg |
| `lon` | float | Kozeppont hosszusag |
| `radius` | float | Sugar km-ben (lat+lon szukseges) |
| `drive_time` | float | Max autos ut percben (lat+lon szukseges, OSRM) |
| `limit` | int | Max elemszam (default: 50, max: 500) |
| `offset` | int | Lapozas |

Peldak:
```
GET /api/locations?category=stamps&county=baranya
GET /api/locations?lat=47.497&lon=19.083&radius=5
GET /api/locations?lat=47.902&lon=20.377&drive_time=60&category=trips
GET /api/locations?search=arboretum
```

### GET /api/locations/{id}
Egy helyszin reszletes adatai. ID formatum: `trips-19`, `stamps-1089`, `castles-1`, `adventures-liget-1`, `bringa-0`.

### GET /api/boat-info
MAHART es BAHART hajo informaciok (kikotok, kedvezmenyek, idoszakok).

---

## Scraper Agent vegpontok (kajla.hu/ajanlatok friss adatai)

### GET /api/agent/stats
Osszesito statisztikak (darabszamok, szolgaltatasok eloszlasa).

### GET /api/agent/counties
Elerheto varmegyek listaja.

### GET /api/agent/cities?county=baranya
Elerheto varosok (opcionalis varmegye szuro).

### GET /api/agent/trips
Kajla-korok szurese.

| Parameter | Tipus | Leiras |
|-----------|-------|--------|
| `county` | string | Varmegye |
| `city` | string | Varos |
| `search` | string | Kereses nev/leiras |
| `max_duration` | float | Max idotartam (ora) |
| `max_length` | float | Max tav (km) |
| `max_difficulty` | int | Max nehezseg (1-5) |
| `parking` | bool | Van parkolo |
| `toilet` | bool | Van mosdo |
| `buffet` | bool | Van bufe |
| `dog_allowed` | bool | Kutyabarat |
| `carriage` | bool | Babakocsival jarhato |
| `postcard` | bool | Van kepeslap |
| `statue` | bool | Van Kajla szobor |
| `free_only` | bool | Csak ingyenes |

### GET /api/agent/stamps
Pecsetelo helyek szurese: `county`, `city`, `search`, `postcard`, `museum`.

### GET /api/agent/discounts
Kedvezmenyek szurese: `county`, `city`, `search`.

### POST /api/agent/refresh
Adatok ujratolti a kajla.hu/ajanlatok-rol.

### POST /api/refresh-all?save=true
TELJES adatfrissites minden forrasbol (ajanlatok, aprodok, kalandok, bringakorok, hajo info). `save=true`: menti a kajla_data.json-t.

---

## Adatforrasok

| Forras | URL | Adat |
|--------|-----|------|
| Ajanlatok | kajla.hu/ajanlatok | trips (42), stamps (890), discounts (49) |
| Aprodok | kajla.hu/aprodok | castles (22) |
| Kalandok | kajla.hu/js/json/{city}-trip-quests.json | adventures (11 konyv, 298 allomas) |
| Bringakorok | kajla.hu/bringakorok | bringa (10 utvonal, utvonal-geometriaval) |
| BAHART | bahart.hu | Balatoni hajo info |
| MAHART | mahartpassnave.hu | Dunai hajo info |
