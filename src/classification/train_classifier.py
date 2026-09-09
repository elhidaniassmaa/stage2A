import os
import sys
import numpy as np
import pandas as pd
import torch

# Ajouter le dossier src au chemin de recherche pour pouvoir importer preprocessing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
    TrainerCallback,
)

# Configuration pour éviter les avertissements de parallélisation sur certains systèmes
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Dictionnaire de correspondance des labels
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

class RequestDataset(torch.utils.data.Dataset):
    """
    Dataset PyTorch standard pour l'entraînement avec le Trainer d'Hugging Face.
    """
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx], dtype=torch.long)
        return item

    def __len__(self):
        return len(self.labels)

def load_data():
    """
    Charge les données depuis dataset.xlsx.
    """
    data_paths = [os.environ.get("DATASET_PATH", "data/dataset.xlsx")]
    data_path = None
    for path in data_paths:
        if os.path.exists(path):
            data_path = path
            break
            
    if data_path is None:
        raise FileNotFoundError(
            "Aucun fichier de données trouvé. Veuillez placer dataset.xlsx dans le dossier data/."
        )
        
    print(f"Chargement des données depuis : {data_path}")
    df = pd.read_excel(data_path)
    
    # Nettoyage des colonnes nécessaires
    df = df.dropna(subset=['Message', 'Entité responsable'])
    
    # Filtrer les classes inconnues
    df = df[df['Entité responsable'].isin(LABEL_MAP.keys())]
    
    # Mapper les labels textuels en entiers
    df['label'] = df['Entité responsable'].map(LABEL_MAP)
    
    return df

class EpochProgressCallback(TrainerCallback):
    """Rapporte la progression à chaque fin d'époque via un callback optionnel."""

    def __init__(self, progress_callback, num_epochs, base_pct=20, span_pct=65):
        self.progress_callback = progress_callback
        self.num_epochs = num_epochs
        self.base_pct = base_pct
        self.span_pct = span_pct
        self.last_loss = None

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs and "loss" in logs:
            self.last_loss = logs["loss"]

    def on_epoch_end(self, args, state, control, **kwargs):
        if not self.progress_callback:
            return
        epoch = int(state.epoch)
        pct = self.base_pct + int((epoch / self.num_epochs) * self.span_pct)
        loss_msg = f" - Perte: {self.last_loss:.4f}" if self.last_loss is not None else ""
        self.progress_callback(
            pct,
            f"Époque {epoch}/{self.num_epochs}{loss_msg}",
            epoch_actuelle=epoch,
            epoch_totale=self.num_epochs,
        )


def main(progress_callback=None):
    # 1. Charger et préparer les données
    df = load_data()
    print(f"Nombre total de lignes chargées et valides : {len(df)}")
    
    # Appliquer clean_text si possible pour harmoniser le format des messages
    try:
        from preprocessing.clean_text import clean_text
        print("Application du prétraitement clean_text sur les messages...")
        df['cleaned_message'] = df['Message'].apply(lambda x: clean_text(str(x))["texte_nettoye"])
    except Exception as e:
        print(f"Avertissement lors de l'import ou l'application de clean_text : {e}. Utilisation du texte brut.")
        df['cleaned_message'] = df['Message'].astype(str)

    # 2. Séparation stratifiée : Train (70%), Validation (15%), Test (15%)
    # On fait deux divisions successives
    train_df, temp_df = train_test_split(
        df, 
        test_size=0.30, 
        random_state=42, 
        stratify=df['label']
    )
    val_df, test_df = train_test_split(
        temp_df, 
        test_size=0.50, 
        random_state=42, 
        stratify=temp_df['label']
    )
    
    print(f"Taille du jeu d'entraînement : {len(train_df)}")
    print(f"Taille du jeu de validation : {len(val_df)}")
    print(f"Taille du jeu de test : {len(test_df)}")

    # 3. Charger le modèle et le tokenizer
    # BASE_MODEL_PATH permet de choisir la source :
    # - "xlm-roberta-base" (défaut) : premier entraînement, tête de classification vierge.
    # - un chemin local (ex: "models/classification/") : AFFINE le modèle déjà
    #   entraîné, en conservant ce qu'il a appris, au lieu de repartir de zéro.
    model_name = os.environ.get("BASE_MODEL_PATH", "xlm-roberta-base")
    if model_name != "xlm-roberta-base" and not os.path.exists(model_name):
        print(f"Avertissement : {model_name} introuvable, retour à xlm-roberta-base.")
        model_name = "xlm-roberta-base"

    print(f"Chargement du tokenizer et du modèle depuis : {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(LABEL_MAP)
    )

    # Tokenisation des jeux de données (longueur max fixée à 128 pour le CPU)
    max_length = 128
    print("Tokenisation des textes...")
    train_encodings = tokenizer(list(train_df['cleaned_message']), truncation=True, padding=True, max_length=max_length)
    val_encodings = tokenizer(list(val_df['cleaned_message']), truncation=True, padding=True, max_length=max_length)
    test_encodings = tokenizer(list(test_df['cleaned_message']), truncation=True, padding=True, max_length=max_length)

    # Création des objets Dataset PyTorch
    train_dataset = RequestDataset(train_encodings, list(train_df['label']))
    val_dataset = RequestDataset(val_encodings, list(val_df['label']))
    test_dataset = RequestDataset(test_encodings, list(test_df['label']))

    # 4. Configuration des arguments d'entraînement
    output_dir = "./results"
    num_epochs = int(os.environ.get("NUM_EPOCHS", "15"))
    learning_rate = float(os.environ.get("LEARNING_RATE", "5e-5"))
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        learning_rate=learning_rate,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        warmup_ratio=0.1,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="loss",
        report_to="none",                     # Désactiver le tracking externe (wandb, etc.)
        save_total_limit=2,  # ne garde que les 2 derniers checkpoints (dont le meilleur)
    )

    callbacks = []
    if progress_callback:
        callbacks.append(EpochProgressCallback(progress_callback, num_epochs))

    # Initialisation du Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        callbacks=callbacks,
    )

    # 5. Entraînement du modèle
    print("Début de l'entraînement...")
    trainer.train()
    print("Entraînement terminé !")

    # 6. Évaluation sur le jeu de test
    print("Évaluation sur le jeu de test...")
    predictions = trainer.predict(test_dataset)
    pred_labels = np.argmax(predictions.predictions, axis=1)
    true_labels = list(test_df['label'])

    # Métriques détaillées par classe
    target_names = [INV_LABEL_MAP[i] for i in range(len(LABEL_MAP))]
    report = classification_report(
        true_labels, 
        pred_labels, 
        target_names=target_names, 
        zero_division=0
    )
    print("\n--- Rapport de Classification ---")
    print(report)

    # Matrice de confusion
    print("--- Matrice de Confusion ---")
    cm = confusion_matrix(true_labels, pred_labels)
    print(cm)

    # 7. Sauvegarde du modèle et du tokenizer
    save_path = os.environ.get("CLASSIFIER_SAVE_PATH", "models/classification/")
    os.makedirs(save_path, exist_ok=True)
    print(f"Sauvegarde du modèle et du tokenizer dans {save_path}...")
    model.config.id2label = INV_LABEL_MAP
    model.config.label2id = LABEL_MAP
    model.save_pretrained(save_path)
    tokenizer.save_pretrained(save_path)
    print("Sauvegarde réussie !")

if __name__ == "__main__":
    main()
