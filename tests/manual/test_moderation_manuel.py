import sys
import os
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from moderation.moderation import verifier_contenu, check_mots_cles

textes_test = [
    ("Neutre français", "Bonjour, je voudrais des informations sur le renouvellement de mon permis de conduire."),
    ("Insulte français claire", "Vous êtes vraiment des incapables, ce service est une honte, bande de connards."),
    ("Neutre arabe", "طلبت رخصة السياقة منذ 3 أشهر ولم أتوصل بأي جواب"),
    ("Darija insultant (cas difficile)", "nta 3andek chi mkhx, rah lmasalh dyalkom khayba"),
    ("Darija insultant avec 'hmar'", "rak 7imar, ma3endkch 7a9 ndir hadchi"),
    ("Arabe insultant clair", "انتم حمير وكذابون في هذه الإدارة"),
]

print("="*70)
print("TEST : verifier_contenu (modèle + mots-clés combinés)")
print("="*70)
for nom, texte in textes_test:
    resultat = verifier_contenu(texte)
    statut = "✅ VALIDE" if resultat["contenu_valide"] else "🚫 SIGNALÉ"
    print(f"\n[{nom}]")
    print(f"Texte : {texte[:60]}...")
    print(f"Résultat : {statut} | score={resultat['score_confiance']:.2f} | méthode={resultat['methode']}")

print("\n" + "="*70)
print("TEST : check_mots_cles seul (pour vérifier la liste enrichie isolément)")
print("="*70)
for nom, texte in textes_test:
    resultat = check_mots_cles(texte)
    statut = "✅ VALIDE" if resultat["contenu_valide"] else "🚫 SIGNALÉ"
    print(f"[{nom}] -> {statut}")