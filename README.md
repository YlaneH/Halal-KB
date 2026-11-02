# Halal KB

Les restos halal du Kremlin-Bicêtre, vérifiés sur place.

Web app sans build ni dépendance à installer : HTML, CSS et JavaScript, avec une carte
[Leaflet](https://leafletjs.com) et OpenStreetMap. Sur un téléphone, elle s'installe
sur l'écran d'accueil (« Ajouter à l'écran d'accueil »).

## Badges

| Badge | Signification |
|---|---|
| **Certifié ✓** | Certificat vu sur place, au nom du resto, en cours de validité |
| **Fournisseur certifié** | Seule la viande ou le fournisseur est certifié |
| **Halal déclaré, sans certificat** | Le resto se dit halal ; la raison et sa source sont affichées |
| **En cours de vérification** | Pas encore vérifié sur place |

Les restos marqués « Pas halal » ou « Fermé » dans le tableur ne sont jamais affichés.

## Mettre à jour les restos

1. Remplis le tableur `data/restos.xlsx` (onglet « Restos », colonnes vertes).
   Il n'est **pas** publié dans le dépôt (voir `.gitignore`) : garde-le sur ta machine.
2. Génère le fichier lu par l'app :
   ```bash
   pip install openpyxl
   python scripts/export_restos.py
   ```
3. Pour un certificat : dépose la photo dans `certificats/`, écris son nom dans la colonne
   « Fichier certificat » et mets « Accord publication certificat » à « Oui ».
4. Commit et push `data/restos.json` (et la photo).

Seules les colonnes vérifiées sur place sont exportées. Ce que dit le web ne sort jamais du tableur.

## Lancer en local

```bash
python -m http.server 8000
```

Puis ouvre http://localhost:8000. Un lien vers une fiche : `http://localhost:8000/#why-not`.

## Mettre en ligne (GitHub Pages)

Settings → Pages → Source : « Deploy from a branch », branche `main`, dossier `/ (root)`.

## À régler

- `contactEmail` dans `app.js` : adresse pour « Signaler une erreur » (le bouton est masqué tant qu'elle est vide).
- Mentions légales et CGU avant toute mise en ligne publique.
