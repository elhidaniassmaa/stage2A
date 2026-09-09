"""
Synchronisation entre la table SQLite `mots_interdits` (interface Administrateur)
et `config/mots_interdits.txt` (fichier lu par moderation.py en repli).

Source de vérité : SQLite (modifiable via l'interface).
Le fichier texte est régénéré à chaque ajout/suppression et au démarrage,
afin que verifier_contenu() et check_mots_cles() utilisent toujours la liste à jour.
"""
import os
import threading

_lock = threading.Lock()

_LANGUE_HEADERS = {
    "Français": "# Français",
    "Arabe standard": "# Arabe classique",
    "Darija": "# Darija",
}

_LANGUE_ORDER = ["Français", "Arabe standard", "Darija"]


def _get_fichier_path():
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "config", "mots_interdits.txt")
    )


def _get_db_connection():
    try:
        from backend.database import get_db_connection
    except ImportError:
        from database import get_db_connection
    return get_db_connection()


def exporter_sqlite_vers_fichier() -> int:
    """
    Régénère config/mots_interdits.txt à partir de la table SQLite.
    Retourne le nombre de mots exportés.
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT mot, langue FROM mots_interdits ORDER BY langue ASC, mot ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    lines = [
        "# Fichier contenant la liste des mots interdits pour la modération.",
        "# Un mot par ligne. Les lignes vides ou commençant par '#' sont ignorées.",
        "# Fichier généré automatiquement depuis la base SQLite — ne pas éditer manuellement.",
        "",
    ]

    by_lang = {lang: [] for lang in _LANGUE_ORDER}
    for row in rows:
        lang = row["langue"]
        if lang not in by_lang:
            by_lang[lang] = []
        by_lang[lang].append(row["mot"])

    for lang in _LANGUE_ORDER:
        mots = by_lang.get(lang, [])
        if not mots and lang not in {r["langue"] for r in rows}:
            continue
        lines.extend(["", _LANGUE_HEADERS.get(lang, f"# {lang}"), ""])
        for mot in mots:
            lines.append(mot)

    # Langues hors liste standard (ex. extensions futures)
    for lang, mots in by_lang.items():
        if lang in _LANGUE_ORDER or not mots:
            continue
        lines.extend(["", f"# {lang}", ""])
        for mot in mots:
            lines.append(mot)

    path = _get_fichier_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    os.replace(tmp_path, path)
    return len(rows)


def synchroniser_mots_interdits() -> dict:
    """Exporte SQLite → fichier. Idempotent, thread-safe."""
    with _lock:
        try:
            count = exporter_sqlite_vers_fichier()
            return {"sync_ok": True, "mots_exportes": count}
        except Exception as e:
            return {"sync_ok": False, "erreur": str(e)}
