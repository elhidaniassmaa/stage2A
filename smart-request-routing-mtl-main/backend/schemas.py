from pydantic import BaseModel, EmailStr
from typing import Optional, List

# Authentification
class LoginRequest(BaseModel):
    email: str
    password: str
    role: str

class UserResponse(BaseModel):
    id: int
    email: str
    nom_complet: str
    direction: str
    role: str
    demandes_traitees: int
    derniere_connexion: Optional[str] = None
    statut: str

    class Config:
        from_attributes = True

# Utilisateur CRUD
class UserCreate(BaseModel):
    email: str
    nom_complet: str
    direction: str
    role: str
    statut: Optional[str] = "ACTIF"

class UserUpdate(BaseModel):
    nom_complet: str
    direction: str
    role: str
    statut: str

# Base réglementaire (Articles)
class ArticleResponse(BaseModel):
    id: int
    numero_article: str
    texte_extrait: str
    decret_source: str
    date_version: str
    code_direction: str
    rag_sync: Optional[bool] = None

    class Config:
        from_attributes = True

class ArticleCreateUpdate(BaseModel):
    numero_article: str
    texte_extrait: str
    decret_source: str
    date_version: str
    code_direction: str

# Mots interdits
class ForbiddenWordResponse(BaseModel):
    id: int
    mot: str
    langue: str
    categorie: str

    class Config:
        from_attributes = True

class ForbiddenWordCreate(BaseModel):
    mot: str
    langue: str
    categorie: str

# Journal d'activité (Logs)
class LogResponse(BaseModel):
    id: int
    date_heure: str
    utilisateur: str
    role: str
    action: str
    element_concerne: str
    detail: str

    class Config:
        from_attributes = True

# Demandes
class DemandeResponse(BaseModel):
    id: int
    nom: Optional[str] = None
    prenom: Optional[str] = None
    message_original: str
    message_nettoye: str
    date_depot: str
    date_echeance: str
    type_alerte: str
    contenu_valide: int
    mot_interdit_detecte: int
    direction_predite: str
    score_confiance: float
    confiance_faible: int
    argumentaire: str
    decision_responsable: str
    statut_demande: str
    region: Optional[str] = None

    class Config:
        from_attributes = True

class DemandeDecisionUpdate(BaseModel):
    decision_responsable: str

class DemandeStatutUpdate(BaseModel):
    statut_demande: str

# Rapport KPIs
class DashboardStats(BaseModel):
    total_demandes: int
    demandes_traitees: int
    en_attente: int
    urgent_depasse: int
