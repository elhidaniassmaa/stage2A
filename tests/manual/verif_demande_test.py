import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "gedec.db")
print(f"Base utilisée : {DB_PATH}")
print(f"Existe : {os.path.exists(DB_PATH)}\n")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM demandes")
print(f"Nombre total de demandes en base : {cur.fetchone()[0]}\n")

cur.execute("SELECT id, direction_predite, statut_demande, type_alerte, notif_prioritaire_envoyee, date_depot FROM demandes WHERE id = 65")
row = cur.fetchone()
if row:
    print("Demande id=65 trouvée :")
    print(dict(row))
else:
    print("Demande id=65 INTROUVABLE dans cette base.")

print("\nDemandes actuellement en statut 'prioritaire' et 'En attente' :")
cur.execute("SELECT id, direction_predite, date_depot FROM demandes WHERE statut_demande = 'En attente' AND type_alerte = 'prioritaire'")
for r in cur.fetchall():
    print(dict(r))

conn.close()
