"""Calculs de base du portefeuille (étape 1) : valeur, gains, poids, secteurs, concentration."""
import config
from formats import fmt


def analyser(positions, marche, taux):
    """Ajoute à chaque position sa valeur, son coût, son gain et sa source de prix.

    Une position sans prix (ou sans taux de change) est gardée mais marquée "exclusion".
    """
    resultats = []
    for p in positions:
        r = dict(p)  # copie de la fiche, pour y ajouter des calculs
        info = marche.get(p["ticker"])
        t = taux.get(p["devise"])
        r.update(prix=None, source_prix=None, date_prix=None, taux=None,
                 valeur=None, cout=None, gain=None, gain_pct=None, poids=None, exclusion=None)

        if info is None:
            r["exclusion"] = "prix indisponible"
        elif t is None:
            r["exclusion"] = f"taux de change {p['devise']}→{config.DEVISE_BASE} indisponible"
        else:
            r["prix"] = info["prix"]
            r["source_prix"] = info["source"]
            r["date_prix"] = info["date"]
            r["taux"] = t["taux"]
            r["valeur"] = p["quantite"] * info["prix"] * t["taux"]
            r["cout"] = p["quantite"] * p["prix_achat"] * t["taux"]
            r["gain"] = r["valeur"] - r["cout"]
            r["gain_pct"] = (info["prix"] / p["prix_achat"] - 1) * 100 if p["prix_achat"] else None
        resultats.append(r)
    return resultats


def resumer(resultats):
    valides = [r for r in resultats if r["valeur"] is not None]
    total = sum(r["valeur"] for r in valides)
    cout = sum(r["cout"] for r in valides)

    for r in valides:
        r["poids"] = r["valeur"] / total * 100 if total else 0.0

    secteurs = {}
    devises = {}
    for r in valides:
        secteurs[r["secteur"]] = secteurs.get(r["secteur"], 0) + r["valeur"]
        devises[r["devise"]] = devises.get(r["devise"], 0) + r["valeur"]

    def avec_poids(dictionnaire):
        triees = sorted(dictionnaire.items(), key=lambda x: x[1], reverse=True)
        return {nom: {"valeur": v, "poids": v / total * 100 if total else 0.0} for nom, v in triees}

    return {
        "valeur_totale": total,
        "cout_total": cout,
        "gain_total": total - cout,
        "gain_total_pct": (total / cout - 1) * 100 if cout else None,
        "secteurs": avec_poids(secteurs),
        "devises": avec_poids(devises),
        "nb_valides": len(valides),
        "nb_exclus": len(resultats) - len(valides),
    }


def observations_concentration(resultats, resume):
    """Règles simples sur la concentration. Retourne une liste de (clé, texte)."""
    obs = []
    for r in resultats:
        if r["poids"] is not None and r["poids"] > config.SEUIL_POSITION:
            obs.append((f"position:{r['ticker']}",
                        f"{r['ticker']} pèse {fmt(r['poids'], 1, ' %')} du portefeuille (seuil choisi : {config.SEUIL_POSITION} %)."))
    for secteur, s in resume["secteurs"].items():
        if s["poids"] > config.SEUIL_SECTEUR:
            obs.append((f"secteur:{secteur}",
                        f"Le secteur {secteur} pèse {fmt(s['poids'], 1, ' %')} du portefeuille (seuil choisi : {config.SEUIL_SECTEUR} %)."))
    return obs