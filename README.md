<div align="center">

# 🇲🇦 GEDEC — Gestion Électronique des Demandes Citoyennes
### Plateforme IA multilingue de routage, modération et traitement des demandes citoyennes


**GEDEC** est un projet de fin d'études (PFA) réalisé dans le cadre du cursus d'ingénieur à l'**ENSIAS**, en partenariat avec le Ministère du Transport et de la Logistique (MTL) du Royaume du Maroc. Le système automatise l'analyse, la modération, le routage réglementaire et le suivi des délais légaux des demandes citoyennes adressées au Ministère.

</div>

## Table des matières

- [Le problème résolu](#-le-problème-résolu)
- [Fonctionnalités](#-fonctionnalités)
- [Résultats & métriques](#-résultats--métriques)
- [Architecture technique](#️-architecture-technique)
- [Structure du projet](#-structure-du-projet)
- [Installation](#-installation)
- [Comptes de démonstration](#-comptes-de-démonstration)
- [Tests](#-tests)
- [Limites connues](#-limites-connues--transparence-assumée)
- [Historique des décisions techniques notables](#-historique-des-décisions-techniques-notables)
- [Licence](#-licence)
- [Contact](#-contact)

---

##  Le problème résolu

Le traitement manuel des demandes citoyennes adressées au Ministère souffre de trois difficultés récurrentes, que ce projet adresse :

1. **Routage lent et sujet à l'erreur humaine** — identifier la bonne direction ministérielle compétente (parmi 7 directions : DTR, DSPCT, DAAJJ, DMM, DJAC, DSI, Cabinet du Ministère) parmi des messages rédigés en français, arabe standard ou darija (latin ou arabe).
2. **Suivi des délais légaux** — le décret n° 2.17.265 impose un délai de traitement de 60 jours, avec un risque de dépassement silencieux si rien ne relance activement les Responsables.
3. **Absence de justification réglementaire systématique** — chaque orientation de dossier devrait pouvoir être justifiée par un texte de loi précis, ce qui est chronophage à faire manuellement pour chaque dossier.

Le système propose une **IA qui assiste, sans jamais décider seule** : chaque prédiction (direction, argumentaire légal) est soumise à validation humaine par un Responsable, qui peut la valider ou la corriger.

---

## Fonctionnalités

###  Classification automatique multilingue
Modèle **XLM-RoBERTa** fine-tuné, prédisant la direction compétente parmi 7 sigles officiels + "Non concerné", avec détection d'incertitude (repli automatique sur un classificateur par mots-clés si le score de confiance est faible ou si le modèle est indisponible).

###  Modération lexicale & Filtrage de Contenu
Filtrage des contenus contre un dictionnaire de mots interdits (français, arabe standard, darija), administrable depuis l'interface (ajout/suppression par langue et catégorie).

###  Génération d'argumentaire réglementaire (RAG)
Justification automatique de la compétence d'une direction, citant précisément le décret n° 2.21.968, via une recherche sémantique par embeddings avec un **système de confiance à 3 paliers** calibré empiriquement.

###  Gestion des délais légaux (SLA)
Calcul automatique de l'échéance à 60 jours, avec double seuil d'alerte (rappel à J-15, prioritaire à J-5)

Envoi automatique de notifications et rappels d'alerte par email (SMTP) pour les dossiers prioritaires ou en souffrance.

###  Réentraînement incrémental supervisé
Un Administrateur peut déclencher un fine-tuning du modèle de classification à partir des corrections réellement faites par les Responsables, avec suivi de progression en temps réel et **garde-fou automatique** empêchant le déploiement d'un modèle moins performant que celui en production.

###  Déduplication à l'import
Détection des demandes en double (même citoyen, même message) lors d'un import Excel massif, par empreinte textuelle normalisée.

###  Rapports d'activité
Bilans chiffrés (répartition par direction/région, taux de respect des délais, fiabilité de la classification IA), avec historique des rapports générés et export PDF/CSV.

---

##  Résultats & métriques

### Classification (XLM-RoBERTa)
| Modèle testé | Exactitude | F1-macro |
|---|---|---|
| CAMeLBERT-DA (arabe seul, écarté) | 40% | 0.37 |
| **XLM-RoBERTa (retenu)** | **94%** | **0.93** |

Testé sur un jeu de 63 exemples réels, multilingue (français, arabe standard, darija latine et arabe).

### Génération d'argumentaire (RAG) — système à 3 paliers
Calibré empiriquement sur **357 messages réels** du dataset, en analysant la distribution des scores de similarité sémantique obtenus (percentiles : médiane 0.42, 90ᵉ centile 0.63) :

| Score de similarité | Comportement | Fréquence observée |
|---|---|---|
| < 0.45 | Citation de l'article complet (prudence) | ~55% des cas |
| 0.45 – 0.75 | Citation des 3 tirets les plus pertinents | ~40% des cas |
| ≥ 0.75 | Citation d'un tiret unique précis | ~5% des cas |

Ce système corrige un biais identifié en cours de développement : sur certains cas (ex. enquête sur un accident aérien), le tiret le plus proche par score absolu s'est avéré être un mauvais candidat malgré un score élevé — d'où l'introduction d'un mécanisme de prudence graduée plutôt qu'un simple seuil binaire.


---

##  Architecture technique

> Cette section documente la stack **réellement utilisée**, vérifiée dans le code — pas une liste de technologies aspirationnelle.

### Backend
- **Python 3.11+, FastAPI, Uvicorn**
- **Base de données : SQLite via `sqlite3` natif** (requêtes SQL brutes — **aucun ORM**, pas de SQLAlchemy)
- **Authentification : comparaison directe email/mot de passe/rôle en base** — **aucun système de token (pas de JWT, pas de session serveur)** ; le frontend conserve l'utilisateur connecté dans le `localStorage` du navigateur
- **IA/NLP** : HuggingFace Transformers, PyTorch, Scikit-learn, Sentence-Transformers, Langdetect
- **Notifications** : `smtplib` (SMTP direct, testé avec Gmail via mot de passe d'application)

### Frontend
- **React 18 + Vite**
- CSS custom (pas de framework type Tailwind en production)
- Notifications desktop via l'API `Notification` du navigateur, son via Web Audio API (synthèse, sans dépendance à un fichier audio externe)

### Modèles IA
- **Classification** : `xlm-roberta-base` fine-tuné (voir `models/classification/`)
- **Argumentaire (RAG)** : `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` pour les embeddings, génération de texte via LLM local (Ollama/Mistral) avec repli sur un template si indisponible

---

##  Structure du projet

```text
gedec/
├── backend/                     # API FastAPI
│   ├── database.py               # Schéma SQLite + seed initial
│   ├── main.py                   # Endpoints REST principaux
│   ├── notifications.py          # Envoi d'alertes email SMTP
│   ├── reentrainement_routes.py  # Déclenchement du fine-tuning IA
│   ├── deduplication.py          # Empreintes textuelles anti-doublon
│   ├── sync_base_reglementaire.py# Synchro base réglementaire ↔ RAG
│   └── sync_mots_interdits.py
│
├── src/                          # Cœur algorithmique (NLP & métier)
│   ├── preprocessing/            # Nettoyage de texte, détection de langue
│   ├── moderation/                # Filtrage lexical
│   ├── classification/           # Prédiction + réentraînement XLM-RoBERTa
│   ├── argumentaire/              # Moteur RAG (embeddings + génération)
│   └── app/                      # Échéances SLA, rapports
│
├── frontend/                     # Application React + Vite
│   └── src/components/           # Dashboard, ListeDemandes, BaseReglementaire, etc.
│
├── data/                         # Datasets (entraînement, corrections)
├── config/                       # Lexique des mots interdits
├── models/classification/        # Modèle XLM-RoBERTa fine-tuné actif
├── scripts/                      # Migrations, utilitaires d'administration
└── tests/                        # unit/, api/, manual/
```

---
## Configuration & Variables d'Environnement

Le projet utilise des variables d'environnement pour configurer les accès et le serveur. 

1. Copiez le fichier `.env.example` vers `.env` :
   ```bash
   cp .env.example .env
   ```
2. Éditez le fichier `.env` selon vos besoins :
   ```env
   HOST=0.0.0.0
   PORT=8000
   DATABASE_URL=sqlite:///backend/gedec.db
   SECRET_KEY=votre_cle_secrete_jwt
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=votre_email@domaine.gov.ma
   SMTP_PASSWORD=votre_mot_de_passe_application
   VITE_API_URL=http://localhost:8000
   ```

---

##  Installation

### Prérequis
- **Python** 3.11 ou supérieur
- **Node.js** v18 ou supérieur & **npm**
- **Git**

### 3. Backend

 **Important** : toutes les commandes Python doivent être lancées depuis la **racine du projet**, jamais depuis l'intérieur de `backend/` (sinon `ModuleNotFoundError: No module named 'src'`).

1. **Cloner le projet** :
   ```bash
   git clone https://github.com/votre-organisation/smart-request-routing-mtl.git
   cd smart-request-routing-mtl
   ```

2. **Créer et activer un environnement virtuel Python** :
   ```bash
   # Sur Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate

   # Sur Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Installer les dépendances Python** :
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Initialiser la base de données** (Optionnel, exécuté automatiquement au démarrage) :
   ```bash
   python backend/database.py
   ```

5. **Lancer le serveur FastAPI** :
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```
   L'API sera accessible sur `http://localhost:8000` et la documentation interactive OpenAPI Swagger sur `http://localhost:8000/docs`.

---

### 4. Frontend 

1. **Naviguer dans le dossier frontend** :
   ```bash
   cd frontend
   ```

2. **Installer les dépendances Node.js** :
   ```bash
   npm install
   ```

3. **Lancer le serveur de développement Vite** :
   ```bash
   npm run dev
   ```
   L'interface web sera accessible sur `http://localhost:5173`.



---

##  Comptes de démonstration

La base est initialisée avec des comptes de test (voir `backend/database.py` pour la liste exacte). Exemple :

| Rôle | Email (exemple) | Mot de passe |
|---|---|---|
| Administrateur | `admin@example.com` | `password123` |
| Responsable (DTR) | `responsable.dtr@example.com` | `password123` |

 Mots de passe volontairement simples car **non hachés** dans ce prototype (ne jamais réutiliser ce schéma d'authentification tel quel dans un contexte réel).

---

##  Tests


### Exécuter la suite de tests unitaires (Core NLP & Logic)
```bash
python -m unittest discover -s tests/unit
```

### Exécuter les tests des endpoints API Backend
```bash
python -m unittest discover -s tests/api
```

Certains tests unitaires nécessitent les dépendances lourdes (PyTorch, Transformers) installées.

---
