import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ajouter le dossier src au chemin pour importer correctement les modules
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.main import app
from backend.database import init_db

class TestGedecAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialiser la base de données de test SQLite
        init_db()
        cls.client = TestClient(app)

    def test_01_login_admin_success(self):
        # Tester la connexion d'un admin avec de bons identifiants
        payload = {
            "email": "admin@transport.gov.ma",
            "password": "password123",
            "role": "Administrateur"
        }
        response = self.client.post("/api/auth/login", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["nom_complet"], "Admin Principal")
        self.assertEqual(data["role"], "Administrateur")
        self.assertEqual(data["statut"], "ACTIF")

    def test_02_login_responsable_success(self):
        # Tester la connexion d'un responsable
        payload = {
            "email": "a.benali@transport.gov.ma",
            "password": "password123",
            "role": "Responsable"
        }
        response = self.client.post("/api/auth/login", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["nom_complet"], "Ahmed Benali")
        self.assertEqual(data["role"], "Responsable")

    def test_03_login_wrong_credentials(self):
        # Tester l'échec de connexion avec de mauvais identifiants
        payload = {
            "email": "admin@transport.gov.ma",
            "password": "wrongpassword",
            "role": "Administrateur"
        }
        response = self.client.post("/api/auth/login", json=payload)
        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.json())

    def test_04_dashboard_stats(self):
        # Tester l'endpoint de KPIs
        response = self.client.get("/api/dashboard/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_demandes", data)
        self.assertIn("demandes_traitees", data)
        self.assertIn("en_attente", data)
        self.assertIn("urgent_depasse", data)

    def test_05_get_demandes(self):
        # Tester l'obtention de la liste des demandes
        response = self.client.get("/api/demandes")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertTrue(len(response.json()) > 0)

    def test_06_get_articles(self):
        # Tester l'obtention des articles de la base réglementaire
        response = self.client.get("/api/base-reglementaire")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertTrue(len(response.json()) > 0)

    def test_07_get_responsables(self):
        # Tester l'obtention des responsables
        response = self.client.get("/api/responsables")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertTrue(len(response.json()) > 0)

    def test_08_get_logs(self):
        # Tester l'obtention du journal d'activité
        response = self.client.get("/api/logs")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertTrue(len(response.json()) > 0)

    def test_09_get_mots_interdits(self):
        # Tester l'obtention des mots interdits pour la langue française
        response = self.client.get("/api/mots-interdits?langue=Français")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertTrue(len(response.json()) > 0)

if __name__ == "__main__":
    unittest.main()
