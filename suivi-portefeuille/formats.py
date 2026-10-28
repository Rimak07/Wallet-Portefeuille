"""Petits outils d'affichage partagés par tout le projet."""


def fmt(x, dec=2, suffixe="", signe=False):
    """Format à la française : 1 234,56 (et "—" quand la donnée n'existe pas)."""
    if x is None:
        return "—"
    texte = f"{x:{'+' if signe else ''},.{dec}f}".replace(",", " ").replace(".", ",")
    return texte + suffixe