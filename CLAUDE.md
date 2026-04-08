# Kajla Kereső (Kajla Célpont Kereső)

## Projekt leírás

Interaktív térképes kereső alkalmazás a **"Hol vagy, Kajla?"** magyar családi turisztikai programhoz. A program a Magyar Turisztikai Ügynökség kezdeményezése, amelyben Kajla, a kíváncsi vizsla kalauzolja a gyerekeket Magyarország látnivalóihoz. A felhasználók öt kategóriában böngészhetnek helyszíneket térképen és listában.

### Kategóriák

| Kategória | Darabszám | Leírás |
|---|---|---|
| Kajla-körök | 42 | Családbarát természetjáró ösvények, parkok, arborétumok |
| Bringakörök | 10 | Kerékpáros túrák a Balaton körül, pecsételő állomásokkal |
| Kalandok | 11 | Városfelfedező kalandkönyvek (Budapest, Pécs, Sopron, Debrecen, stb.) |
| Várak és kastélyok | 22 | Történelmi várak és kastélyok az Apródok programban |
| Pecsételő helyek | ~890 | Pecsétgyűjtő pontok országszerte |

## Kajla program háttér

- **Hivatalos oldal:** https://kajla.hu
- **Kajla-körök:** https://kajla.hu/kajla-korok
- **Bringakörök:** https://kajla.hu/bringakorok
- **Kalandok:** https://kajla.hu/kajla-kalandok (város slugok: `/budapest`, `/pecs`, `/sopron`, `/debrecen`, `/nyiregyhaza`, `/balaton`, `/veszprem`, `/liget`)
- **Várak és kastélyok (Apródok):** https://kajla.hu/aprodok
- **Pecsételő ajánlatok:** https://kajla.hu/ajanlatok
- **Kajla útlevél info:** https://kajla.hu/pecsetgyujtes-utlevel (iskolás), https://kajla.hu/ovis-utlevel (óvodás)
- **Facebook közösség:** https://www.facebook.com/groups/1935560989924243/
- **NÖF Kajla oldal:** https://nof.hu/hu/kajla/

A program részeként a gyerekek Kajla útlevelet kapnak, amelybe pecséteket gyűjtenek a helyszíneken. Három ezüst karika egy arany karikára cserélhető. Az útlevéllel kedvezmények vehetők igénybe (szállás, fürdő, közlekedés).

## Tech stack

- **Vanilla JavaScript** - egyetlen `index.html` fájl (HTML + CSS + JS, ~2150 sor)
- **Leaflet 1.9.4** - interaktív térkép (CDN: unpkg)
- **Leaflet.markercluster 1.5.3** - marker csoportosítás
- **OpenStreetMap** tile layer
- **Python 3** scraper (`scrape.py`) az adatgyűjtéshez
- Nincs build rendszer, bundler, vagy package manager - statikus fájlkiszolgálás elegendő

## Projekt struktúra

```
index.html          - Teljes alkalmazás (HTML + CSS + JS egyben)
kajla_data.json     - Összes helyszínadat (~1.2 MB, scrape.py generálja)
scrape.py           - Adatgyűjtő script a kajla.hu-ról
photos/             - Vár/kastély fotók (1-22-photo.png)
stamps/             - Vár/kastély pecsétképek (1-22-stamp.png)
```

## Adatforrások

A `kajla_data.json` a következő adathalmazokat tartalmazza:
- `tripsData` - Kajla-körök (túrák)
- `stampsData` - Pecsételő helyek
- `discountsData` - Kedvezmények
- `castlesData` - Várak és kastélyok (geocodolt koordinátákkal)
- `adventuresData` - Kalandok állomásokkal (kajla.hu JSON API-kból: `kajla.hu/js/json/{city}-trip-quests.json`)
- `bringaData` - Bringakörök útvonal-geometriával

A scraper a kajla.hu oldalakról és API-jaiból gyűjti az adatokat, Nominatim geocoding-ot használ a várak koordinátáihoz, és irányítószám-alapú medián korrekciót alkalmaz a hibás koordinátákra.

## Fejlesztés

```bash
# Lokális futtatás (bármilyen statikus szerver)
python3 -m http.server 8000
# majd: http://localhost:8000

# Adatok frissítése a kajla.hu-ról
python3 scrape.py
```

## Alkalmazás működése

1. **Kategória választó** - Nyitóképernyő 5 kártyával
2. **Térkép + lista nézet** - Bal oldalt szűrhető lista, jobb oldalt Leaflet térkép
3. **Szűrők** - Kategóriánként eltérő szűrők (régió, szabad szöveges keresés, kalandoknál kaszkád dropdown-ok)
4. **Részletek panel** - Kiválasztott elem részletei slide-in panelben
5. **Térkép szűrés** - A lista a látható térképterületre szűr (debounced zoomend/moveend)
6. **Mobil nézet** - Húzható bottom sheet a listához

## Kód konvenciók

- Magyar nyelv a UI-ban és a kommentekben
- Angol a változó- és függvénynevekben
- Egyetlen fájl architektúra (`index.html`) - minden CSS és JS inline
- DOM elemek `$('id')` helper-rel kezelve
- Koordináták validálása: lat 45-49, lon 16-23 (Magyarország határai)
- Git commit üzenetek angolul

## Repository

- **GitHub:** https://github.com/vinterpeter/kajla-kereso
- **Branch:** main
