"""Point d'entrée : lit le portefeuille, récupère les prix, calcule, écrit le rapport.

Exemples :
    python main.py                      # vrai portefeuille, vrais prix
    python main.py --demo               # données FICTIVES, sans internet
    python main.py --demo --date 2026-10-21 ; python main.py --demo --date 2026-10-28   # tester la comparaison
"""
import argparse
from datetime import date

import analyse
import config
import donnees
import rapport
import risque


def main():
    parseur = argparse.ArgumentParser(description="Suivi de portefeuille")
    parseur.add_argument("--portefeuille", default=str(config.FICHIER_PORTEFEUILLE), help="chemin du fichier CSV")
    parseur.add_argument("--demo", action="store_true", help="utilise des données fictives (aucun accès internet)")
    parseur.add_argument("--date", help="date du rapport AAAA-MM-JJ (par défaut : aujourd'hui)")
    parseur.add_argument("--sans-cache", action="store_true", help="ne réutilise pas les prix déjà téléchargés aujourd'hui")
    parseur.add_argument("--sans-sauvegarde", action="store_true", help="affiche le rapport sans rien enregistrer")
    args = parseur.parse_args()

    aujourdhui = date.fromisoformat(args.date) if args.date else date.today()
    mode = "DÉMO" if args.demo else "marché"

    positions = donnees.lire_portefeuille(args.portefeuille)
    marche, taux, avertissements = donnees.charger_marche(
        positions, aujourdhui, demo=args.demo, utiliser_cache=not args.sans_cache)

    resultats = analyse.analyser(positions, marche, taux)
    resume = analyse.resumer(resultats)
    risques = risque.calculer(resultats, marche)
    observations = analyse.observations_concentration(resultats, resume) + risque.observations_risque(risques)

    ctx = {"date": aujourdhui, "mode": mode, "resultats": resultats, "resume": resume,
           "risques": risques, "observations": observations, "avertissements": avertissements}

    base = config.DOSSIER_DEMO if args.demo else config.DOSSIER
    dossier_historique = base / "historique"
    dossier_rapports = base / "rapports"

    snap = rapport.instantane(ctx)
    precedent = rapport.charger_precedent(dossier_historique, aujourdhui)
    comparaison = rapport.comparer(snap, precedent) if precedent else None

    texte = rapport.construire(ctx, comparaison)
    print(texte)

    if not args.sans_sauvegarde:
        rapport.sauvegarder_instantane(snap, dossier_historique)
        dossier_rapports.mkdir(parents=True, exist_ok=True)
        fichier = dossier_rapports / f"{aujourdhui.isoformat()}.md"
        fichier.write_text(texte, encoding="utf-8")
        print(f"(Rapport enregistré : {fichier.relative_to(config.DOSSIER)})")


if __name__ == "__main__":
    main()