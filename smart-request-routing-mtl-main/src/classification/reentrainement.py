import os
import sys
import shutil
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Dictionnaire de correspondance des labels (identique au classificateur)
LABEL_MAP = {
    'DSI': 0,
    'DSPCT': 1,
    'DAAJJ': 2,
    'DMM': 3,
    'DTR': 4,
    'DJAC': 5,
    'Cabinet du Ministère': 6,
    'Non concerné': 7
}
INV_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}

# Ajouter le dossier src au chemin de recherche pour pouvoir importer les modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def load_and_merge_datasets() -> pd.DataFrame:
    """
    Charge le dataset de base et le fichier des corrections, les fusionne
    en utilisant la décision finale du responsable comme label, et sauvegarde
    le dataset enrichi.
    """
    # 1. Charger le dataset original
    data_paths = ["data/dataset_final_fusionne.xlsx", "data/dataset.xlsx"]
    orig_path = None
    for path in data_paths:
        if os.path.exists(path):
            orig_path = path
            break
        elif os.path.exists(os.path.join("../../", path)):
            orig_path = os.path.join("../../", path)
            break
            
    if orig_path is None:
        raise FileNotFoundError("Dataset original (dataset.xlsx ou dataset_final_fusionne.xlsx) non trouvé.")
        
    df_orig = pd.read_excel(orig_path)
    print(f"Chargement réussi : {len(df_orig)} lignes depuis {orig_path}")
    
    # 2. Charger le fichier historique_corrections.xlsx
    corr_paths = ["data/historique_corrections.xlsx", "historique_corrections.xlsx"]
    corr_path = None
    for path in corr_paths:
        if os.path.exists(path):
            corr_path = path
            break
        elif os.path.exists(os.path.join("../../", path)):
            corr_path = os.path.join("../../", path)
            break
            
    if corr_path is None:
        raise FileNotFoundError(
            "Fichier historique_corrections.xlsx non trouvé. "
            "Veuillez le placer dans le dossier data/."
        )
        
    df_corr = pd.read_excel(corr_path)
    print(f"Chargement réussi : {len(df_corr)} nouvelles corrections depuis {corr_path}")
    
    # S'assurer que les colonnes nécessaires existent
    if 'Message' not in df_corr.columns or 'Direction_validee' not in df_corr.columns:
        raise ValueError("Le fichier des corrections doit contenir les colonnes 'Message' et 'Direction_validee'.")
        
    # Renommer la colonne Direction_validee pour correspondre à 'Entité responsable'
    df_corr_renamed = df_corr.rename(columns={"Direction_validee": "Entité responsable"})
    
    # Alignement et fusion des colonnes
    df_enriched = pd.concat([df_orig, df_corr_renamed], ignore_index=True)
    
    # Enregistrer le fichier fusionné pour train_classifier
    enriched_path = "data/dataset_enriched.xlsx"
    df_enriched.to_excel(enriched_path, index=False)
    print(f"Jeu de données enrichi ({len(df_enriched)} lignes) sauvegardé sous {enriched_path}")
    
    return df_enriched

def evaluate_model_on_data(model_path: str, df_test: pd.DataFrame) -> dict:
    """
    Évalue un modèle de classification BERT sur un jeu de test donné.
    """
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    
    if not os.path.exists(model_path):
        print(f"Avertissement : Modèle non trouvé à {model_path}.")
        return None
        
    print(f"Évaluation du modèle à {model_path} sur le jeu de test...")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model.eval()
    
    # Appliquer clean_text si disponible
    try:
        from preprocessing.clean_text import clean_text
        df_test['cleaned_message'] = df_test['Message'].apply(lambda x: clean_text(str(x))["texte_nettoye"])
    except Exception:
        df_test['cleaned_message'] = df_test['Message'].astype(str)
        
    df_test['label'] = df_test['Entité responsable'].map(LABEL_MAP)
    df_test = df_test.dropna(subset=['label', 'cleaned_message'])
    
    preds = []
    batch_size = 16
    messages = list(df_test['cleaned_message'])
    
    for i in range(0, len(messages), batch_size):
        batch_msgs = messages[i:i+batch_size]
        inputs = tokenizer(batch_msgs, return_tensors="pt", padding=True, truncation=True, max_length=128)
        with torch.no_grad():
            outputs = model(**inputs)
            batch_preds = torch.argmax(outputs.logits, dim=1).tolist()
            preds.extend(batch_preds)
            
    target_names = [INV_LABEL_MAP[i] for i in range(len(LABEL_MAP))]
    report = classification_report(
        list(df_test['label']), 
        preds, 
        target_names=target_names, 
        zero_division=0,
        output_dict=True
    )
    return report

def print_comparison_report(old_report: dict, new_report: dict):
    """
    Affiche un tableau comparatif détaillé des performances avant/après réentraînement.
    """
    print("\n" + "="*80)
    print(" COMPARAISON DES PERFORMANCES DU CLASSIFICATEUR (F1-SCORE & PRECISION) ".center(80, "="))
    print("="*80)
    
    header = f"{'Classe / Direction':<25} | {'F1 Ancien':<10} | {'F1 Nouveau':<10} | {'Prec. Anc.':<10} | {'Prec. Nouv.':<11}"
    print(header)
    print("-" * 80)
    
    for cls in LABEL_MAP.keys():
        old_f1 = old_report.get(cls, {}).get("f1-score", 0.0) if old_report else 0.0
        new_f1 = new_report.get(cls, {}).get("f1-score", 0.0) if new_report else 0.0
        
        old_prec = old_report.get(cls, {}).get("precision", 0.0) if old_report else 0.0
        new_prec = new_report.get(cls, {}).get("precision", 0.0) if new_report else 0.0
        
        # Indicateur visuel d'amélioration (caractères ASCII pour compatibilité d'encodage Windows)
        diff = new_f1 - old_f1
        arrow = "[+]" if diff > 0.01 else ("[-]" if diff < -0.01 else "[=]")
        
        print(f"{cls:<25} | {old_f1:>9.2f}  | {new_f1:>9.2f} {arrow} | {old_prec:>9.2f}  | {new_prec:>10.2f}")
        
    print("-" * 80)
    # Comparaison de l'exactitude globale
    old_acc = old_report.get("accuracy", 0.0) if old_report else 0.0
    new_acc = new_report.get("accuracy", 0.0) if new_report else 0.0
    acc_diff = new_acc - old_acc
    acc_arrow = "[+]" if acc_diff > 0.01 else ("[-]" if acc_diff < -0.01 else "[=]")
    
    print(f"{'Exactitude globale (Acc)':<25} | {old_acc:>9.2f}  | {new_acc:>9.2f} {acc_arrow} | {'-':>9}  | {'-':>10}")
    print("="*80 + "\n")

def replace_production_model(temp_path: str, prod_path: str):
    """
    Remplace en toute sécurité le modèle en production en conservant un backup.
    """
    print(f"Déploiement du nouveau modèle en production...")
    try:
        if os.path.exists(prod_path):
            backup_path = prod_path.rstrip("/") + "_backup/"
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            shutil.copytree(prod_path, backup_path)
            print(f"Sauvegarde de sécurité créée à : {backup_path}")
            shutil.rmtree(prod_path)
            
        shutil.copytree(temp_path, prod_path)
        print(f"Nouveau modèle opérationnel en production à : {prod_path}")
        shutil.rmtree(temp_path)
    except Exception as e:
        print(f"Erreur critique lors du déploiement : {e}")

def main():
    # 1. Charger et fusionner les datasets
    df_enriched = load_and_merge_datasets()
    
    # 2. Préparer le jeu de test identique pour la comparaison équitable
    df_enriched['label'] = df_enriched['Entité responsable'].map(LABEL_MAP)
    df_enriched = df_enriched.dropna(subset=['label', 'Message'])
    
    _, temp_df = train_test_split(
        df_enriched, 
        test_size=0.30, 
        random_state=42, 
        stratify=df_enriched['label']
    )
    _, test_df = train_test_split(
        temp_df, 
        test_size=0.50, 
        random_state=42, 
        stratify=temp_df['label']
    )
    # 3. Évaluer l'ancien modèle (de production)
    prod_path = "models/classification/"
    old_report = evaluate_model_on_data(prod_path, test_df)
    
    # 4. Configurer la sauvegarde temporaire pour le nouvel entraînement
    temp_path = "models/classification_temp/"
    os.environ["CLASSIFIER_SAVE_PATH"] = temp_path
    os.environ["DATASET_PATH"] = "data/dataset_enriched.xlsx"
    
    # Lancer le script d'entraînement principal
    print("Lancement du réentraînement sur le dataset enrichi...")
    try:
        from classification.train_classifier import main as run_training
        run_training()
    except Exception as e:
        print(f"Erreur lors de l'entraînement : {e}")
        # Nettoyer l'environnement et le dataset temporaire
        if os.path.exists("data/dataset_enriched.xlsx"):
            os.remove("data/dataset_enriched.xlsx")
        sys.exit(1)
 
    # 5. Évaluer le nouveau modèle réentraîné
    new_report = evaluate_model_on_data(temp_path, test_df)
    
    # 6. Afficher le rapport de comparaison des métriques
    print_comparison_report(old_report, new_report)
    
    # 7. Remplacer le modèle en production
    replace_production_model(temp_path, prod_path)
    
    # Nettoyage du fichier temporaire de dataset enrichi
    if os.path.exists("data/dataset_enriched.xlsx"):
        os.remove("data/dataset_enriched.xlsx")
    print("Processus de réentraînement et déploiement terminé avec succès !")

if __name__ == "__main__":
    main()
