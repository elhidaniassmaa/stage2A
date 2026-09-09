import unittest
import sys
import os

# Ajouter le dossier src au chemin de recherche
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from classification.predict import predire_direction

class TestClassification(unittest.TestCase):
    def test_predict_format(self):
        # Vérifier que la fonction de prédiction retourne le bon format de sortie
        texte = "السلام عليكم، طلبت رخصة السياقة منذ 3 أشهر ولم أتوصل بأي جواب."

        # Inférence
        result = predire_direction(texte)

        print(f"\n>>> Direction prédite : {result['direction_predite']}")
        print(f">>> Score de confiance : {result['score_confiance']:.4f}")
        print(f">>> Confiance faible : {result['indicateur_confiance_faible']}")

        # Vérification des clés de sortie
        self.assertIn("direction_predite", result)
        self.assertIn("score_confiance", result)
        self.assertIn("indicateur_confiance_faible", result)

        # Vérification des types
        self.assertIsInstance(result["direction_predite"], str)
        self.assertIsInstance(result["score_confiance"], float)
        self.assertIsInstance(result["indicateur_confiance_faible"], bool)    
    def test_predict_empty_text(self):
        # Vérification du comportement par défaut avec un texte vide
        result = predire_direction("")
        self.assertEqual(result["direction_predite"], "Non concerné")
        self.assertEqual(result["score_confiance"], 0.0)
        self.assertTrue(result["indicateur_confiance_faible"])

if __name__ == "__main__":
    unittest.main()
