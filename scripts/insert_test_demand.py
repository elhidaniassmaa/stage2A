import os
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "gedec.db")
DIRECTION_TEST = "DTR"

def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Base introuvable à : {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        "SELECT email, nom_complet FROM users WHERE direction = ? AND role = 'Responsable' AND statut = 'ACTIF'",
        (DIRECTION_TEST,)
    )
    responsables = cur.fetchall()

    if not responsables:
        print(f"⚠️ Aucun Responsable ACTIF trouvé pour '{DIRECTION_TEST}'. L'email ne partira PAS.")
        conn.close()
        return
    else:
        print(f"✅ Destinataire(s) trouvé(s) pour {DIRECTION_TEST} :")
        for r in responsables:
            print(f"   - {r['nom_complet']} <{r['email']}>")

    date_depot = datetime.now() - timedelta(days=55)
    date_echeance = date_depot + timedelta(days=60)

    cur.execute("""
        INSERT INTO demandes (
            nom, prenom, message_original, message_nettoye, date_depot, date_echeance,
            type_alerte, contenu_valide, mot_interdit_detecte, direction_predite,
            score_confiance, confiance_faible, argumentaire, decision_responsable,
            statut_demande, region, notif_rappel_envoyee, notif_prioritaire_envoyee
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "TEST", "Alerte",
        "[DEMANDE DE TEST] Vérification du système d'alerte prioritaire par email.",
        "demande de test pour verifier le systeme d'alerte prioritaire par email",
        date_depot.strftime("%Y-%m-%d %H:%M:%S"),
        date_echeance.strftime("%Y-%m-%d %H:%M:%S"),
        "prioritaire", 1, 0, DIRECTION_TEST, 0.90, 0,
        "Demande de test -- ne pas traiter.",
        "Validé", "En attente", "Rabat-Salé-Kénitra", 0, 0
    ))
    conn.commit()
    new_id = cur.lastrowid
    print(f"\n✅ Demande insérée : id={new_id} (GEDEC-2026-{new_id:03d}), échéance dans 5 jours.")

    cur.execute("SELECT id, direction_predite, type_alerte, notif_prioritaire_envoyee FROM demandes WHERE id = ?", (new_id,))
    print(dict(cur.fetchone()))
    conn.close()

if __name__ == "__main__":
    main()
