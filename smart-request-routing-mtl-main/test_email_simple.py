import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from backend.notifications import envoyer_email_alerte

resultat = envoyer_email_alerte(
    destinataire="elhidaniassmaa00@gmail.com",  # envoyez-vous l'email à vous-même pour ce test
    numero_demande="GEDEC-2026-TEST",
    direction="DTR",
    jours_restants=5
)

print(f"\nRésultat de l'envoi : {'✅ Succès' if resultat else '❌ Échec'}")