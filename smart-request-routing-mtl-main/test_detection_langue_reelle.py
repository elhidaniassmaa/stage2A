import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
from preprocessing.detect_language import detect_language

df = pd.read_excel("data/dataset.xlsx")

resultats = []
for msg in df['Message'].dropna():
    langue_detectee = detect_language(str(msg))
    resultats.append({"message": msg[:70], "langue_detectee": langue_detectee})

df_res = pd.DataFrame(resultats)
print("Répartition des langues détectées sur tout le dataset :")
print(df_res['langue_detectee'].value_counts())
print()

# Affiche 5 exemples de chaque catégorie pour vérification visuelle manuelle
for langue in df_res['langue_detectee'].unique():
    print(f"\n--- Exemples classés '{langue}' ---")
    exemples = df_res[df_res['langue_detectee'] == langue].head(5)
    for _, row in exemples.iterrows():
        print(f"  [{row['langue_detectee']}] {row['message']}")