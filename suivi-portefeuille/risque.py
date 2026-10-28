"""Mesures de risque (étape 4), calculées en Python pur à partir de l'historique des prix.

Ce sont des FAITS sur le passé, jamais des prévisions.
"""
import math
import statistics

import config
from formats import fmt


def rendements(historique):
    """Transforme une liste (date, prix) en {date: rendement du jour}."""
    sortie = {}
    for (_, p0), (d1, p1) in zip(historique, historique[1:]):
        if p0 > 0:
            sortie[d1] = p1 / p0 - 1
    return sortie


def volatilite_annualisee(valeurs):
    """Écart-type des rendements journaliers, ramené à une année (en %)."""
    if len(valeurs) < 2:
        return None
    return statistics.stdev(valeurs) * math.sqrt(config.JOURS_BOURSE_PAR_AN) * 100


def baisse_maximale(valeurs):
    """Pire baisse entre un sommet et le creux suivant (en %, négatif)."""
    valeur = sommet = 1.0
    pire = 0.0
    for r in valeurs:
        valeur *= 1 + r
        sommet = max(sommet, valeur)
        pire = min(pire, valeur / sommet - 1)
    return pire * 100


def _correlation(a, b):
    try:
        return statistics.correlation(a, b)
    except statistics.StatisticsError:
        return None


def calculer(resultats, marche):
    par_titre, series, exclus = {}, {}, []

    for r in resultats:
        if r["valeur"] is None:
            continue
        t = r["ticker"]
        historique = marche[t]["historique"] if marche.get(t) else []
        if len(historique) < config.MIN_JOURS_RISQUE + 1:
            exclus.append((t, "historique de prix insuffisant"))
            continue
        rend = rendements(historique)
        series[t] = rend
        valeurs = [rend[d] for d in sorted(rend)]
        par_titre[t] = {
            "volatilite": volatilite_annualisee(valeurs),
            "baisse_max": baisse_maximale(valeurs),
            "jours": len(valeurs),
        }

    portefeuille = None
    correlation_moyenne = None
    if series:
        dates = sorted(set.intersection(*(set(s) for s in series.values())))
        if len(dates) >= config.MIN_JOURS_RISQUE:
            poids_couvert = sum(r["poids"] for r in resultats if r["ticker"] in series)
            w = {r["ticker"]: r["poids"] / poids_couvert for r in resultats if r["ticker"] in series}
            rp = [sum(w[t] * series[t][d] for t in series) for d in dates]
            portefeuille = {
                "volatilite": volatilite_annualisee(rp),
                "baisse_max": baisse_maximale(rp),
                "jours": len(dates),
                "titres_inclus": len(series),
                "poids_couvert": poids_couvert,
            }
            tickers = list(series)
            paires = []
            for i in range(len(tickers)):
                for j in range(i + 1, len(tickers)):
                    c = _correlation([series[tickers[i]][d] for d in dates],
                                     [series[tickers[j]][d] for d in dates])
                    if c is not None:
                        paires.append(c)
            if paires:
                correlation_moyenne = sum(paires) / len(paires)
        else:
            exclus.append(("portefeuille", "pas assez de jours communs entre les titres"))

    valides = [r for r in resultats if r["poids"] is not None]
    hhi = sum((r["poids"] / 100) ** 2 for r in valides)
    return {
        "par_titre": par_titre,
        "portefeuille": portefeuille,
        "correlation_moyenne": correlation_moyenne,
        "hhi": hhi if valides else None,
        "n_effectif": 1 / hhi if hhi else None,   # "nombre équivalent de titres égaux"
        "exclus": exclus,
    }


def observations_risque(risques):
    """Règles simples sur le risque. Retourne une liste de (clé, texte)."""
    obs = []
    for t, m in risques["par_titre"].items():
        if m["volatilite"] is not None and m["volatilite"] > config.SEUIL_VOLATILITE:
            obs.append((f"volatilite:{t}",
                        f"{t} a une volatilité annualisée de {fmt(m['volatilite'], 1, ' %')} (seuil choisi : {config.SEUIL_VOLATILITE} %)."))
    c = risques["correlation_moyenne"]
    if c is not None and c > config.SEUIL_CORRELATION:
        obs.append(("correlation",
                    f"Les titres ont évolué ensemble (corrélation moyenne de {fmt(c, 2)}, seuil choisi : {config.SEUIL_CORRELATION}) : "
                    f"la diversification a été limitée sur cette période."))
    return obs