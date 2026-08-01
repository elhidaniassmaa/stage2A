import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)


def envoyer_email_alerte(destinataire: str, numero_demande: str, direction: str, jours_restants: int) -> bool:
    """
    Envoie un email d'alerte prioritaire au Responsable concerné.
    Retourne True si l'envoi a réussi, False sinon (sans jamais lever d'exception
    bloquante -- une alerte email en échec ne doit jamais planter le système).
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[EMAIL] Configuration SMTP absente (variables d'environnement non définies). Email non envoyé.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_FROM
        msg["To"] = destinataire
        msg["Subject"] = f"⚠️ Alerte prioritaire — Demande {numero_demande} ({jours_restants} jours restants)"

        corps = f"""
Bonjour,

La demande {numero_demande}, affectée à la direction {direction}, arrive à échéance légale dans {jours_restants} jour(s) (délai réglementaire de 60 jours, Décret n° 2.17.265, article 8).

Merci de traiter ce dossier en priorité.

-- Plateforme GEDEC
"""
        msg.attach(MIMEText(corps, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"[EMAIL] Alerte envoyée avec succès à {destinataire} pour {numero_demande}.")
        return True

    except Exception as e:
        print(f"[EMAIL] Échec de l'envoi à {destinataire} : {e}")
        return False