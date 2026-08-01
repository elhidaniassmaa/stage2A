import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "gedec.db")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

mapping = {
    "Transport Routier": "DTR",
    "Logistique & Ports": "DSPCT",
    "Affaires Générales": "DAAJJ",
    "Marine Marchande": "DMM",
    "Aérien & Civil": "DJAC",
    "Systèmes d'Information": "DSI",
    "Cabinet du Ministère": "Cabinet du Ministère",
}

for nom_complet, sigle in mapping.items():
    cur.execute("UPDATE users SET direction = ? WHERE direction = ?", (sigle, nom_complet))
    print(f"{cur.rowcount} compte(s) : '{nom_complet}' -> '{sigle}'")

conn.commit()
conn.close()
print("Migration terminée.")
