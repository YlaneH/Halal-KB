"""Enrichit le tableur avec OpenStreetMap et la Base Adresse Nationale.

Usage :  python scripts/import_osm.py [chemin/vers/restos.xlsx]

1. Interroge l'API Overpass (OpenStreetMap) : tous les restos, fast-foods et cafés
   du Kremlin-Bicêtre, avec leurs coordonnées et leur tag « diet:halal ».
2. Remplit Latitude / Longitude des restos du tableur reconnus par leur nom.
3. Ajoute en « À vérifier » les restos que OSM marque halal et qui manquent au tableur.
4. Pour les restos encore sans coordonnées, géocode l'adresse avec api-adresse.data.gouv.fr.

Rien n'est publié : relance ensuite scripts/export_restos.py.
Pour tester sans réseau : --overpass fichier.json (réponse Overpass enregistrée) --sans-ban.
"""
import argparse
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
OVERPASS = "https://overpass-api.de/api/interpreter"
BAN = "https://api-adresse.data.gouv.fr/search/"
CODE_POSTAL = "94270"
QUERY = """
[out:json][timeout:60];
area["boundary"="administrative"]["name"="Le Kremlin-Bicêtre"]->.kb;
nwr(area.kb)["amenity"~"^(restaurant|fast_food|cafe)$"];
out center tags;
"""
UA = {"User-Agent": "halal-kb/0.1 (annuaire local de restos halal)"}


def norm(text):
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"\b(le|la|les|l|restaurant|resto|kb|kremlin|bicetre)\b", " ", text)
    return re.sub(r"[^a-z0-9]+", "", text)


def http_json(url, data=None):
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def lieux_osm(fichier=None):
    if fichier:
        brut = json.loads(Path(fichier).read_text(encoding="utf-8"))
    else:
        brut = http_json(OVERPASS, urllib.parse.urlencode({"data": QUERY}).encode())
    lieux = []
    for el in brut.get("elements", []):
        tags = el.get("tags", {})
        if not tags.get("name"):
            continue
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lng = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lng is None:
            continue
        adresse = " ".join(filter(None, [tags.get("addr:housenumber"), tags.get("addr:street")]))
        lieux.append({
            "nom": tags["name"],
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "halal": tags.get("diet:halal") in ("yes", "only"),
            "cuisine": tags.get("cuisine", "").replace(";", ", ").replace("_", " "),
            "adresse": adresse,
            "id": f"{el['type']}/{el['id']}",
        })
    return lieux


def geocoder(adresse):
    url = BAN + "?" + urllib.parse.urlencode({"q": adresse, "postcode": CODE_POSTAL, "limit": 1})
    feats = http_json(url).get("features", [])
    if not feats or feats[0]["properties"].get("score", 0) < 0.5:
        return None
    lng, lat = feats[0]["geometry"]["coordinates"]
    return round(lat, 6), round(lng, 6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx", nargs="?", default=ROOT / "data" / "restos.xlsx")
    ap.add_argument("--overpass", help="réponse Overpass enregistrée (test hors ligne)")
    ap.add_argument("--sans-ban", action="store_true", help="ne pas géocoder les adresses")
    args = ap.parse_args()

    wb = load_workbook(args.xlsx)
    ws = wb["Restos"]
    col = {c.value: c.column for c in ws[1]}
    lignes = [r for r in range(2, ws.max_row + 1) if ws.cell(r, col["Nom"]).value]
    par_nom = {}
    for r in lignes:
        for morceau in str(ws.cell(r, col["Nom"]).value).split("/"):
            par_nom.setdefault(norm(re.sub(r"\(.*?\)", "", morceau)), r)

    def sans_coord(r):
        return not ws.cell(r, col["Latitude"]).value

    lieux = lieux_osm(args.overpass)
    print(f"OpenStreetMap : {len(lieux)} lieux, dont {sum(l['halal'] for l in lieux)} marqués halal")

    places, ajouts = 0, []
    for lieu in lieux:
        r = par_nom.get(norm(lieu["nom"]))
        if r:
            if sans_coord(r):
                ws.cell(r, col["Latitude"]).value = lieu["lat"]
                ws.cell(r, col["Longitude"]).value = lieu["lng"]
                places += 1
        elif lieu["halal"]:
            ajouts.append(lieu)

    prochaine = max(lignes) + 1 if lignes else 2
    for lieu in ajouts:
        valeurs = {
            "Nom": lieu["nom"],
            "Adresse": lieu["adresse"] or "Adresse à trouver",
            "Cuisine": lieu["cuisine"] or "À préciser",
            "Ce que dit le web (non vérifié)": "Tagué halal sur OpenStreetMap",
            "Détail web": f"diet:halal sur OSM ({lieu['id']})",
            "Sources web": "openstreetmap.org",
            "STATUT VÉRIFIÉ": "À vérifier",
            "Latitude": lieu["lat"],
            "Longitude": lieu["lng"],
        }
        for k, v in valeurs.items():
            ws.cell(prochaine, col[k]).value = v
        prochaine += 1

    geocodes = 0
    if not args.sans_ban:
        for r in range(2, prochaine):
            adresse = str(ws.cell(r, col["Adresse"]).value or "")
            if not ws.cell(r, col["Nom"]).value or not sans_coord(r):
                continue
            if not re.match(r"^\d", adresse):  # pas de numéro : trop imprécis
                continue
            pos = geocoder(adresse.replace("av.", "avenue"))
            if pos:
                ws.cell(r, col["Latitude"]).value, ws.cell(r, col["Longitude"]).value = pos
                geocodes += 1

    wb.save(args.xlsx)
    print(f"{places} restos placés grâce à OSM, {len(ajouts)} restos halal ajoutés depuis OSM, {geocodes} adresses géocodées")
    for lieu in ajouts:
        print(f"  + {lieu['nom']} ({lieu['adresse'] or 'sans adresse'})")


if __name__ == "__main__":
    main()
