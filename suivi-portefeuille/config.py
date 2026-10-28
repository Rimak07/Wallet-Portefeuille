"""Réglages du projet : change les valeurs ici, pas dans le reste du code."""
from pathlib import Path

DOSSIER = Path(__file__).parent
FICHIER_PORTEFEUILLE = DOSSIER / "portefeuille.csv"
DOSSIER_HISTORIQUE = DOSSIER / "historique"
DOSSIER_RAPPORTS = DOSSIER / "rapports"
DOSSIER_DEMO = DOSSIER / "demo_sortie"
DOSSIER_CACHE = DOSSIER / ".cache_prix"

# Devise dans laquelle tout est converti et affiché
DEVISE_BASE = "CAD"

# Taux de secours si le marché est indisponible. Exemple : {"USD": 1.37}
# (vide par défaut : on n'invente jamais un taux)
TAUX_MANUELS = {}

# Historique utilisé pour les mesures de risque
PERIODE_HISTORIQUE = "1y"
JOURS_BOURSE_PAR_AN = 252
MIN_JOURS_RISQUE = 30          # minimum de jours de données pour calculer un risque

# Seuils d'observation (des choix arbitraires, pas des vérités)
SEUIL_POSITION = 25            # % du portefeuille pour un seul titre
SEUIL_SECTEUR = 50             # % du portefeuille pour un seul secteur
SEUIL_VOLATILITE = 35          # % annualisé
SEUIL_CORRELATION = 0.7        # corrélation moyenne entre les titres

# Changements jugés importants dans le rapport hebdomadaire
SEUIL_VARIATION_PRIX = 5       # % de variation du prix d'un titre
SEUIL_VARIATION_POIDS = 3      # points de pourcentage de changement de poids
SEUIL_VARIATION_TOTAL = 2      # % de variation de la valeur totale

JOURS_PRIX_PERIME = 5          # avertir si le dernier prix a plus de N jours