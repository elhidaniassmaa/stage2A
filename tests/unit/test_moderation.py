import unittest
import sys
import os
from unittest.mock import patch

# Ajouter le dossier src au chemin de recherche
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from moderation.moderation import verifier_contenu

class TestModeration(unittest.TestCase):
    
    def test_clean_texts_model_or_fallback(self):
        # Textes propres
        clean_texts = [
            "Bonjour, je souhaite prendre un rendez-vous pour demain s'il vous plaît.",
            "السلام عليكم، أريد تقديم طلب للحصول على رخصة سكن.",
            "salam, bghit nswl 3la l-wraq dyal l-kart l-watania."
        ]
        for text in clean_texts:
            result = verifier_contenu(text)
            self.assertTrue(result["contenu_valide"], f"Devrait être valide : {text}")
            self.assertIn(result["methode"], ["modele", "mots_cles"])
            
    def test_toxic_texts_fallback_explicit(self):
        # Forcer le repli mots-clés en mockant le pipeline à None
        with patch('moderation.moderation.get_toxicity_pipeline', return_value=None):
            # Test textes toxiques avec insultes légères
            toxic_cases = [
                # Français
                ("C'est vraiment un travail de merde.", False),
                ("Vous êtes vraiment un imbécile !", False),
                # Arabe
                ("أنت شخص غبي جدا ولا تفهم شيء.", False),
                ("هذا تصرف حقير وغير مقبول.", False),
                # Darija latin
                ("hadchi li derti chouha kbira", False),
                ("nta mkelleg a sahbi", False)
            ]
            for text, expected_valid in toxic_cases:
                result = verifier_contenu(text)
                self.assertEqual(result["contenu_valide"], expected_valid, f"Vérification échouée pour : {text}")
                self.assertEqual(result["methode"], "mots_cles")
                self.assertEqual(result["score_confiance"], 1.0)

    def test_clean_texts_fallback_explicit(self):
        # Forcer le repli mots-clés en mockant le pipeline à None
        with patch('moderation.moderation.get_toxicity_pipeline', return_value=None):
            clean_texts = [
                "Je voudrais savoir comment faire la demande.",
                "احمد شخص محترم ومهذب.",
                "l-khir in chaa allah dima labas"
            ]
            for text in clean_texts:
                result = verifier_contenu(text)
                self.assertTrue(result["contenu_valide"], f"Devrait être valide : {text}")
                self.assertEqual(result["methode"], "mots_cles")
                self.assertEqual(result["score_confiance"], 1.0)

    def test_error_handling(self):
        # Tester que la fonction ne lève pas d'exception et retourne True par défaut en cas de plantage
        with patch('moderation.moderation.load_forbidden_words', side_effect=RuntimeError("Fichier inaccessible")):
            with patch('moderation.moderation.get_toxicity_pipeline', return_value=None):
                result = verifier_contenu("con")
                # Doit être True par défaut, avec score de 0
                self.assertTrue(result["contenu_valide"])
                self.assertEqual(result["score_confiance"], 0.0)
                self.assertEqual(result["methode"], "mots_cles")

if __name__ == "__main__":
    unittest.main()
