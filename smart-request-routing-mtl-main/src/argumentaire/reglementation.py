import os
import json
import re
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("reglementation")

_json_path = "base_reglementaire.json"

_embedder = None
_embedder_attempted = False


def _get_embedder():
    """
    Charge de manière paresseuse le modèle d'embeddings multilingue, utilisé pour
    comparer le sens du message du citoyen avec le sens de chaque tiret
    réglementaire, indépendamment de la langue utilisée (arabe, français, darija).
    """
    global _embedder, _embedder_attempted
    if not _embedder_attempted and _embedder is None:
        _embedder_attempted = True
        try:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer(
                "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
            )
            logger.info("Modèle d'embeddings multilingue (MPNet) chargé avec succès.")
        except Exception as e:
            logger.warning(
                f"Modèle d'embeddings indisponible : {e}. "
                "La sélection de tiret se rabattra sur un recouvrement de mots-clés."
            )
            _embedder = None
    return _embedder


def _find_json_path():
    actual_path = _json_path
    if os.path.exists(actual_path):
        return actual_path
    possible_path = os.path.abspath(os.path.join(os.path.dirname(__file__), _json_path))
    if os.path.exists(possible_path):
        return possible_path
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/argumentaire/", _json_path))
    if os.path.exists(root_path):
        return root_path
    logger.warning(f"Base réglementaire JSON non trouvée à {actual_path} ni {possible_path}.")
    return None


def get_clauses(code_direction: str) -> list:
    """
    Charge TOUS les tirets (clauses) réglementaires associés à une direction.
    """
    if not code_direction:
        return []

    path = _find_json_path()
    if path is None:
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            clauses = json.load(f)

        target_code = code_direction.strip().upper()
        matching = [
            c for c in clauses
            if c.get("code_direction", "").strip().upper() == target_code
            or c.get("code_direction", "").strip().lower() == code_direction.strip().lower()
        ]
        return matching
    except Exception as e:
        logger.error(f"Erreur lors de la lecture de la base réglementaire : {e}")
        return []


def _score_mots_cles(texte: str, clause_texte: str) -> float:
    """
    Repli si les embeddings sont indisponibles : score de recouvrement de mots
    (indice de Jaccard). Limite connue : peu fiable si le message n'est pas dans
    la même langue que le texte de la clause (ex. arabizi comparé à de l'arabe).
    """
    mots_texte = set(re.findall(r"\w+", texte.lower()))
    mots_clause = set(re.findall(r"\w+", clause_texte.lower()))
    if not mots_texte or not mots_clause:
        return 0.0
    return len(mots_texte & mots_clause) / len(mots_texte | mots_clause)


def get_best_clause(code_direction: str, texte_demande: str,
                     seuil_article: float = 0.45, seuil_precis: float = 0.75,
                     top_k_intermediaire: int = 3, verbose: bool = False) -> list:
    """
    Sélectionne, parmi TOUS LES TIRETS associés à une direction, le ou les
    tirets les plus pertinents par rapport au contenu réel de la demande du
    citoyen, via une similarité sémantique multilingue (embeddings), selon un
    système à 3 paliers calibré empiriquement sur 357 messages réels du
    dataset (percentiles observés : médiane 0.42, 90e centile 0.63) :

      - score du meilleur tiret <  seuil_article (0.45)  : le modèle n'est pas
        assez confiant pour discriminer -> on retourne TOUS les tirets de
        l'article contenant le meilleur candidat (citation de l'article
        complet). Cas le plus fréquent (~55% des messages réels).

      - seuil_article <= score < seuil_precis (0.75)      : confiance
        modérée -> on retourne les top_k_intermediaire (3) tirets les plus
        proches, ce qui capture le bon tiret même quand le modèle hésite
        entre plusieurs candidats proches en score (cas observé : "enquête
        accident aérien", où le tiret le plus proche était en fait le mauvais
        de justesse). Concerne ~40% des messages réels.

      - score >= seuil_precis (0.75)                       : confiance forte
        -> on cite directement le seul tiret le plus pertinent. Cas rare
        mais réel (~4-5% des messages), réservé aux demandes sans ambiguïté.

    Limites connues (à documenter) : la similarité fonctionne bien pour le
    français et l'arabe standard ; sa fiabilité sur la darija en alphabet latin
    (arabizi) n'est pas garantie et devrait être renforcée par un score de
    mots-clés spécifique si les tests le montrent nécessaire. La direction DSI
    obtient des scores structurellement plus bas (max observé 0.63 sur
    l'échantillon réel) : ses demandes retombent presque systématiquement sur
    l'article complet, ce qui est probablement une limite du contenu des
    tirets DSI plutôt qu'un défaut du modèle.
    """
    clauses = get_clauses(code_direction)
    if not clauses:
        return []
    if len(clauses) == 1:
        return clauses

    embedder = _get_embedder()
    if embedder is not None:
        try:
            import numpy as np
            textes_clauses = [c.get("texte_clause", "") for c in clauses]
            emb_demande = embedder.encode([texte_demande])[0]
            emb_clauses = embedder.encode(textes_clauses)

            normes = np.linalg.norm(emb_clauses, axis=1) * np.linalg.norm(emb_demande)
            scores = (emb_clauses @ emb_demande) / (normes + 1e-8)

            ordre = np.argsort(-scores)
            meilleur_score = float(scores[ordre[0]])

            if verbose:
                print(f"\n  [DIAGNOSTIC] Demande : {texte_demande[:60]}")
                for i in ordre[:5]:
                    print(f"    [score={scores[i]:.4f}] art.{clauses[i]['numero_article']} pt.{clauses[i]['numero_tiret']} : {clauses[i]['texte_clause'][:60]}")

            if meilleur_score >= seuil_precis:
                palier = "TIRET PRECIS"
                resultat = [clauses[ordre[0]]]
            elif meilleur_score >= seuil_article:
                palier = f"TOP {top_k_intermediaire}"
                resultat = [clauses[i] for i in ordre[:top_k_intermediaire]]
            else:
                palier = "ARTICLE ENTIER"
                meilleur_article = clauses[ordre[0]].get("numero_article", "")
                resultat = [c for c in clauses if c.get("numero_article", "") == meilleur_article]

            if verbose:
                print(f"    [palier retenu = {palier}] (seuil_article={seuil_article}, seuil_precis={seuil_precis})")

            return resultat
        except Exception as e:
            logger.warning(f"Erreur de similarité par embeddings : {e}. Repli sur mots-clés.")

    # Repli mots-clés si les embeddings sont indisponibles
    scores_mc = [(_score_mots_cles(texte_demande, c.get("texte_clause", "")), c) for c in clauses]
    scores_mc.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scores_mc[:top_k]]