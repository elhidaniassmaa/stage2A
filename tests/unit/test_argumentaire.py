import unittest
import sys
import os

# Ajouter le dossier src au chemin de recherche
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from argumentaire.reglementation import get_articles
from argumentaire.generer_argumentaire import generer_argumentaire

class TestReglementation(unittest.TestCase):
    
    def test_get_articles_dtr(self):
        # DTR doit retourner 1 article (l'article 9)
        articles = get_articles("DTR")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["numero_article"], "9")
        self.assertIn("Direction des Transports Routiers", articles[0]["texte_article"])
        
    def test_get_articles_djac(self):
        # DJAC doit retourner 3 articles (6, 7, 8)
        articles = get_articles("DJAC")
        self.assertEqual(len(articles), 3)
        numbers = [art["numero_article"] for art in articles]
        self.assertListEqual(sorted(numbers), ["6", "7", "8"])
        
    def test_get_articles_case_insensitivity(self):
        # Test de l'insensibilité à la casse
        articles_upper = get_articles("DMM")
        articles_lower = get_articles("dmm")
        self.assertEqual(len(articles_upper), 1)
        self.assertEqual(articles_upper, articles_lower)
        
    def test_get_articles_cabinet(self):
        # Cabinet du Ministère
        articles = get_articles("Cabinet du Ministère")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["numero_article"], "Hors décret")
        
    def test_get_articles_invalid(self):
        # Cas invalides ou inexistants
        self.assertEqual(len(get_articles("")), 0)
        self.assertEqual(len(get_articles("INEXISTANTE")), 0)
        self.assertEqual(len(get_articles(None)), 0)

class TestGenererArgumentaire(unittest.TestCase):
    
    def test_generer_argumentaire_dtr_fallback(self):
        # En l'absence de LLM local, doit retourner le message de repli citant l'article 9
        demande = "Je voudrais me renseigner sur le permis de conduire."
        res = generer_argumentaire("DTR", demande)
        self.assertIn("DTR", res)
        self.assertIn("article 9 du décret n° 2.21.968", res)
        self.assertIn("Direction des Transports Routiers", res)
        
    def test_generer_argumentaire_non_concerne(self):
        # Cas où aucune direction n'est compétente
        demande = "Je veux acheter un appartement."
        res = generer_argumentaire("Non concerné", demande)
        self.assertEqual(res, "Aucune direction du Ministère du Transport et de la Logistique n'est compétente pour traiter cette demande.")
        
        res_empty = generer_argumentaire("INVALIDE", demande)
        self.assertEqual(res_empty, "Aucune direction du Ministère du Transport et de la Logistique n'est compétente pour traiter cette demande.")

    def test_generer_argumentaire_cabinet_fallback(self):
        demande = "Demande d'audience privée avec le Ministre."
        res = generer_argumentaire("Cabinet du Ministère", demande)
        self.assertIn("Cabinet du Ministère", res)
        self.assertIn("le rôle du Cabinet du Ministère", res)
        self.assertIn("assiste directement le membre du gouvernement", res)

if __name__ == "__main__":
    unittest.main()
