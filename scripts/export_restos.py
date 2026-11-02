"""Convertit le tableur de suivi (data/restos.xlsx) en data/restos.json pour l'app.

Usage :  python scripts/export_restos.py [chemin/vers/restos.xlsx]

Seules les colonnes « terrain » (vertes) sont exportées. Les colonnes « Ce que dit
le web » ne sortent jamais du tableur : elles ne sont pas vérifiées.
"""
import json
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "restos.xlsx"
OUT = ROOT / "data" / "restos.json"

# Statut du tableur -> clé utilisée par l'app. None = jamais affiché.
STATUTS = {
    "À vérifier": "a_verifier",
    "Certifié ✓": "certifie",
    "Fournisseur certifié": "fournisseur",
    "Déclaré sans certificat": "declare",
    "Pas halal": None,
    "Fermé": None,
}


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def fmt(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%d/%m/%Y")
    return str(value).strip()


def main():
    ws = load_workbook(SRC, data_only=True)["Restos"]
    rows = ws.iter_rows(values_only=True)
    head = [fmt(h) for h in next(rows)]
    col = {name: i for i, name in enumerate(head)}

    def get(row, name):
        return fmt(row[col[name]]) if name in col else ""

    restos, ids = [], set()
    for row in rows:
        nom = get(row, "Nom")
        if not nom:
            continue
        statut_brut = get(row, "STATUT VÉRIFIÉ") or "À vérifier"
        if statut_brut not in STATUTS:
            print(f"! Statut inconnu pour {nom} : {statut_brut!r} (ligne ignorée)")
            continue
        statut = STATUTS[statut_brut]
        if statut is None:
            continue
        rid = slug(nom)
        while rid in ids:
            rid += "-2"
        ids.add(rid)
        adresse = get(row, "Adresse")
        accord = get(row, "Accord publication certificat") == "Oui"
        resto = {
            "id": rid,
            "nom": nom,
            "adresse": "" if adresse.lower().startswith("adresse à trouver") else adresse,
            "cuisine": get(row, "Cuisine"),
            "statut": statut,
            "verifie_le": get(row, "Date vérif sur place"),
        }
        if statut in ("certifie", "fournisseur"):
            resto["organisme"] = get(row, "Organisme")
            resto["validite"] = get(row, "Validité certificat")
            photo = get(row, "Fichier certificat")
            if accord and photo:
                resto["certificat"] = f"certificats/{photo}"
        if statut == "declare":
            resto["raison"] = get(row, "Raison / source si pas de certificat")
        alcool = get(row, "Alcool servi")
        if alcool in ("Oui", "Non"):
            resto["alcool"] = alcool == "Oui"
        lat, lng = get(row, "Latitude"), get(row, "Longitude")
        if lat and lng:
            resto["lat"], resto["lng"] = float(lat.replace(",", ".")), float(lng.replace(",", "."))
        restos.append(resto)

    payload = {"zone": "Le Kremlin-Bicêtre", "maj": date.today().strftime("%d/%m/%Y"), "restos": restos}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(restos)} restos exportés vers {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
