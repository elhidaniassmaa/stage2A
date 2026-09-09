"""
export_corrections.py

Génère data/historique_corrections.xlsx à partir des VRAIES corrections
accumulées en base SQLite (backend/gedec.db), pour alimenter le pipeline de
réentraînement incrémental (reentrainement.py).

Une "correction" est une demande où le Responsable n'a PAS validé la
proposition de l'IA (decision_responsable != "Validé") -- c'est le signal
d'erreur qu'on veut apprendre au modèle à ne plus reproduire.

Format de sortie attendu par reentrainement.py (load_and_merge_datasets) :
    colonnes 'Message' et 'Direction_validee' exactement.

Usage :
    python src/classification/export_corrections.py
    (depuis la racine du projet, avec le venv actif)

Recommandation (documentée dans le rapport) : n'utiliser ce fichier pour un
vrai réentraînement qu'à partir d'un volume minimal de 20-30 corrections
réparties sur plusieurs directions, pour éviter un fine-tuning instable sur
un échantillon trop faible et non représentatif.
"""
import os
import sqlite3
import pandas as pd

# Directions valides (doivent correspondre exactement à LABEL_MAP dans
# reentrainement.py / train_classifier.py -- toute valeur hors de cette
# liste sera silencieusement ignorée par pandas.map() lors du réentraînement,
# donc on la détecte et on alerte ici plutôt que de laisser l'erreur passer
# inaperçue plus tard).
DIRECTIONS_VALIDES = {
    "DSI", "DSPCT", "DAAJJ", "DMM", "DTR", "DJAC",
    "Cabinet du Ministère", "Non concerné"
}

SORTIE_PATH = "data/historique_corrections.xlsx"
SEUIL_RECOMMANDE = 20


def _trouver_db():
    """
    Cherche gedec.db à quelques emplacements plausibles, pour que le script
    fonctionne qu'on le lance depuis la racine du projet ou depuis
    src/classification/. Affiche le chemin retenu pour transparence.
    """
    candidats = [
        "backend/gedec.db",
        os.path.join(os.path.dirname(__file__), "..", "..", "backend", "gedec.db"),
        "gedec.db",
    ]
    for chemin in candidats:
        if os.path.exists(chemin):
            return os.path.abspath(chemin)
    raise FileNotFoundError(
        "gedec.db introuvable. Chemins essayés : " + ", ".join(candidats) +
        " -- lance ce script depuis la racine du projet, ou corrige _trouver_db()."
    )


def exporter_corrections():
    db_path = _trouver_db()
    print(f"Connexion à la base : {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, message_nettoye, decision_responsable, direction_predite
        FROM demandes
        WHERE decision_responsable IS NOT NULL
          AND decision_responsable != 'Validé'
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("Aucune correction trouvée en base (toutes les demandes traitées ont été validées telles quelles, ou aucune demande n'a encore été traitée).")
        print(f"Aucun fichier écrit -- {SORTIE_PATH} n'a PAS été modifié.")
        return None

    lignes = []
    directions_invalides_rencontrees = set()

    for row in rows:
        direction_corrigee = row["decision_responsable"].replace("Corriger : ", "").strip()
        if direction_corrigee not in DIRECTIONS_VALIDES:
            directions_invalides_rencontrees.add(direction_corrigee)
            continue  # on ne l'inclut pas dans l'export, mais on le signale plus bas
        if not row["message_nettoye"] or not str(row["message_nettoye"]).strip():
            continue
        lignes.append({
            "Message": row["message_nettoye"],
            "Direction_validee": direction_corrigee,
        })

    if directions_invalides_rencontrees:
        print(f"⚠️  ATTENTION : {len(directions_invalides_rencontrees)} valeur(s) de direction "
              f"inattendue(s) rencontrée(s) et EXCLUE(S) de l'export : {directions_invalides_rencontrees}")
        print("   Ces valeurs ne correspondent à aucun sigle officiel connu -- vérifie la table 'demandes' "
              "ou la logique de correction côté frontend (BaseReglementaire.jsx / Dashboard.jsx).")

    if not lignes:
        print("Aucune correction exploitable après filtrage (toutes exclues ou vides).")
        print(f"Aucun fichier écrit -- {SORTIE_PATH} n'a PAS été modifié.")
        return None

    df = pd.DataFrame(lignes)

    os.makedirs(os.path.dirname(SORTIE_PATH), exist_ok=True)
    df.to_excel(SORTIE_PATH, index=False)

    # --- Auto-vérification post-écriture ---
    df_relu = pd.read_excel(SORTIE_PATH)
    assert list(df_relu.columns[:2]) == ["Message", "Direction_validee"] or \
           set(["Message", "Direction_validee"]).issubset(df_relu.columns), \
           "Colonnes attendues manquantes après écriture -- fichier potentiellement corrompu."
    assert df_relu["Direction_validee"].isnull().sum() == 0, \
           "Valeurs manquantes détectées dans Direction_validee après écriture."

    print(f"\n{len(df)} correction(s) exportée(s) vers {SORTIE_PATH}")
    print("\nRépartition par direction :")
    print(df["Direction_validee"].value_counts().to_string())

    if len(df) < SEUIL_RECOMMANDE:
        print(f"\n⚠️  Seulement {len(df)} correction(s) trouvée(s), en dessous du seuil recommandé "
              f"de {SEUIL_RECOMMANDE} pour un réentraînement représentatif. "
              f"Utilisable pour un test technique du pipeline, mais à ne pas déployer "
              f"aveuglément en production sans plus de volume.")
    else:
        print(f"\n✅ Volume suffisant ({len(df)} >= {SEUIL_RECOMMANDE}) pour un réentraînement jugé représentatif.")

    return df


if __name__ == "__main__":
    exporter_corrections()
