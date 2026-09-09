# migration_rapport.py — à exécuter une seule fois
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "gedec.db")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE demandes ADD COLUMN date_reponse TEXT")
except sqlite3.OperationalError:
    print("date_reponse existe déjà")

try:
    cur.execute("ALTER TABLE demandes ADD COLUMN theme TEXT")
except sqlite3.OperationalError:
    print("theme existe déjà")

conn.commit()
conn.close()
print("Migration terminée.")