import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from argumentaire.generer_argumentaire import generer_argumentaire
from argumentaire.reglementation import get_best_clause

cas_test = [
    ("DJAC", "Bonjour, mon vol a été retardé de 6 heures sans aucune information de la compagnie."),
    ("DJAC", "طلبت معلومات حول نتائج التحقيق في حادثة طيران وقعت بمطار إقليمي."),
    ("DJAC", "Le contrôle de l'espace aérien pose problème près de l'aéroport, risque de collision signalé."),
    ("DTR", "طلبت رخصة السياقة منذ 3 أشهر ولم أتوصل بأي جواب."),
    # --- Nouveaux cas darija, pour vérifier la couverture linguistique ---
    ("DTR", "Bghit n3ref chno howa lmasar dyal talab ta'hil professionnel dyal transport routier."),
    ("DJAC", "Le temps d'attente est très long au niveau de l'aéroport."),  # témoin français
    ("DAAJJ", "عندي مشكل ديال التقاعد ديالي، الملف ديالي متوقف عند المصالح الإدارية."),
]

for direction, message in cas_test:
    print(f"\n{'='*80}")
    print(f"--- Direction : {direction} ---")
    print(f"Message : {message[:70]}")

    # Affichage des scores de diagnostic (verbose=True) avant de générer l'argumentaire
    _ = get_best_clause(direction, message, verbose=True)

    argumentaire = generer_argumentaire(direction, message)
    print(f"Argumentaire final :\n{argumentaire}\n")