import sqlite3

conn = sqlite3.connect('backend/gedec.db')
cur = conn.cursor()
cur.execute("UPDATE demandes SET decision_responsable = 'Validé' WHERE id = 63")
conn.commit()
print(f"{cur.rowcount} ligne mise à jour.")
conn.close()
