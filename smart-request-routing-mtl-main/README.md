# Projet de Traitement de Demandes Citoyennes

Ce projet vise à automatiser le traitement, la modération, la classification et la génération d'argumentaires pour les demandes citoyennes.

## Structure du projet

Voici la description des dossiers créés pour structurer ce projet :

* **[data/](file:///c:/Users/HP%20ELITEBOOK/Desktop/2A_GD/Stage_2A/Repo_projet/data/)** : Contient les fichiers de données d'entrée (par exemple, les fichiers Excel contenant les demandes citoyennes).
* **[models/](file:///c:/Users/HP%20ELITEBOOK/Desktop/2A_GD/Stage_2A/Repo_projet/models/)** : Destiné à stocker les modèles de machine learning et de deep learning entraînés ou téléchargés.
* **src/** : Contient l'ensemble du code source de l'application, divisé en modules thématiques :
  * **[src/preprocessing/](file:///c:/Users/HP%20ELITEBOOK/Desktop/2A_GD/Stage_2A/Repo_projet/src/preprocessing/)** : Scripts de prétraitement, nettoyage et formatage des données brutes.
  * **[src/moderation/](file:///c:/Users/HP%20ELITEBOOK/Desktop/2A_GD/Stage_2A/Repo_projet/src/moderation/)** : Détection de la langue, modération de contenu, filtrage des demandes non-conformes ou injurieuses.
  * **[src/classification/](file:///c:/Users/HP%20ELITEBOOK/Desktop/2A_GD/Stage_2A/Repo_projet/src/classification/)** : Algorithmes de classification automatique des thématiques ou services concernés par les demandes.
  * **[src/argumentaire/](file:///c:/Users/HP%20ELITEBOOK/Desktop/2A_GD/Stage_2A/Repo_projet/src/argumentaire/)** : Génération de réponses types, de synthèses d'arguments ou de suggestions de réponses.
  * **[src/app/](file:///c:/Users/HP%20ELITEBOOK/Desktop/2A_GD/Stage_2A/Repo_projet/src/app/)** : Code de l'application utilisateur (frontend Streamlit, backend d'API FastAPI).
* **[tests/](file:///c:/Users/HP%20ELITEBOOK/Desktop/2A_GD/Stage_2A/Repo_projet/tests/)** : Tests unitaires et d'intégration pour assurer la robustesse du code.

## Installation

Pour installer les dépendances nécessaires au projet, exécutez la commande suivante :

```bash
pip install -r requirements.txt
```

## Lancement des Tests

Pour exécuter toute la suite de tests unitaires (31 tests validant le pipeline complet) :

```bash
python -m unittest discover tests/
```

## Lancement de l'Application Streamlit

Pour démarrer le portail interactif de traitement des demandes citoyennes :

```bash
streamlit run src/app/main.py
```

## Processus de Réentraînement du Classificateur

Pour enrichir le modèle avec de nouvelles corrections et comparer ses performances avant déploiement :

1. Placez le fichier des nouvelles corrections sous `data/historique_corrections.xlsx` (colonnes : `Message`, `Direction_validee`).
2. Lancez le script de réentraînement :
   ```bash
   python src/classification/reentrainement.py
   ```
   Ce script :
   - Fusionne l'historique et le dataset initial.
   - Entraîne un nouveau modèle temporaire.
   - Compare de manière rigoureuse sur un jeu de test identique les performances (F1-score et précision par classe) de l'ancien modèle et du nouveau modèle.
   - Remplace en toute sécurité le modèle en production en conservant un backup en cas d'erreur.

