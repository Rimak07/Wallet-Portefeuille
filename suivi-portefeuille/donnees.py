"""Lecture du portefeuille et récupération des prix.

Règle d'or : on n'invente JAMAIS un chiffre. Chaque prix a une source
("marché", "manuel" ou "DÉMO") et, s'il n'y a pas de prix, on le dit.
"""
import csv
import json
import random
import time
from datetime import date, timedelta
from pathlib import Path

import config

COLONNES_OBLIGATOIRES = ["ticker", "secteur", "quantite", "prix_achat", "devise"]


# ---------- Lecture du fichier du portefeuille (étape 2) ----------
def nombre(texte):
    """Convertit '2 850,50' ou '2850.50' en nombre. Retourne None si c'est vide."""
    if texte is None:
        return None
    texte = texte.strip().replace(" ", "").replace("\u00a0", "").replace(",", ".")
    if texte == "":
        return None
    return float(texte)


def lire_portefeuille(chemin):
    chemin = Path(chemin)
    if not chemin.exists():
        raise FileNotFoundError(f"Fichier introuvable : {chemin}")

    with open(chemin, encoding="utf-8-sig", newline="") as f:
        lignes = [l for l in f if l.strip() and not l.lstrip().startswith("#")]
    if not lignes:
        raise ValueError("Le fichier du portefeuille est vide.")

    # Excel en français sauvegarde les CSV avec des ; : on accepte les deux
    separateur = ";" if lignes[0].count(";") > lignes[0].count(",") else ","
    lecteur = csv.DictReader(lignes, delimiter=separateur)
    lecteur.fieldnames = [c.strip().lower() for c in lecteur.fieldnames]

    manquantes = [c for c in COLONNES_OBLIGATOIRES if c not in lecteur.fieldnames]
    if manquantes:
        raise ValueError(f"Colonnes manquantes dans le fichier : {', '.join(manquantes)}")

    positions = []
    for numero, ligne in enumerate(lecteur, start=1):
        try:
            p = {
                "ticker": ligne["ticker"].strip().upper(),
                "nom": (ligne.get("nom") or "").strip(),
                "secteur": (ligne.get("secteur") or "").strip() or "Non classé",
                "quantite": nombre(ligne["quantite"]),
                "prix_achat": nombre(ligne["prix_achat"]),
                "devise": ligne["devise"].strip().upper(),
                "prix_manuel": nombre(ligne.get("prix_manuel")),
            }
        except (ValueError, AttributeError) as erreur:
            raise ValueError(f"Titre n° {numero} du fichier : valeur invalide ({erreur})")
        if not p["ticker"] or not p["devise"] or p["quantite"] is None or p["prix_achat"] is None:
            raise ValueError(f"Titre n° {numero} du fichier : ticker, quantité, prix d'achat et devise sont obligatoires.")
        positions.append(p)

    # Si un titre apparaît deux fois (deux achats), on les fusionne
    fusion = {}
    for p in positions:
        t = p["ticker"]
        if t not in fusion:
            fusion[t] = p
            continue
        a = fusion[t]
        if a["devise"] != p["devise"]:
            raise ValueError(f"{t} apparaît avec deux devises différentes ({a['devise']} et {p['devise']}).")
        total = a["quantite"] + p["quantite"]
        if total:
            a["prix_achat"] = (a["quantite"] * a["prix_achat"] + p["quantite"] * p["prix_achat"]) / total
        a["quantite"] = total
    return list(fusion.values())


# ---------- Prix du marché (étape 3) ----------
def _historique_yahoo(symbole, periode):
    # Importé ici pour que le mode démo fonctionne même sans yfinance installé
    import yfinance as yf

    h = yf.Ticker(symbole).history(period=periode, interval="1d", auto_adjust=False)
    if h is None or h.empty:
        raise ValueError("aucune donnée reçue de Yahoo Finance")
    serie = h["Close"].dropna()
    if serie.empty:
        raise ValueError("aucun prix de clôture reçu")
    return [(d.strftime("%Y-%m-%d"), float(c)) for d, c in serie.items()]


def _obtenir(symbole, periode, aujourdhui, utiliser_cache):
    """Va chercher un historique de prix, avec un cache d'une journée pour ne pas surcharger Yahoo."""
    fichier = config.DOSSIER_CACHE / f"{symbole}_{periode}_{aujourdhui}.json"
    if utiliser_cache and fichier.exists():
        return json.loads(fichier.read_text(encoding="utf-8"))
    time.sleep(0.5)  # politesse envers le serveur
    historique = _historique_yahoo(symbole, periode)
    if utiliser_cache:
        config.DOSSIER_CACHE.mkdir(exist_ok=True)
        fichier.write_text(json.dumps(historique), encoding="utf-8")
    return historique


def _taux_change(devise, aujourdhui, demo, utiliser_cache):
    base = config.DEVISE_BASE
    if devise == base:
        return {"taux": 1.0, "source": "—"}
    if demo:
        return {"taux": {"USD": 1.35, "EUR": 1.5}.get(devise, 1.2), "source": "DÉMO"}
    try:
        historique = _obtenir(f"{devise}{base}=X", "5d", aujourdhui, utiliser_cache)
        return {"taux": historique[-1][1], "source": "marché"}
    except Exception:
        manuel = config.TAUX_MANUELS.get(devise)
        if manuel:
            return {"taux": manuel, "source": "manuel"}
        return None


def charger_marche(positions, aujourdhui, demo=False, utiliser_cache=True):
    """Retourne (marche, taux, avertissements).

    marche[ticker] = {"prix", "date", "source", "historique"} ou None si aucun prix.
    """
    marche, taux, avertissements = {}, {}, []

    for p in positions:
        t = p["ticker"]
        try:
            if demo:
                historique = _historique_demo(t, aujourdhui, p["prix_achat"])
                source = "DÉMO"
            else:
                historique = _obtenir(t, config.PERIODE_HISTORIQUE, aujourdhui, utiliser_cache)
                source = "marché"
            derniere_date, dernier_prix = historique[-1][0], historique[-1][1]
            marche[t] = {"prix": dernier_prix, "date": derniere_date, "source": source, "historique": historique}
            age = (aujourdhui - date.fromisoformat(derniere_date)).days
            if source == "marché" and age > config.JOURS_PRIX_PERIME:
                avertissements.append(f"{t} : le dernier prix date du {derniere_date} (il y a {age} jours).")
        except Exception as erreur:
            if p["prix_manuel"] is not None:
                marche[t] = {"prix": p["prix_manuel"], "date": None, "source": "manuel", "historique": []}
                avertissements.append(f"{t} : prix du marché indisponible ({erreur}). Prix manuel utilisé, non vérifié.")
            else:
                marche[t] = None
                avertissements.append(f"{t} : prix indisponible ({erreur}) et aucun prix_manuel. Titre exclu des calculs.")

    for devise in sorted({p["devise"] for p in positions}):
        taux[devise] = _taux_change(devise, aujourdhui, demo, utiliser_cache)
        if taux[devise] is None:
            avertissements.append(
                f"Taux de change {devise}→{config.DEVISE_BASE} indisponible : les titres en {devise} sont exclus "
                f"(tu peux le donner à la main dans config.TAUX_MANUELS)."
            )
        elif taux[devise]["source"] == "manuel":
            avertissements.append(f"Taux {devise}→{config.DEVISE_BASE} : valeur manuelle utilisée, non vérifiée.")

    return marche, taux, avertissements


# ---------- Mode démo : des données FICTIVES pour tester sans internet ----------
def _jours_ouvrables(fin, n):
    jours, d = [], fin
    while len(jours) < n:
        if d.weekday() < 5:
            jours.append(d)
        d -= timedelta(days=1)
    return list(reversed(jours))


def _historique_demo(ticker, aujourdhui, prix_ref, nb_jours=250):
    commun = random.Random(f"marche-{aujourdhui}")      # le "marché" fictif, commun à tous les titres
    propre = random.Random(f"{ticker}-{aujourdhui}")    # la part propre à chaque titre
    sigma = 0.008 + (sum(ord(c) for c in ticker) % 15) / 1000
    prix = (prix_ref or 100.0) * propre.uniform(0.85, 1.15)
    historique = []
    for jour in _jours_ouvrables(aujourdhui, nb_jours):
        rendement = 0.6 * commun.gauss(0.0003, 0.008) + propre.gauss(0, sigma)
        prix = max(prix * (1 + rendement), 0.01)
        historique.append((jour.isoformat(), round(prix, 2)))
    return historique