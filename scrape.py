#!/usr/bin/env python3
"""
Kajla adatgyűjtő script
Összegyűjti az összes adatot a kajla.hu-ról és a kapcsolódó forrásokból.
"""

import json
import re
import time
import urllib.request
import urllib.parse
import math
from collections import defaultdict

USER_AGENT = 'KajlaKereso/1.0'
OUTPUT = 'kajla_data.json'

def fetch(url, retries=2):
    """URL letöltése retry-val"""
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=30)
            return resp.read().decode('utf-8', errors='replace')
        except Exception as e:
            if i == retries:
                print(f'  HIBA: {url} -> {e}')
                return None
            time.sleep(2)

def fetch_json(url):
    """JSON letöltése"""
    text = fetch(url)
    if text:
        return json.loads(text)
    return None

# ============================================================
# 1. AJÁNLATOK (túrák, pecsételők, kedvezmények)
# ============================================================
print('=== 1. Ajánlatok (kajla.hu/ajanlatok) ===')
html = fetch('https://kajla.hu/ajanlatok')
data = {}

if html:
    # Extract window.tripsData, window.stampsData, window.discountsData
    for varname in ['tripsData', 'stampsData', 'discountsData']:
        pattern = r'window\.' + varname + r'\s*=\s*(\[.*?\]);'
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                data[varname] = parsed
                print(f'  {varname}: {len(parsed)} elem')
            except json.JSONDecodeError as e:
                print(f'  {varname}: JSON hiba - {e}')
        else:
            print(f'  {varname}: nem találva')

# ============================================================
# 2. APRÓDOK (várak és kastélyok)
# ============================================================
print('\n=== 2. Apródok (kajla.hu/aprodok) ===')
html_aprodok = fetch('https://kajla.hu/aprodok')
castles = []

if html_aprodok:
    # Extract castle data from HTML
    castle_pattern = r'data-castle-id=["\'](\d+)["\']'
    castle_ids = re.findall(castle_pattern, html_aprodok)

    # Parse castle pins from the map section
    pin_pattern = r'castle-pin.*?style=["\'].*?left:\s*([\d.]+)%.*?top:\s*([\d.]+)%.*?data-castle-id=["\'](\d+)["\']'

    # Extract castle names and info from popup content
    popup_pattern = r'<div[^>]*class=["\']castle-popup["\'][^>]*data-castle-id=["\'](\d+)["\'][^>]*>.*?<h\d[^>]*>(.*?)</h\d>'

    # Alternative: extract from the booklet table
    table_match = re.search(r'<table[^>]*class=["\']booklet-table["\'].*?</table>', html_aprodok, re.DOTALL)

    # Parse castles from structured data in the page
    # Look for castle data in script tags or structured elements
    castle_section = re.findall(
        r'castle-pin[^>]*?style=["\'][^"\']*?left:\s*([\d.]+)%[^"\']*?top:\s*([\d.]+)%[^"\']*?["\'][^>]*?data-castle-id=["\'](\d+)["\']',
        html_aprodok, re.DOTALL
    )

    # Extract castle names from popup images or heading elements
    name_pattern = re.findall(
        r'data-castle-id=["\'](\d+)["\'].*?<(?:h2|h3|h4|span[^>]*class=["\']castle-name["\'])[^>]*>(.*?)</(?:h2|h3|h4|span)>',
        html_aprodok, re.DOTALL
    )

    # Since the page structure is complex, use a simpler approach:
    # Extract all castle data from the existing JSON if available, or rebuild from scratch
    print(f'  Vár pineket találva: {len(castle_section)}')

    # We'll use the existing castle data and just refresh coordinates
    # Load existing data as baseline
    try:
        with open(OUTPUT, 'r') as f:
            existing = json.load(f)
            if 'castlesData' in existing:
                castles = existing['castlesData']
                print(f'  Meglévő váradatok: {len(castles)} vár')
    except:
        pass

# If no existing castles, build from known data
if not castles:
    # Known castle list from the aprodok page
    known_castles = [
        {"id": 1, "name": "Esterházy-kastély", "city": "Fertőd", "postal_code": "9431", "address": "Joseph Haydn utca 2."},
        {"id": 2, "name": "Sümegi vár", "city": "Sümeg", "postal_code": "8330", "address": "Sümegi vár"},
        {"id": 3, "name": "Festetics-kastély", "city": "Keszthely", "postal_code": "8360", "address": "Kastély utca 1."},
        {"id": 4, "name": "Szigligeti vár", "city": "Szigliget", "postal_code": "8264", "address": "Kossuth utca 54."},
        {"id": 5, "name": "Szigetvári vár", "city": "Szigetvár", "postal_code": "7900", "address": "Vár utca 19."},
        {"id": 6, "name": "Siklósi vár", "city": "Siklós", "postal_code": "7800", "address": "Vajda János tér 8"},
        {"id": 7, "name": "Pipo-várkastély", "city": "Ozora", "postal_code": "7086", "address": "Várkastély"},
        {"id": 8, "name": "Nádasdy-kastély", "city": "Nádasdladány", "postal_code": "8145", "address": "Kastély út 1."},
        {"id": 9, "name": "Brunszvik-kastély", "city": "Martonvásár", "postal_code": "2462", "address": "Brunszvik utca 2."},
        {"id": 10, "name": "Kamalduli remeteség", "city": "Oroszlány-Majkpuszta", "postal_code": "2840", "address": "Barokk Műemlékegyüttes"},
        {"id": 11, "name": "Esterházy-kastély", "city": "Tata", "postal_code": "2890", "address": "Hősök tere 9/a"},
        {"id": 12, "name": "Tatai vár", "city": "Tata", "postal_code": "2890", "address": "Öregvár, Váralja utca 1-3."},
        {"id": 13, "name": "Visegrádi fellegvár", "city": "Visegrád", "postal_code": "2025", "address": "Fellegvár"},
        {"id": 14, "name": "Grassalkovich-kastély", "city": "Gödöllő", "postal_code": "2100", "address": "Grassalkovich-kastély"},
        {"id": 15, "name": "Siroki vár", "city": "Sirok", "postal_code": "3332", "address": "Petőfi út 11."},
        {"id": 16, "name": "Egri vár", "city": "Eger", "postal_code": "3300", "address": "Vár 1."},
        {"id": 17, "name": "Andrássy-kastély", "city": "Tiszadob", "postal_code": "4456", "address": "Bocskai utca 59."},
        {"id": 18, "name": "Edelényi kastélysziget", "city": "Edelény", "postal_code": "3780", "address": "Borsodi út 7."},
        {"id": 19, "name": "Füzéri vár", "city": "Füzér", "postal_code": "3996", "address": "Petőfi Sándor út 3/A"},
        {"id": 20, "name": "Sárospataki vár", "city": "Sárospatak", "postal_code": "3950", "address": "Szent Erzsébet út 19."},
        {"id": 21, "name": "Almásy-kastély", "city": "Gyula", "postal_code": "5700", "address": "Kossuth Lajos utca 15."},
        {"id": 22, "name": "Gyulai vár", "city": "Gyula", "postal_code": "5700", "address": "Kossuth Lajos utca 15."},
    ]

    # Geocode each castle
    print('  Várak geocodolása...')
    for c in known_castles:
        query = f"{c['name']}, {c['city']}, Hungary"
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=1&countrycodes=hu"
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            res = json.loads(resp.read())
            if res:
                c['lat'] = float(res[0]['lat'])
                c['lon'] = float(res[0]['lon'])
                print(f'    {c["name"]}: {c["lat"]:.5f}, {c["lon"]:.5f}')
            else:
                print(f'    {c["name"]}: nem találva')
        except Exception as e:
            print(f'    {c["name"]}: hiba - {e}')
        time.sleep(1.1)

    # Add popup image URLs and text
    for c in known_castles:
        c['popup_image_desktop'] = f'https://kajla.hu/img/kastelyok-es-varak/popup-content/{c["id"]}-castle.png'
        c['popup_image_mobile'] = f'https://kajla.hu/img/kastelyok-es-varak/popup-content/{c["id"]}-castle_mobile.png'

    castles = known_castles

# Preserve existing popup_text if available
try:
    with open(OUTPUT, 'r') as f:
        existing = json.load(f)
        if 'castlesData' in existing:
            text_map = {c['id']: c.get('popup_text', '') for c in existing['castlesData']}
            coord_map = {c['id']: (c.get('lat'), c.get('lon')) for c in existing['castlesData']}
            for c in castles:
                if c['id'] in text_map and text_map[c['id']]:
                    c['popup_text'] = text_map[c['id']]
                if c['id'] in coord_map and coord_map[c['id']][0]:
                    c['lat'] = coord_map[c['id']][0]
                    c['lon'] = coord_map[c['id']][1]
except:
    pass

data['castlesData'] = castles
print(f'  Várak: {len(castles)}')

# ============================================================
# 3. KALANDOK (kajla-kalandok)
# ============================================================
print('\n=== 3. Kalandok (kajla.hu/kajla-kalandok) ===')

adventures_config = [
    {"name": "Városligeti kalandok", "slug": "liget", "json_url": "https://kajla.hu/js/json/liget-trip-quests.json"},
    {"name": "Pécsi kalandok", "slug": "pecs", "json_url": "https://kajla.hu/js/json/pecs-trip-quests.json"},
    {"name": "Soproni kalandok", "slug": "sopron", "json_url": "https://kajla.hu/js/json/sopron-trip-quests.json"},
    {"name": "Debreceni kalandok", "slug": "debrecen", "json_url": "https://kajla.hu/js/json/debrecen-trip-quests.json"},
    {"name": "Nyíregyházi kalandok", "slug": "nyiregyhaza", "json_url": "https://kajla.hu/js/json/nyiregyhaza-trip-quests.json"},
    {"name": "Balatoni kalandok 1.", "slug": "balaton", "json_url": "https://kajla.hu/js/json/balaton-trip-quests.json"},
    {"name": "Balatoni kalandok 2.", "slug": "balaton", "json_url": "https://kajla.hu/js/json/balaton-trip-quests.json"},
    {"name": "Veszprémi kalandok 1.", "slug": "veszprem", "json_url": "https://kajla.hu/js/json/veszprem-trip-quests.json"},
    {"name": "Veszprémi kalandok 2.", "slug": "veszprem", "json_url": "https://kajla.hu/js/json/veszprem-trip-quests.json"},
    {"name": "Budapesti kalandok 1.", "slug": "budapest", "json_url": "https://kajla.hu/js/json/budapest-trip-quests.json"},
    {"name": "Budapesti kalandok 2.", "slug": "budapest", "json_url": "https://kajla.hu/js/json/budapest-trip-quests.json"},
]

# Fetch station data per city (deduplicated)
city_stations = {}
for adv in adventures_config:
    city = adv['slug']
    if city not in city_stations:
        print(f'  Állomások letöltése: {city}...')
        stations_data = fetch_json(adv['json_url'])
        if stations_data:
            city_stations[city] = stations_data
            print(f'    {len(stations_data)} állomás')
        else:
            city_stations[city] = []
        time.sleep(0.5)

# Build adventuresData with unique slugs
adventures = []
slug_count = defaultdict(int)
for adv in adventures_config:
    slug_count[adv['slug']] += 1

slug_idx = defaultdict(int)
multi_slugs = {k for k, v in slug_count.items() if v > 1}

for adv in adventures_config:
    base = adv['slug']
    if base in multi_slugs:
        slug_idx[base] += 1
        unique_slug = f'{base}_{slug_idx[base]}'
    else:
        unique_slug = base

    adventures.append({
        'name': adv['name'],
        'slug': base,
        'unique_slug': unique_slug,
        'description': '',
        'image': '',
        'stations': city_stations.get(base, []),
    })

# Try to get descriptions from the main page
html_kalandok = fetch('https://kajla.hu/kajla-kalandok')
if html_kalandok:
    # Simple extraction of adventure descriptions
    for adv in adventures:
        # Look for description near the adventure name
        desc_pattern = rf'{re.escape(adv["name"])}.*?<p[^>]*>(.*?)</p>'
        match = re.search(desc_pattern, html_kalandok, re.DOTALL | re.IGNORECASE)
        if match:
            adv['description'] = re.sub(r'<[^>]+>', '', match.group(1)).strip()

data['adventuresData'] = adventures
total_stations = sum(len(a['stations']) for a in adventures)
print(f'  Kalandok: {len(adventures)}, állomások: {total_stations}')

# ============================================================
# 4. BRINGAKÖRÖK
# ============================================================
print('\n=== 4. Bringakörök (kajla.hu/bringakorok) ===')

# Preserve existing bringaData with route_geometry
try:
    with open(OUTPUT, 'r') as f:
        existing = json.load(f)
        if 'bringaData' in existing:
            data['bringaData'] = existing['bringaData']
            print(f'  Meglévő bringaadatok: {len(data["bringaData"])} útvonal')
            for r in data['bringaData']:
                rg = r.get('route_geometry', [])
                print(f'    {r["title"]}: {len(rg)} pont, {len(r.get("stamp_locations",[]))} pecsételő')
except:
    data['bringaData'] = []
    print('  Nincs meglévő bringaadat')

# ============================================================
# 5. KOORDINÁTA JAVÍTÁS
# ============================================================
print('\n=== 5. Koordináta javítás (irányítószám medián) ===')

def parse_coord(val):
    if not val: return 0.0
    s = str(val).split(',')[0].strip()
    try: return float(s)
    except: return 0.0

# Collect all coords per zip
zip_coords = defaultdict(list)
for ds_name in ['tripsData', 'stampsData']:
    for item in data.get(ds_name, []):
        z = item.get('zip')
        lat = parse_coord(item.get('lat'))
        lon = parse_coord(item.get('lon'))
        if z and 45 < lat < 49 and 16 < lon < 23:
            zip_coords[z].append((lat, lon))

# Calculate median
zip_median = {}
for z, coords in zip_coords.items():
    lats = sorted([c[0] for c in coords])
    lons = sorted([c[1] for c in coords])
    mid = len(coords) // 2
    zip_median[z] = (lats[mid], lons[mid])

def dist_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

# Fix known bad coordinates
fixes = {
    'Agárd hajóállomás (Tópart utca 3.)': (47.1988057, 18.5988544),
    'Agárd hajóállomás (Tópart utca 1.)': (47.1988057, 18.5988544),
}

corrected = 0
for ds_name in ['tripsData', 'stampsData']:
    for item in data.get(ds_name, []):
        name = item.get('name', '')
        # Apply known fixes
        if name in fixes:
            item['lat'] = str(fixes[name][0])
            item['lon'] = str(fixes[name][1])
            corrected += 1
            continue

        # Apply zip median correction
        z = item.get('zip')
        lat = parse_coord(item.get('lat'))
        lon = parse_coord(item.get('lon'))
        if z in zip_median and lat > 0 and lon > 0:
            mlat, mlon = zip_median[z]
            if dist_km(lat, lon, mlat, mlon) > 10:
                item['lat'] = str(mlat)
                item['lon'] = str(mlon)
                corrected += 1

print(f'  Javított koordináták: {corrected}')

# ============================================================
# 6. MENTÉS
# ============================================================
print(f'\n=== 6. Mentés ({OUTPUT}) ===')

# Remove discountsData if present (not needed in new design)
# Actually keep it, it might be useful later
summary = {
    'tripsData': len(data.get('tripsData', [])),
    'stampsData': len(data.get('stampsData', [])),
    'discountsData': len(data.get('discountsData', [])),
    'castlesData': len(data.get('castlesData', [])),
    'adventuresData': len(data.get('adventuresData', [])),
    'bringaData': len(data.get('bringaData', [])),
}

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)

file_size = len(json.dumps(data, ensure_ascii=False))
print(f'  Fájlméret: {file_size / 1024 / 1024:.1f} MB')
print(f'\n  Összesítés:')
for key, count in summary.items():
    print(f'    {key}: {count}')

print('\nKész!')
