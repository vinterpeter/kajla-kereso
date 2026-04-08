"""Kajla.hu/ajanlatok scraper agent.

Kinyeri az összes adatot a kajla.hu/ajanlatok oldalról:
- tripsData (Kajla-körök / túrák)
- stampsData (Pecsételő helyek)
- discountsData (Kedvezmények)

Támogatja az összes szűrési lehetőséget amit az oldal kínál.
"""

import json
import re
import urllib.request
from dataclasses import dataclass, field

USER_AGENT = "KajlaScraperAgent/1.0"
SOURCE_URL = "https://kajla.hu/ajanlatok"


@dataclass
class KajlaAgent:
    """Agent a kajla.hu/ajanlatok adatainak kinyerésére és szűrésére."""

    trips: list[dict] = field(default_factory=list)
    stamps: list[dict] = field(default_factory=list)
    discounts: list[dict] = field(default_factory=list)
    _loaded: bool = False

    def fetch_all(self) -> dict[str, int]:
        """Letölti az összes adatot a kajla.hu/ajanlatok-ról.

        Returns: dict a kinyert elemek számával kategóriánként.
        """
        html = self._fetch_url(SOURCE_URL)
        if not html:
            raise ConnectionError(f"Nem sikerült letölteni: {SOURCE_URL}")

        results = {}
        for varname, attr in [
            ("tripsData", "trips"),
            ("stampsData", "stamps"),
            ("discountsData", "discounts"),
        ]:
            pattern = r"window\." + varname + r"\s*=\s*(\[.*?\]);"
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                    setattr(self, attr, parsed)
                    results[varname] = len(parsed)
                except json.JSONDecodeError:
                    results[varname] = 0
            else:
                results[varname] = 0

        self._loaded = True
        return results

    # ---- Szűrő metódusok ----

    def filter_trips(
        self,
        county: str | None = None,
        city: str | None = None,
        search: str | None = None,
        max_duration: float | None = None,
        max_length: float | None = None,
        max_difficulty: int | None = None,
        parking: bool | None = None,
        toilet: bool | None = None,
        buffet: bool | None = None,
        dog_allowed: bool | None = None,
        carriage: bool | None = None,
        free_only: bool = False,
        active_only: bool = True,
    ) -> list[dict]:
        """Kajla-körök szűrése.

        Args:
            county: Vármegye neve (részleges egyezés)
            city: Város neve (részleges egyezés)
            search: Szabad szöveges keresés (név, leírás)
            max_duration: Max időtartam órában
            max_length: Max táv km-ben
            max_difficulty: Max nehézség (1-5)
            parking: Van-e parkoló
            toilet: Van-e mosdó
            buffet: Van-e büfé
            dog_allowed: Kutyabarát-e
            carriage: Babakocsival járható-e
            free_only: Csak ingyenesek
            active_only: Csak aktív túrák
        """
        results = []
        for t in self.trips:
            if active_only and (t.get("active") != 1 or t.get("status") != 1):
                continue
            if county and county.lower() not in (t.get("county") or "").lower():
                continue
            if city and city.lower() not in (t.get("city") or "").lower():
                continue
            if search:
                q = search.lower()
                name = (t.get("name") or t.get("trip_name") or "").lower()
                desc = (t.get("description") or "").lower()
                if q not in name and q not in desc:
                    continue
            if max_duration and _to_float(t.get("duration"), 99) > max_duration:
                continue
            if max_length and _to_float(t.get("length"), 99) > max_length:
                continue
            if max_difficulty and _to_int(t.get("difficulty"), 5) > max_difficulty:
                continue
            if parking is not None and bool(t.get("parking")) != parking:
                continue
            if toilet is not None and bool(t.get("toilet")) != toilet:
                continue
            if buffet is not None and bool(t.get("buffet")) != buffet:
                continue
            if dog_allowed is not None and bool(t.get("dog_allowed")) != dog_allowed:
                continue
            if carriage is not None and bool(t.get("carriage")) != carriage:
                continue
            if free_only and t.get("paid", 0) != 0:
                continue
            results.append(t)
        return results

    def filter_stamps(
        self,
        county: str | None = None,
        city: str | None = None,
        search: str | None = None,
        postcard: bool | None = None,
        museum: bool | None = None,
        active_only: bool = True,
    ) -> list[dict]:
        """Pecsételő helyek szűrése.

        Args:
            county: Vármegye (részleges)
            city: Város (részleges)
            search: Keresés névben
            postcard: Van-e képeslap
            museum: Múzeum-e
            active_only: Csak aktívak
        """
        results = []
        for s in self.stamps:
            if active_only and (s.get("active") != 1 or s.get("status") != 1):
                continue
            if county and county.lower() not in (s.get("county") or "").lower():
                continue
            if city and city.lower() not in (s.get("city") or "").lower():
                continue
            if search and search.lower() not in (s.get("name") or "").lower():
                continue
            if postcard is not None and bool(s.get("postcard")) != postcard:
                continue
            if museum is not None and bool(s.get("museum")) != museum:
                continue
            results.append(s)
        return results

    def filter_discounts(
        self,
        county: str | None = None,
        city: str | None = None,
        search: str | None = None,
    ) -> list[dict]:
        """Kedvezmények szűrése.

        Args:
            county: Vármegye (részleges)
            city: Város (részleges)
            search: Keresés névben/leírásban
        """
        results = []
        for d in self.discounts:
            if county and county.lower() not in (d.get("county") or "").lower():
                continue
            if city and city.lower() not in (d.get("city") or "").lower():
                continue
            if search:
                q = search.lower()
                name = (d.get("discount_name") or d.get("venue") or "").lower()
                desc = (d.get("discount_description") or "").lower()
                if q not in name and q not in desc:
                    continue
            results.append(d)
        return results

    # ---- Összesítő lekérdezések ----

    def get_counties(self) -> list[str]:
        """Összes elérhető vármegye listája."""
        counties = set()
        for dataset in [self.trips, self.stamps, self.discounts]:
            for item in dataset:
                c = (item.get("county") or "").strip()
                if c:
                    counties.add(c)
        return sorted(counties)

    def get_cities(self, county: str | None = None) -> list[str]:
        """Összes elérhető város (opcionálisan vármegyére szűrve)."""
        cities = set()
        for dataset in [self.trips, self.stamps, self.discounts]:
            for item in dataset:
                if county and county.lower() not in (item.get("county") or "").lower():
                    continue
                c = (item.get("city") or "").strip()
                if c:
                    cities.add(c)
        return sorted(cities)

    def get_stats(self) -> dict:
        """Összesítő statisztikák."""
        active_trips = [t for t in self.trips if t.get("active") == 1 and t.get("status") == 1]
        active_stamps = [s for s in self.stamps if s.get("active") == 1 and s.get("status") == 1]
        return {
            "trips_total": len(self.trips),
            "trips_active": len(active_trips),
            "stamps_total": len(self.stamps),
            "stamps_active": len(active_stamps),
            "discounts_total": len(self.discounts),
            "counties": len(self.get_counties()),
            "amenities": {
                "with_parking": sum(1 for t in active_trips if t.get("parking")),
                "with_toilet": sum(1 for t in active_trips if t.get("toilet")),
                "with_buffet": sum(1 for t in active_trips if t.get("buffet")),
                "dog_friendly": sum(1 for t in active_trips if t.get("dog_allowed")),
                "stroller_ok": sum(1 for t in active_trips if t.get("carriage")),
            },
        }

    # ---- Segédfüggvények ----

    @staticmethod
    def _fetch_url(url: str) -> str | None:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=30)
            return resp.read().decode("utf-8", errors="replace")
        except Exception:
            return None


def _to_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _to_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


# ---- Standalone használat ----
if __name__ == "__main__":
    agent = KajlaAgent()
    print("Adatok letöltése...")
    counts = agent.fetch_all()
    print(f"Letöltve: {counts}")
    print(f"\nStatisztikák: {json.dumps(agent.get_stats(), indent=2, ensure_ascii=False)}")
    print(f"\nVármegyék: {agent.get_counties()}")

    # Példa szűrések
    print("\n--- Heves megyei túrák, kutyabarát ---")
    for t in agent.filter_trips(county="heves", dog_allowed=True):
        print(f"  {t.get('name')} ({t.get('city')})")

    print("\n--- Budapesti pecsételő helyek ---")
    bp_stamps = agent.filter_stamps(city="budapest")
    print(f"  {len(bp_stamps)} db")

    print("\n--- Kedvezmények 'fürdő' keresésre ---")
    for d in agent.filter_discounts(search="fürdő"):
        print(f"  {d.get('discount_name') or d.get('venue')} ({d.get('city')})")
