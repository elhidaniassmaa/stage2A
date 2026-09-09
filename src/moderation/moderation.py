import os
import re
import unicodedata
import logging
from transformers import pipeline

# Configuration du logger
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("moderation")

# Variables globales pour le chargement paresseux (lazy loading) du modèle
_toxicity_pipeline = None
_model_attempted = False
_model_name = "gravitee-io/distilbert-multilingual-toxicity-classifier"

def get_toxicity_pipeline():
    """
    Charge de manière paresseuse le modèle de classification de toxicité.
    Si le chargement échoue, retourne None pour déclencher le repli.
    """
    global _toxicity_pipeline, _model_attempted
    if not _model_attempted and _toxicity_pipeline is None:
        _model_attempted = True
        try:
            # Chargement du pipeline Hugging Face (sur CPU par défaut pour compatibilité)
            _toxicity_pipeline = pipeline(
                "text-classification",
                model=_model_name,
                device=-1
            )
            logger.info(f"Modèle de toxicité {_model_name} chargé avec succès.")
        except Exception as e:
            logger.warning(
                f"Impossible de charger le modèle Hugging Face {_model_name} : {e}. "
                "Le système de modération utilisera le repli par mots-clés."
            )
            _toxicity_pipeline = None
    return _toxicity_pipeline

def normalize_for_matching(text: str) -> str:
    """
    Normalise le texte pour la comparaison avec les mots interdits :
    - Nettoyage avec le module clean_text de preprocessing (Alif, Hamza, Tashkeel)
    - Passage en minuscules
    - Suppression des accents
    """
    try:
        # Importation dynamique pour éviter les dépendances circulaires
        from preprocessing.clean_text import clean_text
        cleaned = clean_text(text)["texte_nettoye"]
    except ImportError:
        # Fallback de base si clean_text n'est pas accessible
        cleaned = text
        
    cleaned = cleaned.lower()
    
    # Suppression des accents latins
    cleaned = "".join(
        c for c in unicodedata.normalize('NFD', cleaned)
        if unicodedata.category(c) != 'Mn'
    )
    return cleaned

def _find_sqlite_db_path() -> str:
    """Chemin canonique vers backend/gedec.db (aligné sur backend/database.py)."""
    try:
        from backend.database import DATABASE_PATH
        return DATABASE_PATH
    except ImportError:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend/gedec.db"))


def _load_from_sqlite() -> list:
    """Charge les mots interdits depuis la table SQLite (source de vérité admin)."""
    db_path = _find_sqlite_db_path()
    if not db_path:
        return []
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT mot FROM mots_interdits ORDER BY mot ASC")
        words = [row[0] for row in cursor.fetchall() if row[0] and str(row[0]).strip()]
        conn.close()
        return words
    except Exception as e:
        logger.warning(f"Impossible de lire mots_interdits depuis SQLite ({db_path}) : {e}")
        return []


def load_forbidden_words(file_path: str = "config/mots_interdits.txt") -> list:
    """
    Charge la liste des mots interdits.
    Priorité : table SQLite (mise à jour par l'interface admin), puis fichier texte.
    """
    words = _load_from_sqlite()
    if words:
        return words

    if not os.path.exists(file_path):
        possible_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../", file_path))
        if os.path.exists(possible_path):
            file_path = possible_path
        else:
            logger.warning(f"Fichier de mots interdits non trouvé à {file_path} ni {possible_path}.")
            return []

    forbidden_words = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    forbidden_words.append(line)
    except Exception as e:
        logger.warning(f"Erreur lors de la lecture du fichier {file_path} : {e}")

    return forbidden_words

def check_mots_cles(texte: str) -> dict:
    """
    Recherche les mots interdits dans le texte d'entrée normalisé.
    Utilise une expression régulière respectant les frontières de mots multilingues.
    """
    try:
        normalized_text = normalize_for_matching(texte)
        forbidden_words = load_forbidden_words()
        
        found_words = []
        for word in forbidden_words:
            normalized_word = normalize_for_matching(word)
            if not normalized_word:
                continue
                
            # Frontières de mots personnalisées gérant l'arabe et le français
            pattern = (
                r'(?<![a-zA-Z0-9_À-ÿ\u0600-\u06FF])'
                + re.escape(normalized_word)
                + r'(?![a-zA-Z0-9_À-ÿ\u0600-\u06FF])'
            )
            
            if re.search(pattern, normalized_text):
                found_words.append(word)
                
        if found_words:
            return {
                "contenu_valide": False,
                "score_confiance": 1.0,
                "methode": "mots_cles"
            }
        else:
            return {
                "contenu_valide": True,
                "score_confiance": 1.0,
                "methode": "mots_cles"
            }
    except Exception as e:
        logger.warning(f"Erreur lors de la vérification par mots-clés : {e}")
        return {
            "contenu_valide": True,
            "score_confiance": 0.0,
            "methode": "mots_cles"
        }
def verifier_contenu(texte: str, seuil_confiance_min: float = 0.75) -> dict:
    """
    Vérifie le contenu d'un texte (français, arabe, ou darija) pour détecter toute toxicité.
    Combine le modèle IA et la vérification par mots-clés lorsque le modèle est peu confiant,
    pour compenser sa faiblesse connue sur la darija.
    """
    try:
        pipeline_model = get_toxicity_pipeline()
        if pipeline_model is not None:
            try:
                result = pipeline_model(texte)[0]
                label = result['label'].lower()
                score = result['score']

                if 'not-toxic' in label or label == 'clean' or label == 'normal':
                    contenu_valide_modele = True
                elif 'toxic' in label or label == 'hate' or label == 'offensive':
                    contenu_valide_modele = False
                else:
                    contenu_valide_modele = True

                # Si le modèle est peu confiant, on croise avec les mots-clés
                if score < seuil_confiance_min:
                    resultat_mots_cles = check_mots_cles(texte)
                    if not resultat_mots_cles["contenu_valide"]:
                        # Le modèle hésitait ET un mot interdit a été trouvé -> on signale
                        return {
                            "contenu_valide": False,
                            "score_confiance": score,
                            "methode": "modele+mots_cles"
                        }

                return {
                    "contenu_valide": contenu_valide_modele,
                    "score_confiance": float(score),
                    "methode": "modele"
                }
            except Exception as e:
                logger.warning(f"Erreur d'inférence avec le modèle : {e}. Repli sur les mots-clés.")

        return check_mots_cles(texte)

    except Exception as e:
        logger.warning(f"Erreur critique dans verifier_contenu : {e}. Validation forcée par défaut.")
        return {
            "contenu_valide": True,
            "score_confiance": 0.0,
            "methode": "mots_cles"
        }

