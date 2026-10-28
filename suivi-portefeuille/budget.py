import json
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox, simpledialog

# --- Où on sauvegarde ---
DOSSIER = Path(__file__).parent / "budgets"
DOSSIER.mkdir(exist_ok=True)

# --- Couleurs (change-les comme tu veux !) ---
FOND = "#1e1f2b"
CARTE = "#2a2c3d"
TEXTE = "#e8e8f0"
DISCRET = "#9a9db5"
ACCENT = "#6c8cff"
ACCENT_CLAIR = "#8aa4ff"
VERT = "#4ade80"
ROUGE = "#f87171"

budget_actuel = None
donnees = {"revenu": 0, "depenses": []}


# ---------- Nombres ----------
def lire_nombre(texte):
    # Accepte 2850.50, 2850,50 et même 2 850,50
    return float(texte.replace(" ", "").replace(",", "."))


def lire_revenu():
    try:
        return lire_nombre(entree_revenu.get())
    except ValueError:
        return 0


# ---------- Sauvegarde et chargement ----------
def lister_budgets():
    return sorted(p.stem for p in DOSSIER.glob("*.json"))


def sauvegarder():
    if budget_actuel is None:
        return
    donnees["revenu"] = lire_revenu()
    with open(DOSSIER / f"{budget_actuel}.json", "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)


def charger(nom):
    global budget_actuel
    with open(DOSSIER / f"{nom}.json", encoding="utf-8") as f:
        contenu = json.load(f)
    budget_actuel = nom
    donnees["revenu"] = contenu.get("revenu", 0)
    donnees["depenses"] = contenu.get("depenses", [])

    entree_revenu.delete(0, tk.END)
    if donnees["revenu"]:
        entree_revenu.insert(0, str(donnees["revenu"]))
    label_budget.config(text=nom)
    rafraichir()


# ---------- Affichage ----------
def rafraichir():
    for item in tableau.get_children():
        tableau.delete(item)
    for d in donnees["depenses"]:
        tableau.insert("", "end", values=(d["description"], d["categorie"], f"{d['montant']:.2f} $"))
    mettre_a_jour()


def mettre_a_jour():
    revenu = lire_revenu()
    total = sum(d["montant"] for d in donnees["depenses"])
    reste = revenu - total

    label_total.config(text=f"Dépenses : {total:.2f} $")
    label_reste.config(text=f"Il reste : {reste:.2f} $", foreground=VERT if reste >= 0 else ROUGE)

    totaux = {}
    for d in donnees["depenses"]:
        cat = d["categorie"]
        totaux[cat] = totaux.get(cat, 0) + d["montant"]

    lignes = []
    for cat, somme in totaux.items():
        pourcentage = somme / total * 100 if total else 0
        lignes.append(f"{cat} : {somme:.2f} $ ({pourcentage:.0f} %)")
    label_categories.config(text="\n".join(lignes))


def mettre_a_jour_bouton_projets():
    # Le bouton n'apparaît que s'il y a plus d'un budget
    if len(lister_budgets()) > 1:
        bouton_projets.grid()
    else:
        bouton_projets.grid_remove()


# ---------- Actions ----------
def ajouter():
    description = entree_description.get().strip()
    categorie = entree_categorie.get().strip().lower()
    if categorie == "":
        categorie = "sans catégorie"

    try:
        montant = lire_nombre(entree_montant.get())
    except ValueError:
        messagebox.showerror("Erreur", "Le montant doit être un nombre.")
        return

    if description == "":
        messagebox.showerror("Erreur", "Remplis la description.")
        return

    donnees["depenses"].append({"description": description, "montant": montant, "categorie": categorie})
    sauvegarder()
    rafraichir()

    entree_description.delete(0, tk.END)
    entree_montant.delete(0, tk.END)
    entree_categorie.delete(0, tk.END)
    entree_description.focus()


def supprimer():
    selection = tableau.selection()
    if not selection:
        messagebox.showinfo("Supprimer", "Clique d'abord sur une dépense dans le tableau.")
        return
    positions = sorted((tableau.index(i) for i in selection), reverse=True)
    for p in positions:
        del donnees["depenses"][p]
    sauvegarder()
    rafraichir()


def revenu_modifie(event):
    mettre_a_jour()
    sauvegarder()


def nouveau_budget():
    global budget_actuel
    nom = simpledialog.askstring("Nouveau budget", "Nom du budget (ex : 2026-11 ou Voyage Europe) :")
    if nom is None:
        return
    nom = nom.strip()
    if nom == "" or any(c in nom for c in '/\\:*?"<>|'):
        messagebox.showerror("Erreur", "Nom invalide (évite / \\ : * ? \" < > |).")
        return
    if nom in lister_budgets():
        messagebox.showerror("Erreur", "Ce budget existe déjà.")
        return

    sauvegarder()
    budget_actuel = nom
    donnees["revenu"] = 0
    donnees["depenses"] = []
    sauvegarder()
    mettre_a_jour_bouton_projets()
    charger(nom)


def ouvrir_menu_projets():
    menu = tk.Menu(fenetre, tearoff=0)
    for nom in lister_budgets():
        menu.add_command(label=nom, command=lambda n=nom: charger(n))
    x = bouton_projets.winfo_rootx()
    y = bouton_projets.winfo_rooty() + bouton_projets.winfo_height()
    menu.tk_popup(x, y)


# ---------- La fenêtre et son style ----------
fenetre = tk.Tk()
fenetre.title("Mon budget")
fenetre.geometry("900x650")
fenetre.minsize(760, 560)
fenetre.configure(bg=FOND)

style = ttk.Style()
style.theme_use("clam")
style.configure("TFrame", background=FOND)
style.configure("Carte.TFrame", background=CARTE)
style.configure("TLabel", background=FOND, foreground=TEXTE, font=("Helvetica", 12))
style.configure("Carte.TLabel", background=CARTE, foreground=TEXTE)
style.configure("Discret.TLabel", background=CARTE, foreground=DISCRET)
style.configure("Nom.TLabel", foreground=ACCENT_CLAIR, font=("Helvetica", 14, "bold"))
style.configure("Titre.TLabel", font=("Helvetica", 24, "bold"))
style.configure("Gros.TLabel", font=("Helvetica", 18, "bold"))
style.configure("TEntry", fieldbackground=FOND, foreground=TEXTE, insertcolor=TEXTE, padding=6)
style.configure("TButton", background=ACCENT, foreground="white", padding=8, font=("Helvetica", 12, "bold"), borderwidth=0)
style.map("TButton", background=[("active", ACCENT_CLAIR)])
style.configure("Treeview", background=CARTE, fieldbackground=CARTE, foreground=TEXTE, rowheight=30, borderwidth=0, font=("Helvetica", 12))
style.configure("Treeview.Heading", background=FOND, foreground=DISCRET, font=("Helvetica", 11, "bold"), borderwidth=0)
style.map("Treeview", background=[("selected", ACCENT)])
style.map("Treeview.Heading", background=[("active", FOND)])

# Ces deux lignes font que la fenêtre s'adapte quand on l'agrandit
fenetre.columnconfigure(0, weight=1)
fenetre.rowconfigure(1, weight=1)

# ---------- Haut : titre + nom du budget + boutons ----------
haut = ttk.Frame(fenetre)
haut.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
haut.columnconfigure(0, weight=1)

ttk.Label(haut, text="Mon budget", style="Titre.TLabel").grid(row=0, column=0, sticky="w")
label_budget = ttk.Label(haut, text="", style="Nom.TLabel")
label_budget.grid(row=0, column=1, padx=10)
bouton_projets = ttk.Button(haut, text="Projets", command=ouvrir_menu_projets)
bouton_projets.grid(row=0, column=2, padx=(0, 10))
ttk.Button(haut, text="+ Nouveau budget", command=nouveau_budget).grid(row=0, column=3)

# ---------- Milieu : formulaire à gauche, tableau à droite ----------
milieu = ttk.Frame(fenetre)
milieu.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
milieu.columnconfigure(1, weight=1)
milieu.rowconfigure(0, weight=1)

carte = ttk.Frame(milieu, style="Carte.TFrame", padding=15)
carte.grid(row=0, column=0, sticky="ns", padx=(0, 15))


def champ(parent, texte, ligne):
    ttk.Label(parent, text=texte, style="Discret.TLabel").grid(row=ligne * 2, column=0, sticky="w", pady=(10, 2))
    entree = ttk.Entry(parent, width=24)
    entree.grid(row=ligne * 2 + 1, column=0, sticky="ew")
    return entree


entree_revenu = champ(carte, "Revenu du mois ($)", 0)
entree_description = champ(carte, "Description", 1)
entree_montant = champ(carte, "Montant ($)", 2)
entree_categorie = champ(carte, "Catégorie (facultatif)", 3)

entree_revenu.bind("<KeyRelease>", revenu_modifie)
for e in (entree_description, entree_montant, entree_categorie):
    e.bind("<Return>", lambda ev: ajouter())

ttk.Button(carte, text="Ajouter la dépense", command=ajouter).grid(row=8, column=0, sticky="ew", pady=(18, 0))
ttk.Label(carte, text="Par catégorie", style="Discret.TLabel").grid(row=9, column=0, sticky="w", pady=(25, 2))
label_categories = ttk.Label(carte, text="", style="Carte.TLabel", justify="left")
label_categories.grid(row=10, column=0, sticky="w")

droite = ttk.Frame(milieu)
droite.grid(row=0, column=1, sticky="nsew")
droite.columnconfigure(0, weight=1)
droite.rowconfigure(0, weight=1)

tableau = ttk.Treeview(droite, columns=("description", "categorie", "montant"), show="headings")
for col, titre in [("description", "Description"), ("categorie", "Catégorie"), ("montant", "Montant")]:
    tableau.heading(col, text=titre, anchor="w")
    tableau.column(col, width=150, anchor="w", stretch=True)
tableau.grid(row=0, column=0, sticky="nsew")

ttk.Button(droite, text="Supprimer la sélection", command=supprimer).grid(row=1, column=0, sticky="e", pady=(10, 0))

# ---------- Bas : totaux ----------
bas = ttk.Frame(fenetre)
bas.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 15))
bas.columnconfigure((0, 1), weight=1)

label_total = ttk.Label(bas, text="", style="Gros.TLabel")
label_total.grid(row=0, column=0, sticky="w")
label_reste = ttk.Label(bas, text="", style="Gros.TLabel")
label_reste.grid(row=0, column=1, sticky="e")

# ---------- Démarrage ----------
budgets = lister_budgets()
if not budgets:
    budget_actuel = datetime.now().strftime("%Y-%m")
    sauvegarder()
    budgets = lister_budgets()

mettre_a_jour_bouton_projets()
charger(budgets[-1])

fenetre.mainloop()