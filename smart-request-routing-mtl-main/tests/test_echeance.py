import unittest
from datetime import datetime
import sys
import os

# Ajouter le dossier src au chemin de recherche
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app.echeance import calculer_echeance, verifier_alerte

class TestEcheance(unittest.TestCase):
    
    def setUp(self):
        # Date de dépôt fixe : 1er Janvier 2026
        # Date d'échéance calculée (+60 jours) : 2 Mars 2026
        self.date_depot = datetime(2026, 1, 1, 10, 0, 0)
        self.date_echeance_attendue = datetime(2026, 3, 2, 10, 0, 0)
        
    def test_calculer_echeance(self):
        result = calculer_echeance(self.date_depot)
        self.assertEqual(result, self.date_echeance_attendue)
        
    def test_alerte_aucune(self):
        # Date de comparaison : 10 Janvier 2026 (51 jours restants > 15)
        date_du_jour = datetime(2026, 1, 10, 12, 0, 0)
        result = verifier_alerte(self.date_depot, date_du_jour)
        self.assertEqual(result["type_alerte"], "aucune")

    def test_alerte_aucune_limite_basse(self):
        # Date de comparaison : 16 jours restants (14 Février)
        date_du_jour = datetime(2026, 2, 14, 12, 0, 0)
        result = verifier_alerte(self.date_depot, date_du_jour)
        self.assertEqual(result["type_alerte"], "aucune")
        
    def test_alerte_rappel_limite_haute(self):
        # Date de comparaison : 15 jours restants (15 jours avant le 2 Mars = 15 Février)
        date_du_jour = datetime(2026, 2, 15, 12, 0, 0)
        result = verifier_alerte(self.date_depot, date_du_jour)
        self.assertEqual(result["type_alerte"], "rappel")
        
    def test_alerte_rappel_limite_basse(self):
        # Date de comparaison : 6 jours restants (6 jours avant le 2 Mars = 24 Février)
        date_du_jour = datetime(2026, 2, 24, 12, 0, 0)
        result = verifier_alerte(self.date_depot, date_du_jour)
        self.assertEqual(result["type_alerte"], "rappel")
        
    def test_alerte_prioritaire_limite_haute(self):
        # Date de comparaison : 5 jours restants (5 jours avant le 2 Mars = 25 Février)
        date_du_jour = datetime(2026, 2, 25, 12, 0, 0)
        result = verifier_alerte(self.date_depot, date_du_jour)
        self.assertEqual(result["type_alerte"], "prioritaire")
        
    def test_alerte_prioritaire_le_jour_meme(self):
        # Date de comparaison : le jour de l'échéance (0 jour restant)
        date_du_jour = datetime(2026, 3, 2, 9, 0, 0)
        result = verifier_alerte(self.date_depot, date_du_jour)
        self.assertEqual(result["type_alerte"], "prioritaire")
        
    def test_alerte_depasse(self):
        # Date de comparaison : le lendemain de l'échéance (-1 jour restant)
        date_du_jour = datetime(2026, 3, 3, 10, 0, 0)
        result = verifier_alerte(self.date_depot, date_du_jour)
        self.assertEqual(result["type_alerte"], "depasse")
        
    def test_types_invalides(self):
        with self.assertRaises(TypeError):
            calculer_echeance("2026-01-01")
        with self.assertRaises(TypeError):
            verifier_alerte(self.date_depot, "2026-01-01")

if __name__ == "__main__":
    unittest.main()