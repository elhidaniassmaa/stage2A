import pandas as pd
df = pd.read_excel("data/dataset.xlsx")
print("Lignes totales:", len(df))
print("Colonnes:", df.columns.tolist())
df2 = df.dropna(subset=['Message', 'Entité responsable'])
print("Lignes après dropna:", len(df2))
LABEL_MAP_KEYS = ['DSI', 'DSPCT', 'DAAJJ', 'DMM', 'DTR', 'DJAC', 'Cabinet du Ministère', 'Non concerné']
df3 = df2[df2['Entité responsable'].isin(LABEL_MAP_KEYS)]
print("Lignes finales exploitables:", len(df3))
print(df3['Entité responsable'].value_counts())