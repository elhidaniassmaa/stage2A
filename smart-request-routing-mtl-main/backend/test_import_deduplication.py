"""Test d'intégration : réimport Excel → doublons ignorés sur la base canonique."""
import io
import os
import sys
import sqlite3
import tempfile
import unittest

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from backend.database import DATABASE_PATH, get_db_connection
from backend.deduplication import compute_demande_fingerprint, load_existing_fingerprints


class TestImportDeduplicationIntegration(unittest.TestCase):
    UNIQUE_MSG = "[TEST_DEDUP_20260801] Route nationale en mauvais état près de Rabat"
    NOM = "TestDedup"
    PRENOM = "Integration"

    @classmethod
    def setUpClass(cls):
        cls.conn = get_db_connection()
        cls.cursor = cls.conn.cursor()
        from preprocessing.clean_text import clean_text
        cls.cleaned = clean_text(cls.UNIQUE_MSG)["texte_nettoye"]
        cls.fingerprint = compute_demande_fingerprint(cls.NOM, cls.PRENOM, cls.cleaned)
        cls.cursor.execute(
            "SELECT id FROM demandes WHERE nom=? AND prenom=? AND message_original=?",
            (cls.NOM, cls.PRENOM, cls.UNIQUE_MSG),
        )
        if cls.cursor.fetchone() is None:
            cls.cursor.execute(
                """INSERT INTO demandes (
                    nom, prenom, message_original, message_nettoye, date_depot, date_echeance,
                    type_alerte, contenu_valide, mot_interdit_detecte, direction_predite,
                    score_confiance, confiance_faible, argumentaire, decision_responsable,
                    statut_demande, region
                ) VALUES (?, ?, ?, ?, datetime('now'), datetime('now', '+60 days'),
                    'aucune', 1, 0, 'DTR', 0.9, 0, 'test', 'Validé', 'En attente', 'Test')""",
                (cls.NOM, cls.PRENOM, cls.UNIQUE_MSG, cls.cleaned),
            )
            cls.conn.commit()

    def test_canonical_db_path(self):
        expected = os.path.abspath(os.path.join(os.path.dirname(__file__), "gedec.db"))
        self.assertEqual(os.path.normpath(DATABASE_PATH), os.path.normpath(expected))

    def test_fingerprint_in_existing_set(self):
        fps = load_existing_fingerprints(self.cursor)
        self.assertIn(self.fingerprint, fps)

    def test_simulated_reimport_skips_duplicate(self):
        """Simule la logique upload sans lancer le pipeline IA complet."""
        existing = load_existing_fingerprints(self.cursor)
        batch: set[str] = set()
        rows = [
            {"Nom": self.NOM, "Prénom": self.PRENOM, "Message": self.UNIQUE_MSG},
            {"Nom": "Autre", "Prénom": "Citoyen", "Message": "[TEST_DEDUP_20260801] Message totalement unique xyz"},
        ]
        importees = 0
        doublons = 0
        from preprocessing.clean_text import clean_text
        for row in rows:
            cleaned = clean_text(row["Message"])["texte_nettoye"]
            fp = compute_demande_fingerprint(row["Nom"], row["Prénom"], cleaned)
            if fp in existing or fp in batch:
                doublons += 1
                continue
            batch.add(fp)
            importees += 1

        self.assertEqual(doublons, 1, "La ligne déjà en base doit être détectée comme doublon")
        self.assertEqual(importees, 1, "Seule la ligne nouvelle doit passer")


if __name__ == "__main__":
    print(f"Base testée : {DATABASE_PATH}")
    unittest.main(verbosity=2)
