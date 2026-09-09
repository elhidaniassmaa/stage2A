"""
Calcule la distribution des scores du MEILLEUR tiret candidat sur un large
échantillon de vrais messages du dataset, direction par direction.

Objectif : décider objectivement où placer les seuils des paliers
(<0.45 -> article entier, 0.45-0.65 -> top 3, >0.75 -> tiret exact)
plutôt qu'à l'intuition, en regardant où se situent réellement les scores
sur du texte de citoyens (informel, parfois mal formé).

A exécuter localement depuis src/ :
    cd src
    python ../analyse_distribution_scores.py
"""
import sys
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from argumentaire.reglementation import get_clauses, _get_embedder

DIRECTIONS_A_TESTER = ["DTR", "DJAC", "DMM", "DSPCT", "DAAJJ", "DSI"]


def meilleur_score(direction, texte, embedder, cache_clauses):
    if direction not in cache_clauses:
        cache_clauses[direction] = get_clauses(direction)
    clauses = cache_clauses[direction]
    if not clauses or len(clauses) == 1:
        return None
    textes_clauses = [c.get("texte_clause", "") for c in clauses]
    emb_demande = embedder.encode([texte])[0]
    emb_clauses = embedder.encode(textes_clauses)
    normes = np.linalg.norm(emb_clauses, axis=1) * np.linalg.norm(emb_demande)
    scores = (emb_clauses @ emb_demande) / (normes + 1e-8)
    ordre = np.argsort(-scores)
    meilleur = float(scores[ordre[0]])
    deuxieme = float(scores[ordre[1]]) if len(ordre) > 1 else -1.0
    return meilleur, meilleur - deuxieme


def main():
    df = pd.read_excel("../data/dataset.xlsx")
    embedder = _get_embedder()
    if embedder is None:
        print("[ERREUR] Modèle d'embeddings indisponible.")
        return

    cache_clauses = {}
    resultats = []  # (direction, score, marge)

    for direction in DIRECTIONS_A_TESTER:
        sous = df[df["Entité responsable"] == direction].drop_duplicates(subset="Message")
        print(f"Traitement {direction} ({len(sous)} messages uniques)...")
        for _, row in sous.iterrows():
            texte = str(row["Message"])
            r = meilleur_score(direction, texte, embedder, cache_clauses)
            if r is not None:
                resultats.append((direction, r[0], r[1]))

    res_df = pd.DataFrame(resultats, columns=["direction", "meilleur_score", "marge"])

    print("\n" + "=" * 70)
    print("DISTRIBUTION GLOBALE DU MEILLEUR SCORE (toutes directions confondues)")
    print("=" * 70)
    print(res_df["meilleur_score"].describe(percentiles=[.1, .25, .5, .75, .9]))

    print("\n" + "=" * 70)
    print("PAR DIRECTION")
    print("=" * 70)
    print(res_df.groupby("direction")["meilleur_score"].describe(percentiles=[.5, .75, .9]))

    print("\n" + "=" * 70)
    print("REPARTITION PAR PALIER (seuils proposés : 0.45 / 0.65 / 0.75)")
    print("=" * 70)
    bins = [0, 0.45, 0.65, 0.75, 1.01]
    labels = ["<0.45 (article entier)", "0.45-0.65 (top 3)", "0.65-0.75 (zone grise)", ">0.75 (tiret exact)"]
    res_df["palier"] = pd.cut(res_df["meilleur_score"], bins=bins, labels=labels)
    print(res_df["palier"].value_counts().sort_index())
    print()
    print("En %:")
    print((res_df["palier"].value_counts(normalize=True).sort_index() * 100).round(1))

    res_df.to_csv("../resultats_distribution_scores.csv", index=False)
    print("\nDétail sauvegardé dans resultats_distribution_scores.csv")


if __name__ == "__main__":
    main()