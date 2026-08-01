"""Vérifie les emplacements possibles de gedec.db et indique la base canonique."""
import os
import sqlite3
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smart-request-routing-mtl-main")
sys.path.insert(0, PROJECT_ROOT)

try:
    from backend.database import DATABASE_PATH as CANONICAL
except ImportError:
    CANONICAL = os.path.join(PROJECT_ROOT, "backend", "gedec.db")

CANDIDATES = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "gedec.db"),
    os.path.join(PROJECT_ROOT, "gedec.db"),
    os.path.join(PROJECT_ROOT, "backend", "gedec.db"),
]

print(f"Base canonique (backend/database.py) : {CANONICAL}\n")

for chemin in CANDIDATES:
    print(f"--- {chemin} ---")
    if not os.path.exists(chemin):
        print("Fichier introuvable.")
        continue
    size = os.path.getsize(chemin)
    print(f"Taille : {size} octets")
    if size == 0:
        print("⚠️  Fichier VIDE — à supprimer.")
        continue
    try:
        conn = sqlite3.connect(chemin)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cur.fetchall()]
        if "demandes" in tables:
            cur.execute("SELECT COUNT(*) FROM demandes")
            nb = cur.fetchone()[0]
            print(f"Tables : {tables}")
            print(f"demandes : {nb}")
        else:
            print(f"Tables : {tables} | table 'demandes' absente")
        conn.close()
        if os.path.normpath(chemin) == os.path.normpath(CANONICAL):
            print("✅ C'est la base canonique.")
        else:
            print("❌ Ce n'est PAS la base canonique — ne pas utiliser pour l'application.")
    except Exception as e:
        print(f"Erreur : {e}")
