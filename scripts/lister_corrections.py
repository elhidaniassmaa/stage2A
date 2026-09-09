"""
Liste toutes les demandes actuellement marquées comme "corrigées"
(decision_responsable != "Validé") pour revue avant nettoyage.

À lancer depuis la racine du projet : python lister_corrections.py
"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "gedec.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nom, prenom, direction_predite, decision_responsable,
               substr(message_original, 1, 60) as apercu_message
        FROM demandes
        WHERE decision_responsable != 'Validé'
        ORDER BY id
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("✅ Aucune correction en base -- rien à nettoyer.")
        return

    print(f"{len(rows)} demande(s) marquée(s) comme corrigée(s) :\n")
    for r in rows:
        print(f"id={r['id']:<4} | {r['nom']} {r['prenom']:<10} | IA: {r['direction_predite']:<6} -> Corrigé: {r['decision_responsable']:<25} | \"{r['apercu_message']}...\"")

if __name__ == "__main__":
    main()
