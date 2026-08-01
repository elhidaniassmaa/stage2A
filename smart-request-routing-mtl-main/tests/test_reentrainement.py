import unittest
import pandas as pd
import os
import sys
import shutil
from unittest.mock import patch

# Ajouter le dossier src au chemin de recherche
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from classification.reentrainement import main as run_reentrainement

class TestReentrainement(unittest.TestCase):
    
    def setUp(self):
        # Créer le dossier data s'il n'existe pas
        os.makedirs("data", exist_ok=True)
        self.corrections_path = "data/historique_corrections.xlsx"
        
        # Créer un fichier de corrections factice pour les tests
        data_corr = {
            "Message": [
                "Je voudrais savoir comment obtenir mon permis.",
                "Le bateau marchand est bloqué au port de Tanger.",
                "Problème technique sur le serveur informatique.",
                "Demande d'autorisation pour un vol charter."
            ],
            "Direction_validee": ["DTR", "DMM", "DSI", "DJAC"]
        }
        self.df_corr = pd.DataFrame(data_corr)
        self.df_corr.to_excel(self.corrections_path, index=False)
        
    def tearDown(self):
        # Nettoyer les fichiers de test
        if os.path.exists(self.corrections_path):
            os.remove(self.corrections_path)
        if os.path.exists("data/dataset_enriched.xlsx"):
            os.remove("data/dataset_enriched.xlsx")
            
        # Supprimer le backup de test s'il existe
        backup_path = "models/classification_backup"
        if os.path.exists(backup_path):
            shutil.rmtree(backup_path)
            
    @patch('classification.reentrainement.replace_production_model')
    @patch('classification.reentrainement.evaluate_model_on_data')
    def test_reentrainement_flow(self, mock_eval, mock_replace):
        # Mocker les retours d'évaluation pour simuler la comparaison de modèles
        mock_eval.side_effect = [
            {"DTR": {"f1-score": 0.5, "precision": 0.6}, "accuracy": 0.55}, # Ancien
            {"DTR": {"f1-score": 0.7, "precision": 0.8}, "accuracy": 0.75}  # Nouveau
        ]
        
        # Mocker l'appel de réentraînement de train_classifier pour éviter l'apprentissage sur CPU
        with patch('classification.train_classifier.main') as mock_training:
            # Lancement du réentraînement
            run_reentrainement()
            
            # Vérifications
            self.assertTrue(mock_training.called)
            self.assertTrue(mock_eval.called)
            self.assertTrue(mock_replace.called)

if __name__ == "__main__":
    unittest.main()
