"""
Synchronisation entre la table SQLite `articles` (interface Administrateur) et
`src/argumentaire/base_reglementaire.json` (fichier réellement lu par le RAG,
via get_clauses() dans reglementation.py).

Pourquoi ce module est nécessaire :
Le RAG (generer_argumentaire.py / get_best_clause) ne lit JAMAIS la base SQLite.
Il relit base_reglementaire.json à CHAQUE appel (aucun cache disque, embeddings
recalculés à la volée) -- donc il suffit d'écrire dans ce fichier pour que le
changement soit pris en compte immédiatement, sans redémarrage ni recalcul
d'index à gérer.

Convention adoptée : un article ajouté/modifié via l'interface Administrateur
devient UN SEUL tiret (numero_tiret unique) dans le JSON, par simplicité --
contrairement aux articles du décret d'origine qui sont déjà pré-découpés en
plusieurs tirets fins.

Point clé de design : la table SQLite `articles` n'a pas de colonne
numero_tiret, donc chaque tiret ajouté ici porte un champ supplémentaire
`admin_article_id` = l'id SQLite de l'article correspondant. C'est ce qui
permet de retrouver/modifier/supprimer le bon tiret plus tard de façon fiable,
sans dépendre de (direction, numero_article, numero_tiret) qui pourrait ne
plus être unique si deux articles administrateur partagent le même numéro.
Les tirets du décret d'origine n'ont pas ce champ (absent = tiret officiel).
"""
import json
import os
import threading

# Verrou pour éviter une écriture concurrente corrompue si deux requêtes admin
# arrivent en même temps (SQLite gère déjà ça pour la table, mais le fichier
# JSON n'a pas cette protection native).
_lock = threading.Lock()


def _get_json_path():
    """
    Chemin vers le vrai fichier utilisé par le RAG. A adapter si la structure
    du repo diffère (vérifie que ce chemin correspond bien à celui résolu par
    _find_json_path() dans reglementation.py). Ici : backend/ et src/ sont
    frères à la racine du projet.
    """
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "src", "argumentaire", "base_reglementaire.json")
    )


def _charger_json():
    path = _get_json_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"base_reglementaire.json introuvable à {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _sauvegarder_json(data):
    path = _get_json_path()
    # Ecriture sur fichier temporaire puis remplacement atomique, pour éviter
    # un JSON corrompu si le processus est interrompu en pleine écriture.
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def _prochain_numero_tiret(data, code_direction, numero_article):
    existants = [
        c["numero_tiret"] for c in data
        if c.get("code_direction") == code_direction
        and str(c.get("numero_article")) == str(numero_article)
    ]
    return (max(existants) + 1) if existants else 1


def _normaliser_numero_article(numero: str) -> str:
    """Harmonise 'Art. 6' (SQLite) et '6' (JSON)."""
    n = str(numero).strip()
    if n.lower().startswith("art."):
        n = n[4:].strip()
    return n


def _normaliser_texte(texte: str) -> str:
    return " ".join(str(texte).split()).strip().lower()


def _creer_tiret(data, article_id, code_direction, numero_article, texte_extrait, date_version=None):
    numero_tiret = _prochain_numero_tiret(data, code_direction, numero_article)
    nouvelle_clause = {
        "code_direction": code_direction,
        "numero_article": str(numero_article),
        "numero_tiret": numero_tiret,
        "texte_clause": texte_extrait,
        "admin_article_id": article_id,
    }
    if date_version:
        nouvelle_clause["date_version"] = date_version
    data.append(nouvelle_clause)
    return nouvelle_clause


def _trouver_tiret_par_admin_id(data, article_id: int):
    for clause in data:
        if clause.get("admin_article_id") == article_id:
            return clause
    return None


def _trouver_tiret_par_contenu(data, code_direction: str, numero_article: str, texte_extrait: str):
    """Recherche un tiret sans admin_article_id par correspondance de contenu."""
    art_num = _normaliser_numero_article(numero_article)
    art_text = _normaliser_texte(texte_extrait)
    art_dir = code_direction.strip().upper()
    for clause in data:
        if clause.get("admin_article_id"):
            continue
        clause_num = _normaliser_numero_article(clause.get("numero_article", ""))
        clause_text = _normaliser_texte(clause.get("texte_clause", ""))
        clause_dir = clause.get("code_direction", "").strip().upper()
        if art_dir == clause_dir and art_num == clause_num and art_text == clause_text:
            return clause
    return None


def rattacher_par_ordre_seed(sqlite_ids: list) -> int:
    """
    Lie les ids SQLite insérés dans le même ordre que base_reglementaire.json
    (appelé une seule fois lors du seed initial dans init_db).
    """
    if not sqlite_ids:
        return 0
    with _lock:
        data = _charger_json()
        rattaches = 0
        id_iter = iter(sqlite_ids)
        for clause in data:
            if clause.get("admin_article_id"):
                continue
            try:
                clause["admin_article_id"] = next(id_iter)
                rattaches += 1
            except StopIteration:
                break
        if rattaches > 0:
            _sauvegarder_json(data)
        return rattaches


def rattacher_articles_heritage() -> dict:
    """
    Rattache rétroactivement les articles SQLite issus du décret d'origine à leurs
    tirets JSON correspondants via admin_article_id.

    1. Correspondance par contenu : code_direction + numero_article + texte.
    2. Repli par ordre d'insertion pour les tirets du décret encore orphelins.
    Idempotent : ne modifie que les tirets JSON sans admin_article_id.
    """
    try:
        from backend.database import get_db_connection
    except ImportError:
        from database import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, numero_article, texte_extrait, code_direction, decret_source "
        "FROM articles ORDER BY id ASC"
    )
    sqlite_articles = [dict(row) for row in cursor.fetchall()]
    conn.close()

    with _lock:
        data = _charger_json()
        deja_lies = {c.get("admin_article_id") for c in data if c.get("admin_article_id")}

        rattaches = 0
        non_trouves = []

        for article in sqlite_articles:
            if article["id"] in deja_lies:
                continue

            art_num = _normaliser_numero_article(article["numero_article"])
            art_text = _normaliser_texte(article["texte_extrait"])
            art_dir = article["code_direction"].strip().upper()
            trouve = False

            for clause in data:
                if clause.get("admin_article_id"):
                    continue
                clause_num = _normaliser_numero_article(clause.get("numero_article", ""))
                clause_text = _normaliser_texte(clause.get("texte_clause", ""))
                clause_dir = clause.get("code_direction", "").strip().upper()

                if art_dir == clause_dir and art_num == clause_num and art_text == clause_text:
                    clause["admin_article_id"] = article["id"]
                    deja_lies.add(article["id"])
                    rattaches += 1
                    trouve = True
                    break

            if not trouve:
                non_trouves.append(article["id"])

        # Repli : articles du décret 2.21.968 encore orphelins ↔ tirets JSON sans lien
        decret_articles = [
            a for a in sqlite_articles
            if a["id"] in non_trouves
            and "2.21.968" in str(a.get("decret_source", ""))
        ]
        tirets_orphelins = [c for c in data if not c.get("admin_article_id")]
        for article, clause in zip(decret_articles, tirets_orphelins):
            clause["admin_article_id"] = article["id"]
            deja_lies.add(article["id"])
            rattaches += 1
            non_trouves.remove(article["id"])

        if rattaches > 0:
            _sauvegarder_json(data)

        return {
            "rattaches": rattaches,
            "deja_lies": len(deja_lies),
            "non_trouves": non_trouves,
        }


def ajouter_article_rag(article_id: int, code_direction: str, numero_article: str,
                         texte_extrait: str, date_version: str = None) -> dict:
    """
    A appeler juste après la création SQLite (create_article), avec
    article_id = new_art['id'] (l'id retourné par lastrowid).
    """
    with _lock:
        data = _charger_json()
        nouvelle_clause = _creer_tiret(
            data, article_id, code_direction, numero_article, texte_extrait, date_version
        )
        _sauvegarder_json(data)
        return nouvelle_clause


def modifier_article_rag(article_id: int, code_direction: str, numero_article: str,
                          texte_extrait: str, date_version: str = None,
                          ancien_texte: str = None) -> bool:
    """
    A appeler juste après l'UPDATE SQLite (update_article).
    Retrouve le tiret via admin_article_id. Si absent, tente un rattachement
    par contenu avant de créer un nouveau tiret (évite les doublons).
    """
    with _lock:
        data = _charger_json()
        clause = _trouver_tiret_par_admin_id(data, article_id)
        if clause is None and ancien_texte:
            clause = _trouver_tiret_par_contenu(
                data, code_direction, numero_article, ancien_texte
            )
            if clause is not None:
                clause["admin_article_id"] = article_id
        if clause is not None:
            clause["code_direction"] = code_direction
            clause["numero_article"] = str(_normaliser_numero_article(numero_article))
            clause["texte_clause"] = texte_extrait
            if date_version:
                clause["date_version"] = date_version
            _sauvegarder_json(data)
            return True
        _creer_tiret(data, article_id, code_direction, numero_article, texte_extrait, date_version)
        _sauvegarder_json(data)
        return True


def supprimer_article_rag(article_id: int, code_direction: str = None,
                           numero_article: str = None, texte_extrait: str = None) -> bool:
    """
    A appeler après le DELETE SQLite (delete_article).
    Retourne True si un tiret correspondant a été trouvé et supprimé.
    """
    with _lock:
        data = _charger_json()
        taille_avant = len(data)
        data = [c for c in data if c.get("admin_article_id") != article_id]
        if len(data) < taille_avant:
            _sauvegarder_json(data)
            return True
        if code_direction and numero_article and texte_extrait:
            clause = _trouver_tiret_par_contenu(data, code_direction, numero_article, texte_extrait)
            if clause is not None:
                data = [c for c in data if c is not clause]
                _sauvegarder_json(data)
                return True
        return False