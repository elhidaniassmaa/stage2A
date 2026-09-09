import unittest
import sys
import os

# Ajouter le dossier src au chemin de recherche pour pouvoir importer les modules de preprocessing
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from preprocessing.clean_text import clean_text
from preprocessing.detect_language import detect_language

class TestPreprocessing(unittest.TestCase):
    
    def test_clean_text_spaces_and_controls(self):
        # Cas 5 : Texte avec espaces/caractères parasites et caractères de contrôle invisibles
        raw_text = "Bonjour   \u200e\u200f le   monde. \n\n Ceci\t est un   test."
        expected = "Bonjour le monde.\nCeci est un test."
        result = clean_text(raw_text)
        self.assertEqual(result["texte_nettoye"], expected)
        self.assertEqual(result["texte_original"], raw_text)
        
    def test_clean_text_arabic_normalization(self):
        # Normalisation d'alif et hamza, suppression des diacritiques
        raw_text = "أحمدُ ذهبَ إلى المدرسةِ. يقرأُ كتاباً في الدفترِ. سؤلٌ رئيسيٌّ."
        expected = "احمد ذهب الى المدرسة. يقرا كتابا في الدفتر. سءل رءيسي."
        result = clean_text(raw_text)
        self.assertEqual(result["texte_nettoye"], expected)

    def test_detect_language_french(self):
        # Cas 2 : Texte français pur
        text = "Bonjour, j'aimerais déposer une réclamation concernant ma facture"
        self.assertEqual(detect_language(text), "fr")
        
    def test_detect_language_arabic_standard(self):
        # Cas 1 : Texte arabe standard (MSA), sans vocabulaire darija -> ar_standard
        text = "مرحبا، أود تقديم شكوى بخصوص فاتورة الكهرباء الخاصة بي."
        self.assertEqual(detect_language(text), "ar_standard")

    def test_detect_language_darija_arabe(self):
        # Cas 1bis (nouveau) : arabe écrit avec vocabulaire darija reconnaissable -> darija_arabe
        text = "واش كاين شي حل ديال هاد المشكل، بغيت نعرف كيفاش نديرها دابا."
        self.assertEqual(detect_language(text), "darija_arabe")
        
    def test_detect_language_mixed(self):
        # Cas 3 : Texte mélangé arabe/français dans le même message -> mixte
        text = "Bonjour, أريد تقديم شكوى بخصوص فاتورة الكهرباء."
        self.assertEqual(detect_language(text), "mixte")
        
    def test_detect_language_darija_latin(self):
        # Cas 4 : Texte darija en caractères latins (Arabizi / Franco-arabe)
        # Ce texte n'utilise pas de caractères arabes et contient du vocabulaire
        # darija reconnaissable -> catégorie dédiée 'darija_latin', distincte de 'mixte'.
        text1 = "choufi hadchi smito chouha bezaf khti"
        text2 = "salam labas 3lik fin knti lbarh dertik f taxi"
        self.assertEqual(detect_language(text1), "darija_latin")
        self.assertEqual(detect_language(text2), "darija_latin")

    def test_detect_language_darija_latin_avec_politesse_francaise(self):
        # Cas 6 : correctif du biais découvert sur les vraies données -- un message
        # darija précédé d'une formule de politesse française ne doit plus être
        # classé "fr" à tort.
        text = "Pour rappel, Wach ghadi ykono kayfin des contrôles 3la les taxis li kayzido f tarif 3la citoyens?"
        self.assertEqual(detect_language(text), "darija_latin")

if __name__ == "__main__":
    unittest.main()