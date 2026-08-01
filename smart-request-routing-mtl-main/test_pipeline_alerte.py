import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "gedec.db")

# 1. Forcer une demande existante à 5 jours restants
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

date_forcee = (datetime.now() - timedelta(days=55)).strftime("%Y-%m-%d %H:%M:%S")

cur.execute("SELECT id, direction_predite FROM demandes WHERE statut_demande = 'En attente' LIMIT 1")
row = cur.fetchone()

if not row:
    print("❌ Aucune demande 'En attente' trouvée en base pour le test.")
    conn.close()
    sys.exit(1)

demande_id, direction = row
print(f"Demande sélectionnée : id={demande_id}, direction={direction}")

# Réinitialiser le flag pour permettre un nouvel envoi de test
try:
    cur.execute(
        "UPDATE demandes SET date_depot = ?, notif_prioritaire_envoyee = 0 WHERE id = ?",
        (date_forcee, demande_id)
    )
    conn.commit()
    print(f"✅ Date de dépôt forcée à {date_forcee} (5 jours restants).")
except sqlite3.OperationalError as e:
    print(f"❌ Erreur SQL : {e}")
    print("   -> La colonne 'notif_prioritaire_envoyee' existe-t-elle bien ? Vérifiez la migration.")
    conn.close()
    sys.exit(1)

conn.close()

# 2. Vérifier qu'un responsable existe bien pour cette direction (sinon aucun email ne partira)
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT email, nom_complet, statut FROM users WHERE direction = ? AND role = 'Responsable'", (direction,))
responsables = cur.fetchall()
conn.close()

if not responsables:
    print(f"⚠️  ATTENTION : aucun compte Responsable trouvé avec direction = '{direction}'.")
    print("   -> Aucun email ne sera envoyé, même si la logique fonctionne, car il n'y a pas de destinataire.")
else:
    for r in responsables:
        print(f"   Responsable trouvé : {r['nom_complet']} ({r['email']}) - statut: {r['statut']}")

# 3. Appeler la fonction de vérification des alertes (déclenche l'envoi si tout est correct)
print("\n--- Lancement de verifier_et_traiter_alertes() ---")
from backend.main import verifier_et_traiter_alertes
verifier_et_traiter_alertes()
print("--- Terminé ---\n")

# 4. Vérifier que le flag a bien été mis à jour (preuve que le code est passé par la bonne branche)
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT type_alerte, notif_prioritaire_envoyee FROM demandes WHERE id = ?", (demande_id,))
type_alerte, notif_envoyee = cur.fetchone()
conn.close()

print(f"type_alerte en base : {type_alerte}")
print(f"notif_prioritaire_envoyee en base : {notif_envoyee}")

if type_alerte == "prioritaire" and notif_envoyee == 1:
    print("✅ Le pipeline complet a fonctionné : vérifiez votre boîte mail.")
elif type_alerte != "prioritaire":
    print("❌ Le type d'alerte n'est pas 'prioritaire' -- problème dans le calcul d'échéance.")
else:
    print("❌ notif_prioritaire_envoyee n'a pas été mis à 1 -- l'email n'a probablement pas été envoyé.")