import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smart-request-routing-mtl-main", "backend", "gedec.db")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

for col, type_sql in [
    ("notif_rappel_envoyee", "INTEGER DEFAULT 0"),
    ("notif_prioritaire_envoyee", "INTEGER DEFAULT 0"),
]:
    try:
        cur.execute(f"ALTER TABLE demandes ADD COLUMN {col} {type_sql}")
        print(f"Colonne {col} ajoutée.")
    except sqlite3.OperationalError:
        print(f"{col} existe déjà.")

conn.commit()
conn.close()