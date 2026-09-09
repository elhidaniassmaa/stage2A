# Guide de Contribution - Smart Request Routing MTL

Merci de votre intérêt pour la contribution au projet **Smart Request Routing MTL** (GEDEC). Ce document fournit les directives à suivre pour proposer des améliorations, signaler des bugs ou soumettre du code.

---

## 📋 Table des Matières

1. [Code de Conduite](#-code-de-conduite)
2. [Comment Contribuer ?](#-comment-contribuer-)
   - [Signaler un Bug](#signaler-un-bug)
   - [Proposer une Fonctionnalité](#proposer-une-fonctionnalité)
   - [Soumettre une Pull Request](#soumettre-une-pull-request)
3. [Normes de Développement](#-normes-de-développement)
   - [Backend (Python / FastAPI)](#backend-python--fastapi)
   - [Frontend (React / Vite)](#frontend-react--vite)
4. [Exécution des Tests](#-exécution-des-tests)
5. [Conventions de Commit](#-conventions-de-commit)

---

## 🤝 Code de Conduite

Veuillez adopter une attitude professionnelle, respectueuse et constructive envers tous les contributeurs et utilisateurs du projet.

---

## 🛠️ Comment Contribuer ?

### Signaler un Bug

Avant d'ouvrir une issue, assurez-vous que le bug n'a pas déjà été signalé. En créant l'issue, précisez :
- Votre environnement (OS, version de Python/Node.js).
- Les étapes précises pour reproduire le comportement inattendu.
- Les logs d'erreur ou captures d'écran associés.

### Proposer une Fonctionnalité

Toute nouvelle idée est la bienvenue. Ouvrez une issue de type **Feature Request** en détaillant le besoin métier, le cas d'usage ainsi que la solution technique envisagée.

### Soumettre une Pull Request

1. **Forkez** le dépôt et créez une branche de fonctionnalité à partir de `main` :
   ```bash
   git checkout -b feature/nom-de-la-fonctionnalite
   ```
2. **Développez** vos modifications en respectant les normes de code.
3. **Exécutez les tests** pour vérifier l'absence de régression.
4. **Committez** vos changements en suivant la convention de commit.
5. **Poussez** votre branche et ouvrez une **Pull Request** vers `main`.

---

## 📏 Normes de Développement

### Backend (Python / FastAPI)

- Formatage du code conforme à **PEP 8**.
- Utilisation de typages stricts avec `Pydantic` et l'annotation de type Python (`typing`).
- Les requêtes et endpoints API doivent gérer correctement les exceptions HTTP (`HTTPException`).

### Frontend (React / Vite)

- Découpage en composants réutilisables et fonctionnels (Hooks React).
- Respect des règles ESLint / Prettier configurées dans le projet.
- Pas de clés d'API ni de mots de passe codés en dur dans le code source.

---

## 🧪 Exécution des Tests

Avant toute soumission de code, validez la suite de tests unitaires et d'intégration :

```bash
# Tests unitaires Backend & IA
python -m unittest discover -s tests/unit

# Tests des endpoints API
python -m unittest discover -s tests/api
```

---

## 📝 Conventions de Commit

Nous recommandons la convention **Conventional Commits** :

- `feat:` Nouvelle fonctionnalité (ex: `feat: ajout de la déduplication floue`).
- `fix:` Correction de bug (ex: `fix: résolution du problème d'encodage des caractères arabes`).
- `docs:` Modification de la documentation (ex: `docs: mise à jour du README`).
- `refactor:` Restructuration du code sans changement de comportement.
- `test:` Ajout ou mise à jour des tests unitaires.
- `chore:` Tâches de maintenance (ex: mise à jour des dépendances).
