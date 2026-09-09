import unittest
import pandas as pd
from datetime import datetime
import sys
import os

# Ajouter le dossier src au chemin de recherche
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.rapport import generer_rapport, generer_graphiques

class TestRapport(unittest.TestCase):
    
    def setUp(self):
        # Création d'un DataFrame fictif d'historique pour valider les calculs
        data = {
            "Message": ["Demande 1", "Demande 2", "Demande 3", "Demande 4"],
            "Direction proposée": ["DTR", "DMM", "DTR", "DSI"],
            "Décision du Responsable": ["Validé", "Corriger : DMM", "Corriger : DSI", "Validé"],
            "Score de confiance": [0.85, 0.90, 0.45, 0.70],
            "Région de la réclamation": ["Rabat", "Casablanca", "Rabat", "Tanger"],
            "Date de dépôt": [
                datetime(2026, 1, 1),
                datetime(2026, 1, 5),
                datetime(2026, 2, 1),
                datetime(2026, 2, 10)
            ],
            "Date de réponse attendue": [
                datetime(2026, 3, 2),
                datetime(2026, 3, 6),
                datetime(2026, 4, 2),
                datetime(2026, 4, 11)
            ],
            "Date de réponse": [
                datetime(2026, 2, 15), # Respecté (45j restants)
                datetime(2026, 3, 10), # Dépassé (4 jours après)
                datetime(2026, 3, 15), # Respecté (18 jours avant)
                None                   # Non répondu
            ]
        }
        self.df = pd.DataFrame(data)
        
    def test_generer_rapport_metrics(self):
        res = generer_rapport(self.df)
        
        # 1. Total
        self.assertEqual(res["total_demandes"], 4)
        
        # 2. Directions
        # DTR (2), DMM (1), DSI (1)
        self.assertEqual(res["repartition_direction"]["DTR"]["nombre"], 2)
        self.assertEqual(res["repartition_direction"]["DTR"]["pourcentage"], 50.0)
        self.assertEqual(res["repartition_direction"]["DMM"]["nombre"], 1)
        
        # 3. Régions
        # Rabat (2), Casablanca (1), Tanger (1)
        self.assertEqual(res["repartition_region"]["Rabat"], 2)
        self.assertEqual(res["repartition_region"]["Casablanca"], 1)
        
        # 4. Respect des délais (demandes avec réponse)
        # Demandes avec réponse : 3 (Lignes 0, 1, 2)
        # Lignes respectées : 0 (15 Fév <= 2 Mar) et 2 (15 Mar <= 2 Avr) -> 2/3 = 66.66%
        self.assertAlmostEqual(res["taux_respect"], 66.666666, places=2)
        
        # 5. Concordance (Validé vs Corrigé)
        # Concordants : 
        # Ligne 0 : Validé -> Oui
        # Ligne 1 : Corriger : DMM == DMM (Direction proposée) -> Oui
        # Ligne 2 : Corriger : DSI != DTR -> Non
        # Ligne 3 : Validé -> Oui
        # Total : 3/4 = 75.0%
        self.assertEqual(res["taux_concordance"], 75.0)
        
        # 6. Score moyen
        # (0.85 + 0.90 + 0.45 + 0.70) / 4 = 2.90 / 4 = 0.725
        self.assertAlmostEqual(res["score_confiance_moyen"], 0.725)
        
        # Évolution
        self.assertEqual(len(res["evolution_respect"]["periodes"]), 2) # Janvier et Février
        
    def test_generer_graphiques(self):
        res = generer_rapport(self.df)
        fig1, fig2 = generer_graphiques(res)
        
        self.assertIsNotNone(fig1)
        self.assertIsNotNone(fig2)

if __name__ == "__main__":
    unittest.main()
