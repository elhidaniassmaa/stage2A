from datetime import datetime, timedelta

def calculer_echeance(date_depot: datetime) -> datetime:
    """
    Calcule la date d'échéance à partir de la date de dépôt (date_depot + 60 jours).
    
    Arguments :
    - date_depot : datetime représentant la date de soumission.
    
    Retourne :
    - datetime : date de dépôt + 60 jours.
    """
    if not isinstance(date_depot, datetime):
        raise TypeError("date_depot doit être une instance de datetime.")
    return date_depot + timedelta(days=60)

def verifier_alerte(date_depot: datetime, date_du_jour: datetime = None) -> dict:
    """
    Détermine l'alerte à générer selon le nombre de jours calendaires restants avant l'échéance.
    
    Arguments :
    - date_depot : datetime représentant la date de soumission.
    - date_du_jour : datetime facultatif représentant la date de comparaison (défaut : date système actuelle).
    
    Retourne un dictionnaire :
    - {"type_alerte": "aucune"} si plus de 15 jours restants.
    - {"type_alerte": "rappel"} si entre 6 et 15 jours restants (inclus).
    - {"type_alerte": "prioritaire"} si 5 jours ou moins restants (inclus).
    - {"type_alerte": "depasse"} si la date d'échéance est dépassée.
    """
    if not isinstance(date_depot, datetime):
        raise TypeError("date_depot doit être une instance de datetime.")
        
    if date_du_jour is None:
        date_du_jour = datetime.now()
    elif not isinstance(date_du_jour, datetime):
        raise TypeError("date_du_jour doit être une instance de datetime.")
        
    # Calcul de la date d'échéance (+60 jours)
    echeance = calculer_echeance(date_depot)
    
    # Calcul de la différence en jours calendaires
    jours_restants = (echeance.date() - date_du_jour.date()).days
    
    if jours_restants < 0:
        return {"type_alerte": "depasse"}
    elif jours_restants <= 5:
        return {"type_alerte": "prioritaire"}
    elif jours_restants <= 15:
        return {"type_alerte": "rappel"}
    else:
        return {"type_alerte": "aucune"}
