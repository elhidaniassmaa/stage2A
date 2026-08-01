import os
import sys
import io
import csv
import sqlite3
import asyncio
import json
from dotenv import load_dotenv
load_dotenv()
from backend.notifications import envoyer_email_alerte
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
import pandas as pd
from typing import Optional, List

# Ajouter le dossier src au chemin de recherche pour importer les modules existants
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from backend.database import get_db_connection, init_db
from backend.deduplication import compute_demande_fingerprint, load_existing_fingerprints
from backend.sync_base_reglementaire import (
    ajouter_article_rag, modifier_article_rag, supprimer_article_rag, rattacher_articles_heritage
)
from backend.sync_mots_interdits import synchroniser_mots_interdits
from backend.schemas import (
    LoginRequest, UserResponse, UserCreate, UserUpdate,
    ArticleResponse, ArticleCreateUpdate, ForbiddenWordResponse, ForbiddenWordCreate,
    LogResponse, DemandeResponse, DemandeDecisionUpdate, DemandeStatutUpdate, DashboardStats
)

app = FastAPI(title="GEDEC API", description="API de Gestion des Demandes Citoyennes")

# Configurer CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialiser la base de données au démarrage
@app.on_event("startup")
async def startup_event():
    init_db()
    try:
        resultat = rattacher_articles_heritage()
        if resultat["rattaches"] > 0:
            print(f"[SYNC RAG] {resultat['rattaches']} article(s) hérité(s) rattaché(s) au JSON.")
    except Exception as e:
        print(f"[SYNC RAG] Echec du rattachement rétroactif : {e}")
    try:
        sync_mots = synchroniser_mots_interdits()
        if sync_mots.get("sync_ok"):
            print(f"[SYNC MOTS] {sync_mots['mots_exportes']} mot(s) interdit(s) synchronisé(s) vers le fichier de modération.")
    except Exception as e:
        print(f"[SYNC MOTS] Echec de la synchronisation des mots interdits : {e}")
    asyncio.create_task(boucle_verification_alertes())
# --- HELPER FUNCTIONS ---

def add_system_log(user: str, role: str, action: str, element: str, detail: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    cursor.execute("""
    INSERT INTO logs (date_heure, utilisateur, role, action, element_concerne, detail)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (now_str, user, role, action, element, detail))
    conn.commit()
    conn.close()

def api_predire_direction(text: str) -> dict:
    """
    Tente d'utiliser le classificateur IA existant. En cas d'erreur ou d'absence
    de modèle, utilise un classificateur de secours par mots-clés.
    """
    try:
        from classification.predict import predire_direction
        resultat = predire_direction(text)
        print(f"[IA] ✅ Modèle XLM-RoBERTa utilisé -> {resultat}")
        return resultat
    except Exception as e:
        print(f"[IA] ❌ ECHEC du modèle réel, repli mots-clés -> Erreur : {e}")
        text_lower = text.lower()
        # Règles simples de classification de repli par mots-clés
        if any(w in text_lower for w in ["sertificat", "licence", "permis", "camion", "routier", "marchandise", "règlement", "conduite", "transport", "رخصة", "سياقة", "شاحنة", "طريق", "نقل", "routiere"]):
            dir_pred = "DTR"
        elif any(w in text_lower for w in ["port", "logistique", "plateforme", "coordination", "لوجستيك", "ميناء", "maroc logistique"]):
            dir_pred = "DSPCT"
        elif any(w in text_lower for w in ["avion", "aérien", "vol", "aviation", "طيران", "جوي", "مطار", "matar"]):
            dir_pred = "DJAC"
        elif any(w in text_lower for w in ["bateau", "navire", "maritime", "mer", "marins", "بحر", "سفينة", "بحرية"]):
            dir_pred = "DMM"
        elif any(w in text_lower for w in ["site", "informatique", "système", "serveur", "réseau", "numérique", "حاسوب", "رقمي", "موقع", "dsi"]):
            dir_pred = "DSI"
        elif any(w in text_lower for w in ["plainte", "insulte", "loi", "juridique", "ressources", "contrat", "قانون", "قضائية", "منازعات", "responsables"]):
            dir_pred = "DAAJJ"
        else:
            dir_pred = "Cabinet du Ministère"
            
        return {
            "direction_predite": dir_pred,
            "score_confiance": 0.85,
            "indicateur_confiance_faible": False
        }

def api_generer_argumentaire(direction: str, text: str) -> str:
    try:
        from argumentaire.generer_argumentaire import generer_argumentaire
        return generer_argumentaire(direction, text)
    except Exception:
        # Fallback argumentaire si le module échoue
        return f"En vertu du décret régissant les attributions du Ministère du Transport et de la Logistique, la direction '{direction}' est compétente pour instruire et traiter les demandes citoyennes relatives à ce domaine d'activité."

def detecter_mot_interdit(text: str) -> bool:
    """
    Vérifie si le texte contient au moins un mot de la liste admin (SQLite),
    via le même moteur que verifier_contenu (mots-clés multilingues).
    """
    try:
        from moderation.moderation import check_mots_cles
        return not check_mots_cles(text)["contenu_valide"]
    except Exception:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT mot FROM mots_interdits")
        mots = [row['mot'] for row in cursor.fetchall()]
        conn.close()
        text_lower = text.lower()
        return any(mot.lower() in text_lower for mot in mots if mot.strip())
def verifier_et_traiter_alertes():
    from app.echeance import verifier_alerte
    from datetime import datetime, timedelta

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, date_depot, direction_predite, decision_responsable,
               notif_rappel_envoyee, notif_prioritaire_envoyee
        FROM demandes
        WHERE statut_demande = 'En attente'
    """)
    demandes = cursor.fetchall()

    for d in demandes:
        date_depot = datetime.strptime(d["date_depot"], "%Y-%m-%d %H:%M:%S")
        alerte = verifier_alerte(date_depot)
        type_alerte = alerte["type_alerte"]

        cursor.execute("UPDATE demandes SET type_alerte = ? WHERE id = ?", (type_alerte, d["id"]))

        direction_finale = d["decision_responsable"]
        if direction_finale == "Validé":
            direction_finale = d["direction_predite"]
        else:
            direction_finale = direction_finale.replace("Corriger : ", "").strip()

        if type_alerte == "prioritaire" and not d["notif_prioritaire_envoyee"]:
            cursor.execute(
                "SELECT email FROM users WHERE direction = ? AND role = 'Responsable' AND statut = 'ACTIF'",
                (direction_finale,)
            )
            responsables = cursor.fetchall()
            jours_restants = (date_depot.date() + timedelta(days=60) - datetime.now().date()).days

            if responsables:
                tous_envoyes_avec_succes = True
                for resp in responsables:
                    succes = envoyer_email_alerte(resp["email"], f"GEDEC-2026-{d['id']:03d}", direction_finale, jours_restants)
                    if not succes:
                        tous_envoyes_avec_succes = False
                if tous_envoyes_avec_succes:
                    cursor.execute("UPDATE demandes SET notif_prioritaire_envoyee = 1 WHERE id = ?", (d["id"],))
                else:
                    print(f"[ALERTES] Demande {d['id']} : échec d'envoi, flag laissé à 0 pour retenter.")
            else:
                print(f"[ALERTES] Demande {d['id']} : aucun Responsable ACTIF pour '{direction_finale}'.")

        elif type_alerte == "rappel" and not d["notif_rappel_envoyee"]:
            cursor.execute("UPDATE demandes SET notif_rappel_envoyee = 1 WHERE id = ?", (d["id"],))

    conn.commit()
    conn.close()


async def boucle_verification_alertes():
    """
    Tâche de fond qui vérifie les alertes toutes les heures.
    Limite connue : cette approche par boucle asyncio en mémoire convient à un
    prototype mono-processus ; en production avec plusieurs workers, il
    faudrait un vrai planificateur externe (ex. Celery + Redis, ou cron).
    """
    while True:
        try:
            verifier_et_traiter_alertes()
        except Exception as e:
            print(f"[ALERTES] Erreur lors de la vérification : {e}")
        await asyncio.sleep(3600)  # toutes les heures

@app.post("/api/debug/verifier-alertes-maintenant")
def debug_verifier_alertes():
    verifier_et_traiter_alertes()
    return {"message": "Vérification des alertes exécutée manuellement."}

# --- AUTHENTIFICATION ---

@app.post("/api/auth/login")
def login(req: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM users WHERE email = ? AND password_hash = ? AND role = ?
    """, (req.email, req.password, req.role))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        raise HTTPException(status_code=401, detail="Identifiants ou rôle incorrects.")
        
    if user['statut'] == 'INACTIF':
        conn.close()
        raise HTTPException(status_code=403, detail="Ce compte est inactif. Contactez l'administrateur.")
        
    # Mettre à jour la date de dernière connexion
    now_str = datetime.now().strftime("Aujourd'hui, %H:%M")
    cursor.execute("UPDATE users SET derniere_connexion = ? WHERE id = ?", (now_str, user['id']))
    conn.commit()
    
    user_dict = dict(user)
    user_dict['derniere_connexion'] = now_str
    conn.close()
    
    # Logger
    add_system_log(user_dict['nom_complet'], user_dict['role'], "Connexion", "Système", "Utilisateur connecté avec succès.")
    
    return user_dict

@app.post("/api/auth/logout")
def logout(user_name: str = Query(...), user_role: str = Query(...)):
    add_system_log(user_name, user_role, "Déconnexion", "Système", "Utilisateur déconnecté.")
    return {"message": "Déconnecté avec succès"}

# --- TABLEAU DE BORD (STATS & DEMANDES) ---
@app.get("/api/notifications")
def get_notifications():
    """
    Retourne les demandes en attente ayant une alerte active (rappel ou
    prioritaire), pour affichage dans la cloche de notification.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, direction_predite, decision_responsable, type_alerte, date_echeance
        FROM demandes
        WHERE statut_demande = 'En attente' AND type_alerte IN ('rappel', 'prioritaire', 'depasse')
        ORDER BY date_echeance ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    notifications = []
    for r in rows:
        direction = r["decision_responsable"]
        if direction == "Validé":
            direction = r["direction_predite"]
        else:
            direction = direction.replace("Corriger : ", "").strip()

        notifications.append({
            "id": r["id"],
            "numero": f"GEDEC-2026-{r['id']:03d}",
            "direction": direction,
            "type_alerte": r["type_alerte"],
            "date_echeance": r["date_echeance"],
        })

    return {"notifications": notifications, "total": len(notifications)}

@app.get("/api/dashboard/stats", response_model=DashboardStats)
def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM demandes")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM demandes WHERE statut_demande = 'Répondue'")
    traitees = cursor.fetchone()[0]
    
    en_attente = total - traitees
    
    cursor.execute("SELECT COUNT(*) FROM demandes WHERE type_alerte IN ('prioritaire', 'depasse')")
    urgent_depasse = cursor.fetchone()[0]
    
    conn.close()
    return {
        "total_demandes": total,
        "demandes_traitees": traitees,
        "en_attente": en_attente,
        "urgent_depasse": urgent_depasse
    }

@app.get("/api/demandes")
def get_demandes(
    statut: Optional[str] = None,
    region: Optional[str] = None,
    urgent: Optional[bool] = None,
    q: Optional[str] = None
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM demandes WHERE 1=1"
    params = []
    
    if statut and statut != "Toutes":
        query += " AND statut_demande = ?"
        params.append(statut)
        
    if region:
        query += " AND region = ?"
        params.append(region)
        
    if urgent:
        query += " AND type_alerte IN ('prioritaire', 'depasse')"
        
    if q:
        query += " AND (message_original LIKE ? OR direction_predite LIKE ? OR decision_responsable LIKE ?)"
        search_param = f"%{q}%"
        params.extend([search_param, search_param, search_param])
        
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    demandes = [dict(row) for row in rows]
    conn.close()
    return demandes

@app.post("/api/demandes/upload")
def upload_demandes(file: UploadFile = File(...), user_name: str = Query(...), user_role: str = Query(...)):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Seuls les fichiers Excel (.xlsx) sont supportés.")
        
    try:
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # Trouver les colonnes Message, Date de dépôt, Nom, Prénom
        msg_col = None
        date_col = None
        nom_col = None
        prenom_col = None
        for col in df.columns:
            col_lower = str(col).lower()
            if 'message' in col_lower and msg_col is None:
                msg_col = col
            elif ('depot' in col_lower or 'dépôt' in col_lower) and date_col is None:
                date_col = col
            elif ('prénom' in col_lower or 'prenom' in col_lower) and prenom_col is None:
                prenom_col = col
            elif 'nom' in col_lower and nom_col is None:
                nom_col = col

        # Repli : si aucune colonne "dépôt" explicite trouvée, prendre la première contenant "date"
        if date_col is None:
            for col in df.columns:
                if 'date' in str(col).lower():
                    date_col = col
                    break

        if msg_col is None:
            msg_col = df.columns[0]
        conn = get_db_connection()
        cursor = conn.cursor()
        existing_fingerprints = load_existing_fingerprints(cursor)
        batch_fingerprints: set[str] = set()

        importees = 0
        doublons_ignores = 0
        lignes_vides = 0

        for idx, row in df.iterrows():
            raw_msg = str(row[msg_col]) if not pd.isna(row[msg_col]) else ""
            nom_val = str(row[nom_col]).strip() if nom_col and not pd.isna(row[nom_col]) else "Non renseigné"
            prenom_val = str(row[prenom_col]).strip() if prenom_col and not pd.isna(row[prenom_col]) else ""
            if not raw_msg.strip():
                lignes_vides += 1
                continue
                
            date_val = row[date_col] if date_col and not pd.isna(row[date_col]) else None
            
            # Prétraitement de date
            if date_val:
                try:
                    date_depot = pd.to_datetime(date_val)
                    if isinstance(date_depot, pd.Timestamp):
                        date_depot = date_depot.to_pydatetime()
                except Exception:
                    date_depot = datetime.now()
            else:
                date_depot = datetime.now()
                
            # 1. clean_text
            try:
                from preprocessing.clean_text import clean_text
                cleaned_msg = clean_text(raw_msg)["texte_nettoye"]
            except Exception:
                cleaned_msg = raw_msg

            fingerprint = compute_demande_fingerprint(nom_val, prenom_val, cleaned_msg)
            if fingerprint in existing_fingerprints or fingerprint in batch_fingerprints:
                doublons_ignores += 1
                continue

            # 2. Moderation
            try:
                from moderation.moderation import verifier_contenu
                mod_res = verifier_contenu(cleaned_msg)
                contenu_valide = 1 if mod_res["contenu_valide"] else 0
            except Exception:
                contenu_valide = 1

            # 2b. Détection de mots interdits (indépendante de la modération IA)
            try:
                mot_interdit = 1 if detecter_mot_interdit(cleaned_msg) else 0
            except Exception:
                mot_interdit = 0   
    
            # 3. Classification
            pred_res = api_predire_direction(cleaned_msg)
            dir_predite = pred_res["direction_predite"]
            score_confiance = pred_res["score_confiance"]
            confiance_faible = 1 if pred_res["indicateur_confiance_faible"] else 0
            
            # 4. Argumentaire
            arg_text = api_generer_argumentaire(dir_predite, cleaned_msg)
            
            # 5. Echeance
            try:
                from app.echeance import calculer_echeance, verifier_alerte
                date_echeance = calculer_echeance(date_depot)
                alerte_res = verifier_alerte(date_depot)
                type_alerte = alerte_res["type_alerte"]
            except Exception:
                date_echeance = date_depot + pd.to_timedelta(60, unit='D')
                type_alerte = "aucune"
                
            # Region (extraction ou défaut)
            region_val = "Rabat-Salé-Kénitra"
            for c in df.columns:
                if "region" in str(c).lower() or "région" in str(c).lower():
                    region_val = str(row[c]) if not pd.isna(row[c]) else "Rabat-Salé-Kénitra"
                    break
            cursor.execute("""
            INSERT INTO demandes (
                nom, prenom, message_original, message_nettoye, date_depot, date_echeance, type_alerte,
                contenu_valide, mot_interdit_detecte, direction_predite, score_confiance, confiance_faible,
                argumentaire, decision_responsable, statut_demande, region
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                nom_val, prenom_val, raw_msg, cleaned_msg,
                date_depot.strftime("%Y-%m-%d %H:%M:%S"),
                date_echeance.strftime("%Y-%m-%d %H:%M:%S"),
                type_alerte, contenu_valide, mot_interdit, dir_predite, score_confiance,
                confiance_faible, arg_text, "Validé", "En attente", region_val
            ))
            batch_fingerprints.add(fingerprint)
            existing_fingerprints.add(fingerprint)
            importees += 1

        conn.commit()
        conn.close()

        total_lignes = len(df)
        if importees == 0 and doublons_ignores > 0:
            message = (
                f"Aucune nouvelle demande importée : {doublons_ignores} doublon(s) détecté(s) "
                f"et ignoré(s) sur {total_lignes} ligne(s)."
            )
        elif doublons_ignores > 0:
            message = (
                f"{importees} demande(s) importée(s) avec succès. "
                f"{doublons_ignores} doublon(s) ignoré(s) (même nom, prénom et message déjà en base)."
            )
        else:
            message = f"{importees} demande(s) importée(s) avec succès."

        add_system_log(
            user_name, user_role, "Importation massive",
            f"Fichier: {file.filename}",
            f"{importees} importée(s), {doublons_ignores} doublon(s) ignoré(s), {lignes_vides} ligne(s) vide(s)."
        )

        return {
            "message": message,
            "importees": importees,
            "doublons_ignores": doublons_ignores,
            "lignes_vides": lignes_vides,
            "total_lignes": total_lignes,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'import : {str(e)}")

@app.put("/api/demandes/{id}/decision")
def update_decision(
    id: int, 
    body: DemandeDecisionUpdate, 
    user_name: str = Query(...), 
    user_role: str = Query(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM demandes WHERE id = ?", (id,))
    demande = cursor.fetchone()
    
    if not demande:
        conn.close()
        raise HTTPException(status_code=404, detail="Demande non trouvée.")
        
    decision = body.decision_responsable
    
    # Si la décision est "Validé", on garde la direction prédite
    # Sinon, on prend la direction corrigée
    nouvelle_dir = demande['direction_predite']
    if decision != "Validé":
        nouvelle_dir = decision.replace("Corriger : ", "").strip()
        
    # Régénérer l'argumentaire légal pour la nouvelle direction
    nouvel_arg = api_generer_argumentaire(nouvelle_dir, demande['message_nettoye'])
    
    cursor.execute("""
    UPDATE demandes 
    SET decision_responsable = ?, argumentaire = ?
    WHERE id = ?
    """, (decision, nouvel_arg, id))
    conn.commit()
    conn.close()
    
    # Ajouter au log d'activité
    log_detail = f"{demande['direction_predite']} -> {nouvelle_dir}" if decision != "Validé" else "Validation direction proposée"
    add_system_log(
        user_name, user_role, "Correction direction" if decision != "Validé" else "Validation Demande",
        f"Demande #GEDEC-2026-{id:03d}", log_detail
    )
    
    return {"message": "Décision mise à jour avec succès"}

@app.put("/api/demandes/{id}/statut")
def update_statut(
    id: int, 
    body: DemandeStatutUpdate, 
    user_name: str = Query(...), 
    user_role: str = Query(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM demandes WHERE id = ?", (id,))
    demande = cursor.fetchone()
    
    if not demande:
        conn.close()
        raise HTTPException(status_code=404, detail="Demande non trouvée.")

    # Écrire la date de réponse UNIQUEMENT au moment où la demande passe à "Répondue"
    if body.statut_demande == "Répondue" and demande["statut_demande"] != "Répondue":
        date_reponse_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "UPDATE demandes SET statut_demande = ?, date_reponse = ? WHERE id = ?",
            (body.statut_demande, date_reponse_str, id)
        )
    else:
        cursor.execute("UPDATE demandes SET statut_demande = ? WHERE id = ?", (body.statut_demande, id))

    conn.commit()
    
    cursor.execute("UPDATE users SET demandes_traitees = demandes_traitees + 1 WHERE nom_complet = ?", (user_name,))
    conn.commit()
    
    conn.close()
    
    add_system_log(
        user_name, user_role, "Statut mis à jour", 
        f"Demande #GEDEC-2026-{id:03d}", f"Marquée comme {body.statut_demande}."
    )
    return {"message": "Statut mis à jour avec succès"}

@app.get("/api/demandes/export")
def export_demandes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM demandes ORDER BY id DESC")
    rows = cursor.fetchall()
    
    df_rows = []
    for r in rows:
        d = dict(r)
        # Déterminer la direction finale
        decision = d['decision_responsable']
        direction_finale = d['direction_predite']
        if decision != "Validé":
            direction_finale = decision.replace("Corriger : ", "").strip()
            
        df_rows.append({
            "Numéro Demande": f"GEDEC-2026-{d['id']:03d}",
            "Message Citoyen": d['message_original'],
            "Date de Dépôt": d['date_depot'],
            "Date d'Échéance": d['date_echeance'],
            "Contenu Conforme": "Oui" if d['contenu_valide'] == 1 else "Non (Signalé)",
            "Direction Proposée": d['direction_predite'],
            "Score Confiance IA": f"{d['score_confiance']:.2%}",
            "Décision Responsable": decision,
            "Direction Finale": direction_finale,
            "Argumentaire Législatif": d['argumentaire'],
            "Statut": d['statut_demande'],
            "Région": d['region']
        })
        
    conn.close()
    
    df = pd.DataFrame(df_rows)
    
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Suivi Demandes')
    excel_data = excel_buffer.getvalue()
    
    headers = {
        'Content-Disposition': f'attachment; filename="suivi_demandes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    }
    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )

# --- BASE RÉGLEMENTAIRE ---

@app.get("/api/base-reglementaire", response_model=List[ArticleResponse])
def get_articles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM articles ORDER BY id DESC")
    rows = cursor.fetchall()
    articles = [dict(row) for row in rows]
    conn.close()
    return articles

@app.post("/api/base-reglementaire", response_model=ArticleResponse)
def create_article(
    body: ArticleCreateUpdate, 
    user_name: str = Query(...), 
    user_role: str = Query(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO articles (numero_article, texte_extrait, decret_source, date_version, code_direction)
    VALUES (?, ?, ?, ?, ?)
    """, (body.numero_article, body.texte_extrait, body.decret_source, body.date_version, body.code_direction))
    conn.commit()
    new_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM articles WHERE id = ?", (new_id,))
    new_art = cursor.fetchone()
    conn.close()

    # --- Synchronisation RAG : rend l'article utilisable par generer_argumentaire ---
    rag_sync = False
    try:
        ajouter_article_rag(new_id, body.code_direction, body.numero_article, body.texte_extrait, body.date_version)
        rag_sync = True
    except Exception as e:
        print(f"[SYNC RAG] Echec de synchronisation (ajout) : {e}")

    add_system_log(
        user_name, user_role, "Ajout Article", 
        f"Article {body.numero_article}", f"Ajouté à la base réglementaire pour {body.code_direction}."
    )
    result = dict(new_art)
    result["rag_sync"] = rag_sync
    return result

@app.put("/api/base-reglementaire/{id}", response_model=ArticleResponse)
def update_article(
    id: int, 
    body: ArticleCreateUpdate, 
    user_name: str = Query(...), 
    user_role: str = Query(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM articles WHERE id = ?", (id,))
    art = cursor.fetchone()
    if not art:
        conn.close()
        raise HTTPException(status_code=404, detail="Article non trouvé.")

    art_dict = dict(art)
        
    cursor.execute("""
    UPDATE articles 
    SET numero_article = ?, texte_extrait = ?, decret_source = ?, date_version = ?, code_direction = ?
    WHERE id = ?
    """, (body.numero_article, body.texte_extrait, body.decret_source, body.date_version, body.code_direction, id))
    conn.commit()
    
    cursor.execute("SELECT * FROM articles WHERE id = ?", (id,))
    updated_art = cursor.fetchone()
    conn.close()

    # --- Synchronisation RAG ---
    rag_sync = False
    try:
        rag_sync = modifier_article_rag(
            id, body.code_direction, body.numero_article, body.texte_extrait, body.date_version,
            ancien_texte=art_dict["texte_extrait"]
        )
    except Exception as e:
        print(f"[SYNC RAG] Echec de synchronisation (modification) : {e}")

    add_system_log(
        user_name, user_role, "Modif. Article", 
        f"Article {body.numero_article}", f"Modifications enregistrées."
    )
    result = dict(updated_art)
    result["rag_sync"] = rag_sync
    return result

@app.delete("/api/base-reglementaire/{id}")
def delete_article(
    id: int, 
    user_name: str = Query(...), 
    user_role: str = Query(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM articles WHERE id = ?", (id,))
    art = cursor.fetchone()
    if not art:
        conn.close()
        raise HTTPException(status_code=404, detail="Article non trouvé.")

    art_dict = dict(art)
        
    cursor.execute("DELETE FROM articles WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    # --- Synchronisation RAG (base utilisée par generer_argumentaire) ---
    rag_sync = False
    try:
        rag_sync = supprimer_article_rag(
            id,
            code_direction=art_dict["code_direction"],
            numero_article=art_dict["numero_article"],
            texte_extrait=art_dict["texte_extrait"],
        )
    except Exception as e:
        print(f"[SYNC RAG] Echec de synchronisation (suppression) : {e}")

    add_system_log(
        user_name, user_role, "Suppr. Article", 
        f"Article {art_dict['numero_article']}", "Supprimé de la base réglementaire."
    )
    return {
        "message": "Article supprimé avec succès",
        "rag_sync": rag_sync,
    }

# --- GESTION DES RESPONSABLES ---

@app.get("/api/responsables", response_model=List[UserResponse])
def get_responsables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY role DESC, id ASC")
    rows = cursor.fetchall()
    users = [dict(row) for row in rows]
    conn.close()
    return users

@app.post("/api/responsables", response_model=UserResponse)
def create_responsable(
    body: UserCreate, 
    user_name: str = Query(...), 
    user_role: str = Query(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO users (email, password_hash, nom_complet, direction, role, statut)
        VALUES (?, 'password123', ?, ?, ?, ?)
        """, (body.email, body.nom_complet, body.direction, body.role, body.statut))
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")
        
    cursor.execute("SELECT * FROM users WHERE id = ?", (new_id,))
    new_user = cursor.fetchone()
    conn.close()
    
    add_system_log(
        user_name, user_role, "Création Compte", 
        f"Utilisateur: {body.nom_complet}", f"Attribution du rôle {body.role} ({body.direction})."
    )
    return dict(new_user)

@app.put("/api/responsables/{id}", response_model=UserResponse)
def update_responsable(
    id: int, 
    body: UserUpdate, 
    user_name: str = Query(...), 
    user_role: str = Query(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
        
    cursor.execute("""
    UPDATE users 
    SET nom_complet = ?, direction = ?, role = ?, statut = ?
    WHERE id = ?
    """, (body.nom_complet, body.direction, body.role, body.statut, id))
    conn.commit()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
    updated_user = cursor.fetchone()
    conn.close()
    
    add_system_log(
        user_name, user_role, "Modification Compte", 
        f"Utilisateur: {body.nom_complet}", "Attributs du compte mis à jour."
    )
    return dict(updated_user)

@app.post("/api/responsables/{id}/toggle-status")
def toggle_responsable_status(
    id: int, 
    user_name: str = Query(...), 
    user_role: str = Query(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")
        
    nouveau_statut = "INACTIF" if user['statut'] == "ACTIF" else "ACTIF"
    cursor.execute("UPDATE users SET statut = ? WHERE id = ?", (nouveau_statut, id))
    conn.commit()
    conn.close()
    
    add_system_log(
        user_name, user_role, "Modif. Accès", 
        f"Utilisateur: {user['nom_complet']}", f"Compte passé à {nouveau_statut}."
    )
    return {"message": f"Statut passé à {nouveau_statut}"}

# --- JOURNAL D'ACTIVITÉ (LOGS) ---

@app.get("/api/logs", response_model=List[LogResponse])
def get_logs(
    action_type: Optional[str] = None,
    q: Optional[str] = None
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM logs WHERE 1=1"
    params = []
    
    if action_type and action_type != "Toutes les actions":
        query += " AND action = ?"
        params.append(action_type)
        
    if q:
        query += " AND (utilisateur LIKE ? OR element_concerne LIKE ? OR detail LIKE ?)"
        search_param = f"%{q}%"
        params.extend([search_param, search_param, search_param])
        
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    logs = [dict(row) for row in rows]
    conn.close()
    return logs

@app.get("/api/logs/export")
def export_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY id DESC")
    rows = cursor.fetchall()
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Date/Heure", "Utilisateur", "Rôle", "Action", "Élément concerné", "Détail"])
    
    for r in rows:
        writer.writerow([r['date_heure'], r['utilisateur'], r['role'], r['action'], r['element_concerne'], r['detail']])
        
    conn.close()
    
    headers = {
        'Content-Disposition': 'attachment; filename="journal_activite.csv"'
    }
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers=headers
    )

# --- MOTS INTERDITS ---

@app.get("/api/mots-interdits", response_model=List[ForbiddenWordResponse])
def get_mots_interdits(langue: Optional[str] = "Français"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mots_interdits WHERE langue = ? ORDER BY mot ASC", (langue,))
    rows = cursor.fetchall()
    words = [dict(row) for row in rows]
    conn.close()
    return words

@app.post("/api/mots-interdits")
def create_mots_interdits(
    body: ForbiddenWordCreate, 
    user_name: str = Query(...), 
    user_role: str = Query(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Permet d'insérer des mots séparés par des virgules (ajout multiple)
    mots = [m.strip() for m in body.mot.split(",") if m.strip()]
    inserted_count = 0
    
    for mot in mots:
        try:
            cursor.execute("""
            INSERT INTO mots_interdits (mot, langue, categorie)
            VALUES (?, ?, ?)
            """, (mot, body.langue, body.categorie))
            inserted_count += 1
        except sqlite3.IntegrityError:
            # Ignorer si déjà existant
            pass
            
    conn.commit()
    conn.close()

    moderation_sync = False
    if inserted_count > 0:
        sync_res = synchroniser_mots_interdits()
        moderation_sync = sync_res.get("sync_ok", False)
        add_system_log(
            user_name, user_role, "Modif. Mots Interdits", 
            "Liste Noire Lexicale", f"Ajout de {inserted_count} mots ({body.langue}, Catégorie: {body.categorie})."
        )
        
    return {
        "message": f"{inserted_count} mots ajoutés avec succès.",
        "moderation_sync": moderation_sync,
    }

@app.delete("/api/mots-interdits/{id}")
def delete_mot_interdit(
    id: int, 
    user_name: str = Query(...), 
    user_role: str = Query(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mots_interdits WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Mot non trouvé.")
        
    cursor.execute("DELETE FROM mots_interdits WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    sync_res = synchroniser_mots_interdits()
    moderation_sync = sync_res.get("sync_ok", False)
    
    add_system_log(
        user_name, user_role, "Modif. Mots Interdits", 
        "Liste Noire Lexicale", f"Suppression du mot '{row['mot']}' ({row['langue']})."
    )
    return {
        "message": "Mot interdit supprimé avec succès",
        "moderation_sync": moderation_sync,
    }
# --- RAPPORT ANALYTIQUE TRIMESTRIEL ---

@app.get("/api/rapport")
def get_rapport_data(date_debut: Optional[str] = None, date_fin: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM demandes ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    demandes = [dict(row) for row in rows]

    if not demandes:
        return {
            "indicateurs_generaux": {"recues": 0, "cloturees": 0, "en_cours": 0, "non_concernees": 0},
            "par_direction": [],
            "respect_delais": {"traitees_dans_delai": 0, "hors_delai": 0, "taux_respect": None},
            "delais_moyens": [],
            "fiabilite_ia": [],
            "dossiers_critiques": [],
        }

    df = pd.DataFrame(demandes)
    df['date_depot_dt'] = pd.to_datetime(df['date_depot'], errors='coerce')
    df['date_echeance_dt'] = pd.to_datetime(df['date_echeance'], errors='coerce')
    df['date_reponse_dt'] = pd.to_datetime(df.get('date_reponse'), errors='coerce') if 'date_reponse' in df.columns else pd.NaT

    # --- Filtre de période (nouveau) ---
    if date_debut:
        df = df[df['date_depot_dt'] >= pd.to_datetime(date_debut)]
    if date_fin:
        borne_fin = pd.to_datetime(date_fin) + pd.Timedelta(days=1)  # inclure toute la journée de fin
        df = df[df['date_depot_dt'] < borne_fin]

    if df.empty:
        return {
            "indicateurs_generaux": {"recues": 0, "cloturees": 0, "en_cours": 0, "non_concernees": 0},
            "par_direction": [],
            "respect_delais": {"traitees_dans_delai": 0, "hors_delai": 0, "taux_respect": None},
            "delais_moyens": [],
            "fiabilite_ia": [],
            "dossiers_critiques": [],
        }
    # --- Fin du filtre ---

    def direction_finale(row):
        if row['decision_responsable'] == "Validé":
            return row['direction_predite']
        return row['decision_responsable'].replace("Corriger : ", "").strip()
    df['direction_finale'] = df.apply(direction_finale, axis=1)

    # (le reste de la fonction ne change pas : indicateurs_generaux, par_direction,
    #  respect_delais, delais_moyens, fiabilite_ia, dossiers_critiques, return)
    # 1. Indicateurs généraux
    recues = len(df)
    cloturees = int((df['statut_demande'] == 'Répondue').sum())
    non_concernees = int((df['direction_finale'] == 'Non concerné').sum())
    en_cours = recues - cloturees

    indicateurs_generaux = {
        "recues": recues,
        "cloturees": cloturees,
        "en_cours": en_cours,
        "non_concernees": non_concernees,
    }

    # 2. Analyse par direction
    par_direction = []
    for direction, groupe in df.groupby('direction_finale'):
        if direction == "Non concerné":
            continue
        recues_d = len(groupe)
        cloturees_d = int((groupe['statut_demande'] == 'Répondue').sum())
        en_retard_ouvert = ((groupe['statut_demande'] != 'Répondue') & (groupe['type_alerte'] == 'depasse')).sum()
        en_retard_reponse = ((groupe['statut_demande'] == 'Répondue') &
                              groupe['date_reponse_dt'].notna() &
                              (groupe['date_reponse_dt'] > groupe['date_echeance_dt'])).sum()
        en_retard_d = int(en_retard_ouvert + en_retard_reponse)
        taux_retard_d = round((en_retard_d / recues_d) * 100, 1) if recues_d > 0 else 0.0

        par_direction.append({
            "direction": direction,
            "recues": recues_d,
            "cloturees": cloturees_d,
            "en_retard": en_retard_d,
            "taux_retard": taux_retard_d,
        })
    par_direction.sort(key=lambda d: d["recues"], reverse=True)

    # 3. Respect des délais légaux
    df_repondues = df[(df['statut_demande'] == 'Répondue') & df['date_reponse_dt'].notna()].copy()
    if len(df_repondues) > 0:
        dans_delai = int((df_repondues['date_reponse_dt'] <= df_repondues['date_echeance_dt']).sum())
        hors_delai = len(df_repondues) - dans_delai
        taux_respect = round((dans_delai / len(df_repondues)) * 100, 1)
    else:
        dans_delai, hors_delai, taux_respect = 0, 0, None

    respect_delais = {
        "traitees_dans_delai": dans_delai,
        "hors_delai": hors_delai,
        "taux_respect": taux_respect,
    }

    # 4. Délais moyens par direction
    delais_moyens = []
    if len(df_repondues) > 0:
        df_repondues['delai_reel_jours'] = (df_repondues['date_reponse_dt'] - df_repondues['date_depot_dt']).dt.days
        df_repondues['direction_finale_r'] = df_repondues.apply(direction_finale, axis=1)
        for direction, groupe in df_repondues.groupby('direction_finale_r'):
            if direction == "Non concerné":
                continue
            delais_moyens.append({
                "direction": direction,
                "delai_cible": 60,
                "delai_reel_moyen": round(float(groupe['delai_reel_jours'].mean()), 1),
            })
        delais_moyens.sort(key=lambda d: d["direction"])

    # 5. Fiabilité de la classification IA par direction
    fiabilite_ia = []
    for direction, groupe in df.groupby('direction_predite'):
        total_d = len(groupe)
        score_moyen_d = round(float(groupe['score_confiance'].mean()) * 100, 1)
        corrigees_d = int((groupe['decision_responsable'] != "Validé").sum())
        taux_correction_d = round((corrigees_d / total_d) * 100, 1) if total_d > 0 else 0.0
        signalees_d = int(((groupe['contenu_valide'] == 0) | (groupe['mot_interdit_detecte'] == 1)).sum())

        fiabilite_ia.append({
            "direction": direction,
            "score_confiance_moyen": score_moyen_d,
            "taux_correction": taux_correction_d,
            "contenus_signales": signalees_d,
        })
    fiabilite_ia.sort(key=lambda d: d["taux_correction"], reverse=True)

    # 6. Dossiers critiques
    df_critiques = df[(df['type_alerte'] == 'depasse') & (df['statut_demande'] != 'Répondue')].copy()
    dossiers_critiques = []
    if len(df_critiques) > 0:
        now = pd.Timestamp.now()
        df_critiques['retard_jours'] = (now - df_critiques['date_echeance_dt']).dt.days
        df_critiques = df_critiques.sort_values('retard_jours', ascending=False)
        for _, r in df_critiques.head(20).iterrows():
            dossiers_critiques.append({
                "reclamation": f"GEDEC-2026-{int(r['id']):03d}",
                "direction": r['direction_finale'],
                "retard_jours": int(r['retard_jours']),
                "statut": r['statut_demande'],
            })

    return {
        "indicateurs_generaux": indicateurs_generaux,
        "par_direction": par_direction,
        "respect_delais": respect_delais,
        "delais_moyens": delais_moyens,
        "fiabilite_ia": fiabilite_ia,
        "dossiers_critiques": dossiers_critiques,
    }
@app.get("/api/rapport/tendances")
def get_rapport_tendances(date_debut: Optional[str] = None, date_fin: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM demandes ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    demandes = [dict(row) for row in rows]

    if not demandes:
        return {"repartition_region": [], "repartition_direction": [], "evolution_demandes": [], "delais_moyens_direction": []}

    df = pd.DataFrame(demandes)
    df['date_depot_dt'] = pd.to_datetime(df['date_depot'], errors='coerce')
    df['date_reponse_dt'] = pd.to_datetime(df.get('date_reponse'), errors='coerce') if 'date_reponse' in df.columns else pd.NaT

    if date_debut:
        df = df[df['date_depot_dt'] >= pd.to_datetime(date_debut)]
    if date_fin:
        df = df[df['date_depot_dt'] < pd.to_datetime(date_fin) + pd.Timedelta(days=1)]

    if df.empty:
        return {"repartition_region": [], "repartition_direction": [], "evolution_demandes": [], "delais_moyens_direction": []}

    def direction_finale(row):
        if row['decision_responsable'] == "Validé":
            return row['direction_predite']
        return row['decision_responsable'].replace("Corriger : ", "").strip()
    df['direction_finale'] = df.apply(direction_finale, axis=1)

    total = len(df)

    # Répartition par région
    repartition_region = [
        {"nom": region, "nombre": int(n), "pourcentage": round(n / total * 100, 1)}
        for region, n in df['region'].value_counts().items()
    ]

    # Répartition par direction
    repartition_direction = [
        {"nom": d, "nombre": int(n), "pourcentage": round(n / total * 100, 1)}
        for d, n in df['direction_finale'].value_counts().items()
    ]

    # Évolution des demandes par semaine
    df['semaine'] = df['date_depot_dt'].dt.strftime('%Y-S%U')
    evolution_demandes = [
        {"periode": semaine, "nombre": int(n)}
        for semaine, n in df.groupby('semaine').size().items()
    ]

    # Délai moyen de réponse par direction
    df_rep = df[df['date_reponse_dt'].notna()].copy()
    delais_moyens_direction = []
    if len(df_rep) > 0:
        df_rep['delai_jours'] = (df_rep['date_reponse_dt'] - df_rep['date_depot_dt']).dt.days
        for d, groupe in df_rep.groupby('direction_finale'):
            delais_moyens_direction.append({
                "direction": d,
                "delai_moyen": round(float(groupe['delai_jours'].mean()), 1)
            })

    return {
        "repartition_region": repartition_region,
        "repartition_direction": repartition_direction,
        "evolution_demandes": evolution_demandes,
        "delais_moyens_direction": delais_moyens_direction,
    }
@app.post("/api/rapports-historique")
def sauvegarder_rapport(
    nom: str = Query(...),
    type_rapport: str = Query(...),
    date_debut: Optional[str] = Query(None),
    date_fin: Optional[str] = Query(None),
    user_name: str = Query(...),
):
    if type_rapport == "bilan":
        donnees = get_rapport_data(date_debut, date_fin)
    else:
        donnees = get_rapport_tendances(date_debut, date_fin)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO rapports_historique (nom, type_rapport, date_debut, date_fin, date_generation, genere_par, donnees_json)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (nom, type_rapport, date_debut, date_fin, datetime.now().strftime("%d/%m/%Y %H:%M:%S"), user_name, json.dumps(donnees, ensure_ascii=False)))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"message": "Rapport enregistré dans l'historique.", "id": new_id}

@app.get("/api/rapports-historique")
def lister_rapports_historique():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nom, type_rapport, date_debut, date_fin, date_generation, genere_par FROM rapports_historique ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
@app.delete("/api/rapports-historique/{id}")
def supprimer_rapport_historique(id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM rapports_historique WHERE id = ?", (id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Rapport non trouvé.")
    cursor.execute("DELETE FROM rapports_historique WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"message": "Rapport supprimé de l'historique."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)