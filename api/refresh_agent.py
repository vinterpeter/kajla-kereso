#!/usr/bin/env python3
"""Kajla teljes adatfrissítő ügynök.

Minden adatforrást egyszerre frissít:
1. Ajánlatok (kajla.hu/ajanlatok): trips, stamps, discounts
2. Apródok (kajla.hu/aprodok): várak és kastélyok
3. Kalandok (kajla.hu/kajla-kalandok): kalandkönyv állomások
4. Bringakörök (kajla.hu/bringakorok): útvonalak (meglévő megmarad)
5. MAHART/BAHART hajó info (meta-adat)

Használat:
    python3 -m api.refresh_agent          # frissít és összefoglalót ír
    python3 -m api.refresh_agent --save   # frissít és menti kajla_data.json-be
"""

import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

USER_AGENT = "KajlaRefreshAgent/1.0"
OUTPUT = Path(__file__).resolve().parent.parent / "kajla_data.json"


def fetch(url: str, retries: int = 2) -> str | None:
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=30)
            return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            if i == retries:
                print(f"  HIBA: {url} -> {e}")
                return None
            time.sleep(2)


def fetch_json(url: str):
    text = fetch(url)
    if text:
        return json.loads(text)
    return None


def parse_coord(val):
    if not val:
        return 0.0
    s = str(val).split(",")[0].strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def dist_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(
        math.radians(lat2)
    ) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


class RefreshAgent:
    def __init__(self):
        self.data = {}
        self.report = []

    def refresh_all(self) -> dict:
        """Minden adatforrás frissítése. Visszaadja az összefoglaló dict-et."""
        self._refresh_ajanlatok()
        self._refresh_aprodok()
        self._refresh_kalandok()
        self._refresh_bringakorok()
        self._correct_coords()
        self._add_boat_meta()
        return self._summary()

    def save(self, path: str | None = None):
        """Adatok mentése JSON fájlba."""
        target = Path(path) if path else OUTPUT
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False)
        size_mb = target.stat().st_size / 1024 / 1024
        self.report.append(f"Mentve: {target} ({size_mb:.1f} MB)")

    def _log(self, msg):
        print(msg)
        self.report.append(msg)

    # ---- 1. Ajánlatok ----
    def _refresh_ajanlatok(self):
        self._log("=== 1. Ajánlatok (kajla.hu/ajanlatok) ===")
        html = fetch("https://kajla.hu/ajanlatok")
        if not html:
            self._log("  HIBA: nem sikerült letölteni")
            return

        for varname in ["tripsData", "stampsData", "discountsData"]:
            pattern = r"window\." + varname + r"\s*=\s*(\[.*?\]);"
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                    self.data[varname] = parsed
                    self._log(f"  {varname}: {len(parsed)} elem")
                except json.JSONDecodeError as e:
                    self._log(f"  {varname}: JSON hiba - {e}")
            else:
                self._log(f"  {varname}: nem találva az oldalon")

    # ---- 2. Apródok (várak) ----
    def _refresh_aprodok(self):
        self._log("\n=== 2. Apródok (kajla.hu/aprodok) ===")
        # Meglévő adat megtartása (koordináták, popup_text, képek)
        try:
            with open(OUTPUT) as f:
                existing = json.load(f)
            if "castlesData" in existing:
                self.data["castlesData"] = existing["castlesData"]
                self._log(f"  Meglévő váradatok: {len(self.data['castlesData'])} vár")
        except Exception:
            self.data.setdefault("castlesData", [])
            self._log("  Nincs meglévő váradat")

    # ---- 3. Kalandok ----
    def _refresh_kalandok(self):
        self._log("\n=== 3. Kalandok ===")
        adventures_config = [
            ("Városligeti kalandok", "liget", "https://kajla.hu/js/json/liget-trip-quests.json"),
            ("Pécsi kalandok", "pecs", "https://kajla.hu/js/json/pecs-trip-quests.json"),
            ("Soproni kalandok", "sopron", "https://kajla.hu/js/json/sopron-trip-quests.json"),
            ("Debreceni kalandok", "debrecen", "https://kajla.hu/js/json/debrecen-trip-quests.json"),
            ("Nyíregyházi kalandok", "nyiregyhaza", "https://kajla.hu/js/json/nyiregyhaza-trip-quests.json"),
            ("Balatoni kalandok 1.", "balaton", "https://kajla.hu/js/json/balaton-trip-quests.json"),
            ("Balatoni kalandok 2.", "balaton", "https://kajla.hu/js/json/balaton-trip-quests.json"),
            ("Veszprémi kalandok 1.", "veszprem", "https://kajla.hu/js/json/veszprem-trip-quests.json"),
            ("Veszprémi kalandok 2.", "veszprem", "https://kajla.hu/js/json/veszprem-trip-quests.json"),
            ("Budapesti kalandok 1.", "budapest", "https://kajla.hu/js/json/budapest-trip-quests.json"),
            ("Budapesti kalandok 2.", "budapest", "https://kajla.hu/js/json/budapest-trip-quests.json"),
        ]

        city_stations = {}
        for name, slug, url in adventures_config:
            if slug not in city_stations:
                self._log(f"  {slug}: letöltés...")
                data = fetch_json(url)
                city_stations[slug] = data or []
                if data:
                    self._log(f"    {len(data)} állomás")
                time.sleep(0.5)

        adventures = []
        slug_count = defaultdict(int)
        for name, slug, _ in adventures_config:
            slug_count[slug] += 1
        slug_idx = defaultdict(int)
        multi = {k for k, v in slug_count.items() if v > 1}

        for name, slug, _ in adventures_config:
            if slug in multi:
                slug_idx[slug] += 1
                unique = f"{slug}_{slug_idx[slug]}"
            else:
                unique = slug
            adventures.append({
                "name": name,
                "slug": slug,
                "unique_slug": unique,
                "description": "",
                "image": "",
                "stations": city_stations.get(slug, []),
            })

        self.data["adventuresData"] = adventures
        total_st = sum(len(a["stations"]) for a in adventures)
        self._log(f"  Kalandok: {len(adventures)}, állomások: {total_st}")

    # ---- 4. Bringakörök ----
    def _refresh_bringakorok(self):
        self._log("\n=== 4. Bringakörök ===")
        try:
            with open(OUTPUT) as f:
                existing = json.load(f)
            if "bringaData" in existing:
                self.data["bringaData"] = existing["bringaData"]
                self._log(f"  Meglévő bringaadatok: {len(self.data['bringaData'])} útvonal")
        except Exception:
            self.data.setdefault("bringaData", [])
            self._log("  Nincs meglévő bringaadat")

    # ---- 5. Koordináta javítás ----
    def _correct_coords(self):
        self._log("\n=== 5. Koordináta javítás ===")
        zip_coords = defaultdict(list)
        for ds in ["tripsData", "stampsData"]:
            for item in self.data.get(ds, []):
                z = item.get("zip")
                lat = parse_coord(item.get("lat"))
                lon = parse_coord(item.get("lon"))
                if z and 45 < lat < 49 and 16 < lon < 23:
                    zip_coords[z].append((lat, lon))

        zip_median = {}
        for z, coords in zip_coords.items():
            lats = sorted(c[0] for c in coords)
            lons = sorted(c[1] for c in coords)
            mid = len(coords) // 2
            zip_median[z] = (lats[mid], lons[mid])

        fixes = {
            "Agárd hajóállomás (Tópart utca 3.)": (47.1988057, 18.5988544),
            "Agárd hajóállomás (Tópart utca 1.)": (47.1988057, 18.5988544),
        }

        corrected = 0
        for ds in ["tripsData", "stampsData"]:
            for item in self.data.get(ds, []):
                name = item.get("name", "")
                if name in fixes:
                    item["lat"] = str(fixes[name][0])
                    item["lon"] = str(fixes[name][1])
                    corrected += 1
                    continue
                z = item.get("zip")
                lat = parse_coord(item.get("lat"))
                lon = parse_coord(item.get("lon"))
                if z in zip_median and lat > 0 and lon > 0:
                    mlat, mlon = zip_median[z]
                    if dist_km(lat, lon, mlat, mlon) > 10:
                        item["lat"] = str(mlat)
                        item["lon"] = str(mlon)
                        corrected += 1
        self._log(f"  Javított koordináták: {corrected}")

    # ---- 6. Hajó meta-adat ----
    def _add_boat_meta(self):
        self._log("\n=== 6. Hajó/közlekedési meta-adatok ===")
        self.data["boatInfo"] = {
            "bahart": {
                "name": "BAHART - Balatoni Hajózási Zrt.",
                "url": "https://bahart.hu",
                "kajla_info": "https://bahart.hu/hu/dijmentes-hajos-utazas-kajlaval",
                "benefit": "6-11 éves Kajla útlevéllel rendelkező diákok ingyenes utazása menetrend szerinti hajókon",
                "routes": "Települések közötti járatok a Balatonton (Siófok, Balatonfüred, Tihany, Keszthely, stb.)",
                "period": "Tavaszi szünet és nyári időszak",
            },
            "mahart": {
                "name": "MAHART PassNave Kft.",
                "url": "https://mahartpassnave.hu",
                "kajla_info": "https://mahartpassnave.hu/hu/hirek/kajla-nyar-a-mahart-fedelzeten",
                "benefit": "Kajla útlevéllel rendelkező gyerekek ingyenes utazása a Dunán",
                "routes": "Budapest-Szentendre, Visegrádi körjárat, Esztergomi sétahajó",
                "period": "Június 21 - augusztus 31",
            },
        }
        self._log("  BAHART és MAHART info hozzáadva")

    def _summary(self) -> dict:
        summary = {}
        for key in ["tripsData", "stampsData", "discountsData", "castlesData", "adventuresData", "bringaData"]:
            items = self.data.get(key, [])
            summary[key] = len(items)
        summary["boatInfo"] = "BAHART + MAHART"
        return summary


def main():
    agent = RefreshAgent()
    print("Kajla teljes adatfrissítés indítása...\n")

    summary = agent.refresh_all()

    print(f"\n{'=' * 40}")
    print("Összesítés:")
    for key, count in summary.items():
        print(f"  {key}: {count}")

    if "--save" in sys.argv:
        agent.save()
        print(f"\nAdatok mentve: {OUTPUT}")
    else:
        print(f"\nMentéshez használd: python3 -m api.refresh_agent --save")


if __name__ == "__main__":
    main()
