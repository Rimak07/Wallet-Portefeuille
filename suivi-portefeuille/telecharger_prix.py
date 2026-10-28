"""Télécharge les prix de clôture (2 ans) et écrit prix.json, lu par index.html.

Utilisation : pip install yfinance && python telecharger_prix.py
Pour ajouter un titre, ajoute une ligne dans TITRES (symbole Yahoo Finance).
"""
import json

import yfinance as yf

TITRES = {
    "AAPL": ("Apple", "USD"),
    "MSFT": ("Microsoft", "USD"),
    "NVDA": ("Nvidia", "USD"),
    "TSLA": ("Tesla", "USD"),
    "AMZN": ("Amazon", "USD"),
    "SPY": ("FNB S&P 500", "USD"),
    "SHOP.TO": ("Shopify", "CAD"),
    "RY.TO": ("Banque Royale", "CAD"),
    "TD.TO": ("Banque TD", "CAD"),
    "ENB.TO": ("Enbridge", "CAD"),
    "VFV.TO": ("FNB S&P 500 (CAD)", "CAD"),
    "XIU.TO": ("FNB TSX 60", "CAD"),
}

brut = yf.download(
    list(TITRES) + ["CAD=X"], period="2y", auto_adjust=True, progress=False
)["Close"]


def serie(colonne):
    s = brut[colonne].dropna()
    return {d.strftime("%Y-%m-%d"): round(float(v), 4) for d, v in s.items()}


data = {
    "tickers": {
        sym: {"nom": nom, "devise": devise, "prix": serie(sym)}
        for sym, (nom, devise) in TITRES.items()
    },
    "fx": serie("CAD=X"),  # taux USD -> CAD
}
data["maj"] = max(max(t["prix"]) for t in data["tickers"].values())

with open("prix.json", "w", encoding="utf-8") as f:
    json.dump(data, f, separators=(",", ":"))

print("prix.json écrit, dernière date :", data["maj"])
