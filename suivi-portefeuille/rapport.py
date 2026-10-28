"""Rapport (étape 5) : texte Markdown, historique des instantanés et comparaison hebdomadaire.

Le rapport sépare toujours :
  - les FAITS (données et calculs directs),
  - les OBSERVATIONS (règles simples appliquées par le code, avec leur seuil),
  - les LIMITES (ce que le rapport ne sait pas).
"""
import json
from datetime import date

import config
from formats import fmt

LIBELLES_ALERTES = {
    "position": "concentration du titre {}",
    "secteur": "concentration du secteur {}",
    "volatilite": "volatilité élevée de {}",
    "correlation": "corrélation moyenne élevée entre les titres",
}


def libelle_alerte(cle):
    genre, _, nom = cle.partition(":")
    return LIBELLES_ALERTES.get(genre, cle).format(nom)


# ---------- Instantanés (la mémoire du programme) ----------
def instantane(ctx):
    return {
        "date": ctx["date"].isoformat(),
        "mode": ctx["mode"],
        "devise": config.DEVISE_BASE,
        "valeur_totale": ctx["resume"]["valeur_totale"],
        "positions": {
            r["ticker"]: {
                "quantite": r["quantite"], "prix": r["prix"], "devise": r["devise"],
                "valeur": r["valeur"], "poids": r["poids"], "secteur": r["secteur"],
                "source_prix": r["source_prix"],
            }
            for r in ctx["resultats"] if r["valeur"] is not None
        },
        "alertes": [cle for cle, _ in ctx["observations"]],
    }


def sauvegarder_instantane(snap, dossier):
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / f"{snap['date']}.json"
    fichier.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    return fichier


def charger_precedent(dossier, aujourdhui):
    """Retourne l'instantané le plus proche d'il y a 7 jours (et antérieur à aujourd'hui)."""
    if not dossier.exists():
        return None
    cible = aujourdhui.toordinal() - 7
    candidats = []
    for f in dossier.glob("*.json"):
        try:
            d = date.fromisoformat(f.stem)
        except ValueError:
            continue
        if d < aujourdhui:
            candidats.append((abs(d.toordinal() - cible), d, f))
    if not candidats:
        return None
    candidats.sort()
    return json.loads(candidats[0][2].read_text(encoding="utf-8"))


# ---------- Comparaison avec le rapport précédent ----------
def comparer(actuel, precedent):
    devise = config.DEVISE_BASE
    v0, v1 = precedent["valeur_totale"], actuel["valeur_totale"]
    variation = (v1 / v0 - 1) * 100 if v0 else None
    lignes = []
    avant, apres = precedent["positions"], actuel["positions"]

    for t in sorted(set(avant) & set(apres)):
        a, b = avant[t], apres[t]
        if a["quantite"] != b["quantite"]:
            lignes.append(f"**{t}** : quantité modifiée ({a['quantite']:g} → {b['quantite']:g}). La valeur totale inclut ce changement.")
        if a["prix"] and b["prix"]:
            var_prix = (b["prix"] / a["prix"] - 1) * 100
            if abs(var_prix) >= config.SEUIL_VARIATION_PRIX:
                lignes.append(f"**{t}** : prix {fmt(var_prix, 1, ' %', True)} ({fmt(a['prix'])} → {fmt(b['prix'])} {b['devise']}).")
        if a["poids"] is not None and b["poids"] is not None:
            ecart = b["poids"] - a["poids"]
            if abs(ecart) >= config.SEUIL_VARIATION_POIDS:
                lignes.append(f"**{t}** : poids {fmt(a['poids'], 1, ' %')} → {fmt(b['poids'], 1, ' %')} ({fmt(ecart, 1, ' pts', True)}).")

    for t in sorted(set(apres) - set(avant)):
        lignes.append(f"**{t}** : nouveau dans le portefeuille ({fmt(apres[t]['valeur'])} {devise}).")
    for t in sorted(set(avant) - set(apres)):
        lignes.append(f"**{t}** : n'est plus dans le portefeuille (ou n'a plus de prix).")

    for cle in actuel["alertes"]:
        if cle not in precedent["alertes"]:
            lignes.append(f"Nouvelle observation : {libelle_alerte(cle)}.")
    for cle in precedent["alertes"]:
        if cle not in actuel["alertes"]:
            lignes.append(f"Observation disparue : {libelle_alerte(cle)}.")

    return {
        "date_ref": precedent["date"],
        "jours": (date.fromisoformat(actuel["date"]) - date.fromisoformat(precedent["date"])).days,
        "valeur_avant": v0, "valeur_apres": v1, "variation": variation,
        "total_important": variation is not None and abs(variation) >= config.SEUIL_VARIATION_TOTAL,
        "lignes": lignes,
    }


# ---------- Le rapport lui-même ----------
def construire(ctx, comparaison):
    devise = config.DEVISE_BASE
    resume, risques = ctx["resume"], ctx["risques"]
    L = []
    ajouter = L.append

    ajouter(f"# Rapport de portefeuille — {ctx['date'].isoformat()}")
    if ctx["mode"] == "DÉMO":
        ajouter("\n> ⚠️ **MODE DÉMO : toutes les données ci-dessous sont FICTIVES** (générées au hasard pour tester le programme).")
    ajouter(f"\nTous les montants sont en **{devise}**. Les prix viennent de la source indiquée dans la colonne « Source ».")

    if resume["nb_valides"] == 0:
        ajouter("\n> ⚠️ **Aucun titre n'a pu être valorisé** (prix ou taux de change indisponibles). "
                "Les totaux ci-dessous sont donc vides : regarde la section « Avertissements ».")

    # --- Faits ---
    ajouter("\n## 1. Faits : positions et valeur")
    ajouter(f"\n| Titre | Secteur | Qté | Prix | Devise | Source | Valeur ({devise}) | Gain ({devise}) | Gain % | Poids % |")
    ajouter("|---|---|---:|---:|---|---|---:|---:|---:|---:|")
    for r in ctx["resultats"]:
        if r["valeur"] is None:
            continue
        ajouter(f"| {r['ticker']} | {r['secteur']} | {r['quantite']:g} | {fmt(r['prix'])} | {r['devise']} | {r['source_prix']} | "
                f"{fmt(r['valeur'])} | {fmt(r['gain'], 2, '', True)} | {fmt(r['gain_pct'], 1, ' %', True)} | {fmt(r['poids'], 1)} |")
    exclus = [r for r in ctx["resultats"] if r["valeur"] is None]
    if exclus:
        ajouter("\n**Titres exclus des calculs :** " + ", ".join(f"{r['ticker']} ({r['exclusion']})" for r in exclus) + ".")

    ajouter(f"\n- Valeur totale : **{fmt(resume['valeur_totale'])} {devise}**")
    ajouter(f"- Coût total : {fmt(resume['cout_total'])} {devise}")
    ajouter(f"- Gain total : {fmt(resume['gain_total'], 2, '', True)} {devise} ({fmt(resume['gain_total_pct'], 1, ' %', True)})")

    ajouter("\n**Répartition par secteur**\n")
    ajouter("| Secteur | Valeur | Poids % |")
    ajouter("|---|---:|---:|")
    for nom, s in resume["secteurs"].items():
        ajouter(f"| {nom} | {fmt(s['valeur'])} | {fmt(s['poids'], 1)} |")
    ajouter("\n**Répartition par devise** : " + ", ".join(f"{d} {fmt(s['poids'], 1, ' %')}" for d, s in resume["devises"].items()))

    # --- Risque ---
    ajouter("\n## 2. Faits : mesures de risque (calculées sur l'historique passé)\n")
    if risques["par_titre"]:
        ajouter("| Titre | Volatilité annualisée | Pire baisse sur la période | Jours de données |")
        ajouter("|---|---:|---:|---:|")
        for t, m in risques["par_titre"].items():
            ajouter(f"| {t} | {fmt(m['volatilite'], 1, ' %')} | {fmt(m['baisse_max'], 1, ' %')} | {m['jours']} |")
    p = risques["portefeuille"]
    if p:
        ajouter(f"\n**Portefeuille** (rétrospectif, avec les poids actuels, sur {p['jours']} jours communs, "
                f"{p['titres_inclus']} titres représentant {fmt(p['poids_couvert'], 1, ' %')} de la valeur) :")
        ajouter(f"- Volatilité annualisée : {fmt(p['volatilite'], 1, ' %')}")
        ajouter(f"- Pire baisse : {fmt(p['baisse_max'], 1, ' %')}")
        ajouter(f"- Corrélation moyenne entre les titres : {fmt(risques['correlation_moyenne'], 2)}")
    if risques["n_effectif"]:
        ajouter(f"- Concentration : le portefeuille se comporte comme **{fmt(risques['n_effectif'], 1)} titre(s) de poids égal** "
                f"(sur {ctx['resume']['nb_valides']} titre(s) réel(s)).")
    for t, raison in risques["exclus"]:
        ajouter(f"- {t} : mesure de risque non calculée ({raison}).")
    ajouter("\n*La volatilité mesure l'ampleur habituelle des variations passées. La corrélation va de -1 à +1 : "
            "plus elle est haute, moins les titres se compensent. Aucune de ces mesures ne prédit l'avenir.*")

    # --- Observations ---
    ajouter("\n## 3. Observations automatiques (règles simples, PAS des prévisions)")
    ajouter("\n*Ces lignes viennent de seuils que tu peux changer dans `config.py`. Ce sont des interprétations, pas des vérités.*\n")
    if ctx["observations"]:
        for _, texte in ctx["observations"]:
            ajouter(f"- {texte}")
    else:
        ajouter("- Aucune observation avec les seuils actuels.")

    # --- Changements ---
    ajouter("\n## 4. Changements importants")
    if comparaison is None:
        ajouter("\nPremier rapport : il n'y a pas encore de rapport précédent à comparer.")
    else:
        c = comparaison
        ajouter(f"\nComparaison avec le rapport du **{c['date_ref']}** (il y a {c['jours']} jours).\n")
        marque = " ← changement important" if c["total_important"] else ""
        ajouter(f"- Valeur totale : {fmt(c['valeur_avant'])} → {fmt(c['valeur_apres'])} {devise} "
                f"({fmt(c['variation'], 1, ' %', True)}){marque}. Cette variation inclut les achats, les ventes et les taux de change.")
        for ligne in c["lignes"]:
            ajouter(f"- {ligne}")
        if not c["lignes"]:
            ajouter("- Aucun autre changement important selon les seuils choisis.")

    # --- Avertissements et limites ---
    ajouter("\n## 5. Avertissements sur les données\n")
    if ctx["avertissements"]:
        for a in ctx["avertissements"]:
            ajouter(f"- {a}")
    else:
        ajouter("- Aucun.")

    ajouter("\n## Limites de ce rapport")
    ajouter("\n- Les prix viennent de Yahoo Finance via une bibliothèque non officielle : ils peuvent être différés ou indisponibles.")
    ajouter("- Les gains en devise de base utilisent le taux de change d'aujourd'hui, pas celui du jour de l'achat.")
    ajouter("- Les mesures de risque sont calculées en devise locale de chaque titre, sans l'effet des variations de taux de change.")
    ajouter("- Le passé ne prédit pas l'avenir. Ce rapport est un outil d'analyse, pas un conseil financier.")
    return "\n".join(L) + "\n"