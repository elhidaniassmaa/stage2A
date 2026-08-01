import os
import requests
import logging
from collections import defaultdict
from argumentaire.reglementation import get_best_clause

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("generer_argumentaire")


def generer_argumentaire(direction: str, texte_demande: str) -> str:
    """
    Génère une justification réglementaire (argumentaire) pour la direction choisie
    concernant une demande citoyenne donnée.

    Sélectionne le tiret le plus pertinent (ou l'article entier si aucun tiret
    n'est assez pertinent) via get_best_clause, puis tente de faire rédiger une
    justification fluide par un LLM local. Si le LLM est indisponible, retourne
    un message de repli citant directement le(s) tiret(s) sélectionné(s).
    """
    articles = get_best_clause(direction, texte_demande)

    if not articles or direction.strip().upper() == "NON CONCERNÉ" or direction.strip().lower() == "non concerné":
        return "Aucune direction du Ministère du Transport et de la Logistique n'est compétente pour traiter cette demande."

    # Regrouper les tirets par article pour un affichage lisible (utile quand
    # get_best_clause retourne l'article complet plutôt qu'un seul tiret)
    par_article = defaultdict(list)
    for art in articles:
        par_article[art.get("numero_article", "")].append(art.get("texte_clause", ""))

    articles_citations = []
    for num, textes in par_article.items():
        if num.lower() == "hors décret 2.21.968":
            articles_citations.append(f"le rôle du Cabinet du Ministère, qui prévoit que : \"{' '.join(textes)}\"")
        elif len(textes) == 1:
            articles_citations.append(f"l'article {num} du décret n° 2.21.968 qui dispose que : \"{textes[0]}\"")
        else:
            texte_complet = " ; ".join(textes)
            articles_citations.append(f"l'article {num} du décret n° 2.21.968, qui dispose notamment que : \"{texte_complet}\"")

    citations_text = " et ".join(articles_citations)
    fallback_message = f"La direction {direction} est désignée compétente pour cette demande en vertu de {citations_text}."

    # Construction du prompt pour le LLM local (génération de texte uniquement,
    # pas de sélection de tiret -- cette dernière est faite par get_best_clause)
    articles_content = "\n".join([
        f"- Article {art.get('numero_article', '')}, point {art.get('numero_tiret', '')} : {art.get('texte_clause', '')}"
        for art in articles
    ])

    prompt = (
        f"[INST] Tu es un assistant juridique expert pour le Ministère du Transport et de la Logistique. "
        f"En te basant STRICTEMENT sur le ou les points réglementaires fournis ci-dessous, rédige une justification de 2 à 3 phrases expliquant pourquoi la direction \"{direction}\" est compétente pour traiter la demande suivante. "
        f"Ne rajoute aucune information externe ou spéculation non présente dans les points fournis.\n\n"
        f"Points réglementaires :\n{articles_content}\n\n"
        f"Demande citoyenne :\n\"{texte_demande}\"\n\n"
        f"Rédige ta justification de manière claire et professionnelle en français. [/INST]"
    )

    # Tenter d'interroger un LLM local (Ollama sur http://localhost:11434)
    try:
        model_name = os.environ.get("LOCAL_LLM_MODEL", "mistral")
        url = "http://localhost:11434/api/generate"
        headers = {"Content-Type": "application/json"}
        data = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(url, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            generated_text = response.json().get("response", "").strip()
            if generated_text:
                return generated_text
    except Exception as e:
        logger.debug(f"Ollama local non disponible ou erreur : {e}")

    # Tenter d'interroger llama-cpp-python si installé
    try:
        from llama_cpp import Llama
        model_path = os.environ.get("LOCAL_GGUF_PATH", "")
        if model_path and os.path.exists(model_path):
            llm = Llama(model_path=model_path, verbose=False, n_ctx=1024)
            output = llm(f"Q: {prompt}\nA:", max_tokens=150, stop=["Q:", "\n"])
            generated_text = output["choices"][0]["text"].strip()
            if generated_text:
                return generated_text
    except Exception as e:
        logger.debug(f"Llama-cpp local non disponible ou erreur : {e}")

    # Message de repli si le modèle local n'est pas disponible
    return fallback_message