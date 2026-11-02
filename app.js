// Halal KB — app sans build : lit data/restos.json et affiche liste, carte et fiches.

const CONFIG = {
  // Adresse qui reçoit les « Signaler une erreur ». Vide = bouton masqué.
  contactEmail: "",
  centre: [48.8105, 2.3605], // Le Kremlin-Bicêtre
  codePostal: "94270",
  ville: "Le Kremlin-Bicêtre",
};

const STATUTS = {
  certifie: { label: "Certifié ✓", couleur: "--certifie" },
  fournisseur: { label: "Fournisseur certifié", couleur: "--fournisseur" },
  declare: { label: "Halal déclaré, sans certificat", couleur: "--declare" },
  a_verifier: { label: "En cours de vérification", couleur: "--a_verifier" },
};

let restos = [];
let filtre = "tous";
let carte = null;
const marqueurs = new Map();

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const badge = (statut) => `<span class="badge ${statut}">${STATUTS[statut].label}</span>`;
const couleur = (statut) => getComputedStyle(document.documentElement).getPropertyValue(STATUTS[statut].couleur).trim();

function stockage(cle, valeur) {
  try {
    if (valeur === undefined) return JSON.parse(localStorage.getItem(cle) || "null");
    localStorage.setItem(cle, JSON.stringify(valeur));
  } catch { return null; }
}

// ---------- Filtres ----------
function rendreFiltres() {
  const options = [["tous", "Tous"], ...Object.entries(STATUTS).map(([k, v]) => [k, v.label])];
  $("#filters").innerHTML = options
    .filter(([k]) => k === "tous" || restos.some((r) => r.statut === k))
    .map(([k, label]) => `<button class="chip" data-filtre="${k}" aria-pressed="${k === filtre}">${esc(label)}</button>`)
    .join("");
}

$("#filters").addEventListener("click", (e) => {
  const b = e.target.closest("[data-filtre]");
  if (!b) return;
  filtre = b.dataset.filtre;
  rendreFiltres();
  rendreListe();
  rendreMarqueurs();
});

const visibles = () => restos.filter((r) => filtre === "tous" || r.statut === filtre);

// ---------- Liste ----------
function rendreListe() {
  const liste = visibles();
  $("#vue-liste").innerHTML = liste.length
    ? liste.map((r) => `
        <button class="card" data-id="${esc(r.id)}">
          <h2>${esc(r.nom)}</h2>
          <p class="meta">${esc(r.cuisine)}${r.adresse ? " · " + esc(r.adresse) : ""}</p>
          ${badge(r.statut)}
        </button>`).join("")
    : `<p class="vide">Aucun resto dans cette catégorie pour l'instant.</p>`;
}

$("#vue-liste").addEventListener("click", (e) => {
  const c = e.target.closest("[data-id]");
  if (c) location.hash = c.dataset.id;
});

// ---------- Fiche ----------
function ouvrirFiche(id) {
  const r = restos.find((x) => x.id === id);
  if (!r) return;
  const lignes = [
    ["Cuisine", r.cuisine],
    ["Adresse", r.adresse],
    r.organisme && ["Organisme", r.organisme],
    r.validite && ["Valide jusqu'au", r.validite],
    r.alcool !== undefined && ["Alcool", r.alcool ? "Servi sur place" : "Pas d'alcool"],
    ["Vérifié sur place", r.verifie_le || "Pas encore"],
  ].filter((l) => l && l[1]);

  let source = "";
  if (r.statut === "certifie") source = `Certificat fourni par l'établissement${r.organisme ? ", délivré par " + esc(r.organisme) : ""}, vu sur place le ${esc(r.verifie_le)}.`;
  if (r.statut === "fournisseur") source = `Seule la viande (le fournisseur) est certifiée${r.organisme ? " par " + esc(r.organisme) : ""}. Le restaurant lui-même n'a pas de certificat.`;
  if (r.statut === "declare") source = r.raison ? esc(r.raison) : "Le restaurant se déclare halal, sans certificat.";
  if (r.statut === "a_verifier") source = "Ce restaurant n'a pas encore été vérifié sur place. Repassez bientôt !";

  const adresseComplete = encodeURIComponent(`${r.nom}, ${r.adresse}, ${CONFIG.codePostal} ${CONFIG.ville}`);
  const signaler = CONFIG.contactEmail
    ? `<a class="btn" href="mailto:${CONFIG.contactEmail}?subject=${encodeURIComponent("Erreur fiche : " + r.nom)}">Signaler une erreur</a>`
    : "";

  $("#fiche-contenu").innerHTML = `
    <h2 id="fiche-nom">${esc(r.nom)}</h2>
    ${badge(r.statut)}
    <dl>${lignes.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}</dl>
    <p class="source">${source}</p>
    ${r.certificat ? `<img class="certif-img" src="${esc(r.certificat)}" alt="Certificat halal de ${esc(r.nom)}">` : ""}
    <div class="actions">
      ${r.adresse ? `<a class="btn primary" target="_blank" rel="noopener" href="https://www.google.com/maps/search/?api=1&query=${adresseComplete}">Itinéraire</a>` : ""}
      ${signaler}
    </div>`;
  const d = $("#fiche");
  if (!d.open) d.showModal();
}

$("#fiche").addEventListener("close", () => {
  if (location.hash.length > 1) history.replaceState(null, "", location.pathname + location.search);
});

function suivreHash() {
  const m = location.hash.match(/^#([a-z0-9-]+)$/);
  if (m) ouvrirFiche(decodeURIComponent(m[1]));
  else if ($("#fiche").open) $("#fiche").close();
}
window.addEventListener("hashchange", suivreHash);

// ---------- Carte ----------
async function geocoder(r) {
  if (r.lat && r.lng) return [r.lat, r.lng];
  if (!r.adresse) return null;
  const cache = stockage("geo") || {};
  const cle = r.adresse;
  if (cache[cle]) return cache[cle];
  try {
    const url = `https://api-adresse.data.gouv.fr/search/?q=${encodeURIComponent(r.adresse)}&postcode=${CONFIG.codePostal}&limit=1`;
    const res = await fetch(url);
    const f = (await res.json()).features?.[0];
    if (!f) return null;
    const pos = [f.geometry.coordinates[1], f.geometry.coordinates[0]];
    cache[cle] = pos;
    stockage("geo", cache);
    return pos;
  } catch { return null; }
}

function initCarte() {
  if (carte) return;
  if (typeof L === "undefined") {
    $("#vue-carte").innerHTML = `<p class="vide">La carte n'est pas disponible ici. Ouvre la version en ligne de l'app pour la voir.</p>`;
    return;
  }
  carte = L.map("map").setView(CONFIG.centre, 15);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(carte);
  restos.forEach(async (r) => {
    const pos = await geocoder(r);
    if (!pos) return;
    const icone = L.divIcon({ className: "", html: `<div class="pin" style="background:${couleur(r.statut)}"></div>`, iconSize: [16, 16] });
    const m = L.marker(pos, { icon: icone, title: r.nom })
      .bindPopup(`<strong>${esc(r.nom)}</strong><br>${STATUTS[r.statut].label}<br><button data-id="${esc(r.id)}">Voir la fiche</button>`);
    marqueurs.set(r.id, m);
    rendreMarqueurs();
  });
  carte.on("popupopen", (e) => {
    e.popup.getElement().querySelector("[data-id]")?.addEventListener("click", (ev) => {
      location.hash = ev.target.dataset.id;
    });
  });
}

function rendreMarqueurs() {
  if (!carte) return;
  const ids = new Set(visibles().map((r) => r.id));
  marqueurs.forEach((m, id) => (ids.has(id) ? m.addTo(carte) : m.remove()));
}

// ---------- Onglets ----------
function montrer(vue) {
  const carteActive = vue === "carte";
  $("#vue-liste").hidden = carteActive;
  $("#vue-carte").hidden = !carteActive;
  $("#tab-liste").setAttribute("aria-selected", !carteActive);
  $("#tab-carte").setAttribute("aria-selected", carteActive);
  if (carteActive) { initCarte(); if (carte) setTimeout(() => carte.invalidateSize(), 0); }
}
$("#tab-liste").addEventListener("click", () => montrer("liste"));
$("#tab-carte").addEventListener("click", () => montrer("carte"));

// ---------- Démarrage ----------
const ORDRE = ["certifie", "fournisseur", "declare", "a_verifier"];

// window.HALAL_DATA permet d'embarquer les données directement dans la page (démo hors ligne).
(window.HALAL_DATA ? Promise.resolve(window.HALAL_DATA) : fetch("data/restos.json", { cache: "no-cache" }).then((r) => r.json()))
  .then((data) => {
    restos = data.restos.sort((a, b) => ORDRE.indexOf(a.statut) - ORDRE.indexOf(b.statut) || a.nom.localeCompare(b.nom, "fr"));
    $("#maj").textContent = `Mise à jour : ${data.maj} · ${restos.length} restos`;
    rendreFiltres();
    rendreListe();
    suivreHash();
  })
  .catch(() => { $("#vue-liste").innerHTML = `<p class="vide">Impossible de charger les restos.</p>`; });
