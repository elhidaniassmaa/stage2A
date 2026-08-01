"""Détection de doublons lors de l'import Excel des demandes citoyennes."""

import hashlib
import unicodedata


def _normalize_field(value: str) -> str:
    """Normalise un champ texte pour comparaison (casse, espaces, unicode)."""
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value).strip().lower())
    return " ".join(text.split())


def compute_demande_fingerprint(nom: str, prenom: str, message_nettoye: str) -> str:
    """
    Calcule une empreinte unique basée sur nom + prénom + message nettoyé.
    Deux demandes identiques sur ces trois champs produiront la même empreinte.
    """
    key = "|".join([
        _normalize_field(nom),
        _normalize_field(prenom),
        _normalize_field(message_nettoye),
    ])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def load_existing_fingerprints(cursor) -> set[str]:
    """Charge les empreintes de toutes les demandes déjà en base."""
    cursor.execute("SELECT nom, prenom, message_nettoye FROM demandes")
    return {
        compute_demande_fingerprint(
            row["nom"] or "",
            row["prenom"] or "",
            row["message_nettoye"] or "",
        )
        for row in cursor.fetchall()
    }
