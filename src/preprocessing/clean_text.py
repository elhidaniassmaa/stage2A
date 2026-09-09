import re
import unicodedata

def clean_text(text: str) -> dict:
    """
    Nettoie un texte brut (pouvant contenir du français, de l'arabe ou un mélange) :
    1. Supprime les caractères de contrôle invisibles.
    2. Normalise les formes d'alif et hamza en arabe.
    3. Supprime les diacritiques arabes (tashkeel).
    4. Supprime les espaces multiples en conservant la structure générale.
    5. Conserve la ponctuation utile au sens.
    
    Retourne un dictionnaire {"texte_original": str, "texte_nettoye": str}.
    """
    if not isinstance(text, str):
        raise TypeError("Le texte d'entrée doit être une chaîne de caractères.")
        
    texte_original = text
    
    # 1. Supprimer les caractères de contrôle invisibles (catégories Unicode commençant par 'C')
    # en préservant les espaces blancs utiles comme les sauts de ligne et tabulations.
    # Cc (contrôle), Cf (format), Cs (surrogate), Co (usage privé), Cn (non attribué)
    texte_nettoye = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in ["\n", "\r", "\t"])
    
    # 2. Supprimer les diacritiques arabes (tashkeel / harakat)
    # Les diacritiques arabes s'étendent de U+064B à U+0652, plus Shadda U+0651, etc.
    tashkeel_regex = re.compile(r'[\u064B-\u0652\u0653\u0654\u0655\u0670]')
    texte_nettoye = tashkeel_regex.sub('', texte_nettoye)
    
    # 3. Normaliser les formes d'alif et hamza en arabe
    # Normalisation des Alifs : أ, إ, آ, ٱ -> ا
    texte_nettoye = re.sub(r'[أإآٱ]', 'ا', texte_nettoye)
    
    # Normalisation des Hamzas : ؤ, ئ -> ء
    texte_nettoye = re.sub(r'[ؤئ]', 'ء', texte_nettoye)
    
    # 4. Supprimer les espaces multiples (espaces, tabulations) et normaliser les retours à la ligne
    texte_nettoye = re.sub(r'[ \t]+', ' ', texte_nettoye)
    texte_nettoye = re.sub(r'\r\n', '\n', texte_nettoye)
    texte_nettoye = re.sub(r'[ \t]*\n[ \t]*', '\n', texte_nettoye)
    texte_nettoye = re.sub(r'\n+', '\n', texte_nettoye)
    texte_nettoye = texte_nettoye.strip()
    
    return {
        "texte_original": texte_original,
        "texte_nettoye": texte_nettoye
    }
