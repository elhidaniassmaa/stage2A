import os
import sys
import sqlite3
import json
from datetime import datetime

# Garantir l'accès aux modules backend et src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Source de vérité unique : toujours backend/gedec.db (chemin absolu, indépendant du CWD).
DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "gedec.db"))

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table des utilisateurs (Responsables / Administrateurs)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nom_complet TEXT NOT NULL,
        direction TEXT NOT NULL,
        role TEXT NOT NULL,
        demandes_traitees INTEGER DEFAULT 0,
        derniere_connexion TEXT DEFAULT NULL,
        statut TEXT DEFAULT 'ACTIF'
    )
    """)

    # Table de la base réglementaire (Articles)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_article TEXT NOT NULL,
        texte_extrait TEXT NOT NULL,
        decret_source TEXT NOT NULL,
        date_version TEXT NOT NULL,
        code_direction TEXT NOT NULL
    )
    """)

    # Table des mots interdits
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mots_interdits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mot TEXT UNIQUE NOT NULL,
        langue TEXT NOT NULL,
        categorie TEXT NOT NULL DEFAULT 'Vulgarité'
    )
    """)

    # Table du journal d'activité (Logs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_heure TEXT NOT NULL,
        utilisateur TEXT NOT NULL,
        role TEXT NOT NULL,
        action TEXT NOT NULL,
        element_concerne TEXT NOT NULL,
        detail TEXT NOT NULL
    )
    """)

    # Table des demandes citoyennes
    # Table des demandes citoyennes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS demandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        prenom TEXT,
        message_original TEXT NOT NULL,
        message_nettoye TEXT NOT NULL,
        date_depot TEXT NOT NULL,
        date_echeance TEXT NOT NULL,
        type_alerte TEXT NOT NULL DEFAULT 'aucune',
        contenu_valide INTEGER DEFAULT 1,
        mot_interdit_detecte INTEGER DEFAULT 0,
        direction_predite TEXT NOT NULL,
        score_confiance REAL NOT NULL,
        confiance_faible INTEGER DEFAULT 0,
        argumentaire TEXT NOT NULL,
        decision_responsable TEXT DEFAULT 'Validé',
        statut_demande TEXT DEFAULT 'En attente',
        region TEXT DEFAULT 'Rabat-Salé-Kénitra',
        notif_rappel_envoyee INTEGER DEFAULT 0,
        notif_prioritaire_envoyee INTEGER DEFAULT 0,
        date_reponse TEXT,
        theme TEXT
    )
    """)
 

    conn.commit()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rapports_historique (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        type_rapport TEXT NOT NULL,
        date_debut TEXT,
        date_fin TEXT,
        date_generation TEXT NOT NULL,
        genere_par TEXT NOT NULL,
        donnees_json TEXT NOT NULL
    )
    """)
    conn.commit()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications_vues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        demande_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        date_vue TEXT NOT NULL,
        UNIQUE(demande_id, user_id)
    )
    """)
    conn.commit()
    # --- ENSEMBLING / SEEDING DATA ---

    # 1. Seed Users (Responsables)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users_seed = [
            ("a.benali@transport.gov.ma", "password123", "Ahmed Benali", "DTR", "Responsable", 156, "Aujourd'hui, 09:42", "ACTIF"),
            ("s.mansouri@transport.gov.ma", "password123", "Sara Mansouri", "DSPCT", "Responsable", 89, "Hier, 16:15", "ACTIF"),
            ("k.idrissi@transport.gov.ma", "password123", "Kamal Idrissi", "DAAJJ", "Responsable", 12, "12 Mai 2024", "INACTIF"),
            ("y.drissi@transport.gov.ma", "password123", "Yassine Drissi", "DJAC", "Responsable", 214, "Aujourd'hui, 11:30", "ACTIF"),
            ("admin@transport.gov.ma", "password123", "Admin Principal", "DSI", "Administrateur", 0, "Aujourd'hui, 15:30", "ACTIF")
        ]
        cursor.executemany("""
        INSERT INTO users (email, password_hash, nom_complet, direction, role, demandes_traitees, derniere_connexion, statut)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, users_seed)
        conn.commit()

    # 2. Seed Articles (Base réglementaire)
    cursor.execute("SELECT COUNT(*) FROM articles")
    if cursor.fetchone()[0] == 0:
        # Insérer d'abord les articles de la capture d'écran 1
        screenshot_articles = [
            ("Art. 12-A", "Les conditions d'octroi des licences de transport international routier de marchandises.", "Décret 2.04.175", "12/10/2023", "DTR"),
            ("Art. 45", "Spécifications techniques des véhicules de transport de voyageurs et de marchandises.", "Loi 52.05", "05/01/2024", "DTR"),
            ("Art. 88-C", "Réglementation relative au temps de conduite et de repos des conducteurs professionnels.", "Décret 2.10.311", "22/02/2024", "DTR")
        ]
        cursor.executemany("""
        INSERT INTO articles (numero_article, texte_extrait, decret_source, date_version, code_direction)
        VALUES (?, ?, ?, ?, ?)
        """, screenshot_articles)

        # Charger et insérer les articles depuis base_reglementaire.json
        json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src/argumentaire/base_reglementaire.json"))
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    articles_json = json.load(f)

                ids_decret = []
                for art in articles_json:
                    num_art = f"Art. {art['numero_article']}"
                    if art['numero_article'].startswith("Hors"):
                        num_art = art['numero_article']

                    decret = "Décret 2.21.968"
                    if "Hors" in num_art:
                        decret = "Hors décret 2.21.968"

                    date_v = datetime.strptime(art['date_version'], "%Y-%m-%d").strftime("%d/%m/%Y")

                    cursor.execute("""
                    INSERT INTO articles (numero_article, texte_extrait, decret_source, date_version, code_direction)
                    VALUES (?, ?, ?, ?, ?)
                    """, (
                        num_art,
                        art['texte_clause'],
                        decret,
                        date_v,
                        art['code_direction']
                    ))
                    ids_decret.append(cursor.lastrowid)

                conn.commit()

                try:
                    from backend.sync_base_reglementaire import rattacher_par_ordre_seed
                    n = rattacher_par_ordre_seed(ids_decret)
                    if n > 0:
                        print(f"[SYNC RAG] {n} tiret(s) du décret lié(s) au JSON lors du seed initial.")
                except Exception as e:
                    print(f"[SYNC RAG] Echec liaison seed → JSON : {e}")
            except Exception as e:
                print(f"Erreur lors du chargement de base_reglementaire.json : {e}")
        conn.commit()

    # 3. Seed Mots Interdits
    cursor.execute("SELECT COUNT(*) FROM mots_interdits")
    if cursor.fetchone()[0] == 0:
        words_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../config/mots_interdits.txt"))
        mots_seed = []
        
        # Mots par défaut structurés selon la nouvelle taxonomie (5 catégories)
        default_mots = [
            ("salaud", "Français", "Insulte"),
            ("bâtard", "Français", "Insulte"),
            ("merde", "Français", "Vulgarité"),
            ("imbécile", "Français", "Insulte"),
            ("débile", "Français", "Insulte"),
            ("escroc", "Français", "Diffamation / Calomnie"),
            ("voleur", "Français", "Diffamation / Calomnie"),
            ("corrompu", "Français", "Diffamation / Calomnie"),
            ("حمار", "Arabe standard", "Insulte"),
            ("كلب", "Arabe standard", "Insulte"),
            ("غبي", "Arabe standard", "Insulte"),
            ("خسيس", "Arabe standard", "Insulte"),
            ("hmar", "Darija", "Insulte"),
            ("kalb", "Darija", "Insulte"),
            ("mkelleg", "Darija", "Insulte"),
            ("chouha", "Darija", "Vulgarité"),
            ("mseti", "Darija", "Insulte"),
            ("zbel", "Darija", "Vulgarité")
        ]
        
        if os.path.exists(words_file):
            try:
                current_lang = "Français"
                with open(words_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("#"):
                            header = line.replace("#", "").strip().lower()
                            if "français" in header:
                                current_lang = "Français"
                            elif "arabe" in header:
                                current_lang = "Arabe standard"
                            elif "darija" in header:
                                current_lang = "Darija"
                            continue
                        
                        # Déduire la catégorie basée sur la taxonomie officielle GEDEC
                        cat = "Insulte"
                        if line in ["merde", "chieur", "chouha", "شوها", "khayb", "خايب", "khayba", "خايبة", "khnez", "خنز", "n3al", "zbel", "زبل", "زبالة"]:
                            cat = "Vulgarité"
                        elif line in ["escroc", "voleur", "menteur", "corrompu", "pourri", "فاسد", "حرامي", "لص", "كذاب", "كداب", "kaddab"]:
                            cat = "Diffamation / Calomnie"
                        elif line in ["enculé"]:
                            cat = "Obscénité"
                            
                        mots_seed.append((line, current_lang, cat))
                
                # Fusionner avec les défauts pour s'assurer que c'est bien peuplé
                seen_words = {m[0] for m in mots_seed}
                for m in default_mots:
                    if m[0] not in seen_words:
                        mots_seed.append(m)
            except Exception as e:
                print(f"Erreur lors de la lecture de mots_interdits.txt : {e}")
                mots_seed = default_mots
        else:
            mots_seed = default_mots

        for mot, lang, cat in mots_seed:
            try:
                cursor.execute("""
                INSERT OR IGNORE INTO mots_interdits (mot, langue, categorie)
                VALUES (?, ?, ?)
                """, (mot, lang, cat))
            except sqlite3.Error:
                pass
        conn.commit()

    # 4. Seed Logs (Journal d'activité)
    cursor.execute("SELECT COUNT(*) FROM logs")
    if cursor.fetchone()[0] == 0:
        logs_seed = [
            ("14/05/2024 10:45:22", "Ahmed B.", "CHEF DE DIVISION", "Correction direction", "Demande #GEDEC-2024-089", "DTR -> DSPCT"),
            ("14/05/2024 10:30:15", "Meriem L.", "ADMINISTRATEUR", "Importation massive", "Fichier: demandes_mai.csv", "142 nouvelles demandes importées avec succès."),
            ("14/05/2024 09:12:04", "Said O.", "UTILISATEUR", "Consultation Rapport", "Bilan Trimestriel Q1", "Génération du rapport en format PDF."),
            ("13/05/2024 17:45:50", "System Agent", "SYSTEME", "Alerte de seuil", "Délai Traitement DTR", "Dépassement de 48h pour 5 dossiers actifs."),
            ("13/05/2024 16:20:11", "Meriem L.", "ADMINISTRATEUR", "Modif. Mots Interdits", "Liste Noire Lexicale", "Ajout du terme 'Obsolete_Ref' à la base réglementaire."),
            ("13/05/2024 14:10:33", "Yassine K.", "RESPONSABLE", "Validation Demande", "Demande #GEDEC-2024-012", "Dossier validé techniquement, transfert au service juridique."),
            ("13/05/2024 11:05:55", "Meriem L.", "ADMINISTRATEUR", "Création Compte", "Utilisateur: Fatima E.", "Attribution du rôle 'Utilisateur Direction' (DTR).")
        ]
        cursor.executemany("""
        INSERT INTO logs (date_heure, utilisateur, role, action, element_concerne, detail)
        VALUES (?, ?, ?, ?, ?, ?)
        """, logs_seed)
        conn.commit()
    # 5. Seed Demandes de base
    cursor.execute("SELECT COUNT(*) FROM demandes")
    if cursor.fetchone()[0] == 0:
        demandes_seed = [
            (
                "Alami", "Youssef",
                "Le camion de transport international bloque la rue principale à Tanger. Nous demandons une licence spéciale.",
                "Le camion de transport international bloque la rue principale a Tanger. Nous demandons une licence speciale.",
                "2026-06-15 10:00:00", "2026-08-14 10:00:00", "aucune", 1, 0, "DTR", 0.85, 0,
                "En vertu du Décret 2.21.968, la Direction des Transports Routiers (DTR) est chargée de la réglementation et du contrôle des activités de transport routier de marchandises et de voyageurs.",
                "Validé", "En attente", "Tanger-Tétouan-Al Hoceïma"
            ),
            (
                "Bennani", "Sara",
                "Demande d'autorisation pour l'aménagement d'une plateforme logistique près du port de Casablanca.",
                "Demande d'autorisation pour l'amenagement d'une plateforme logistique pres du port de Casablanca.",
                "2026-07-25 11:30:00", "2026-09-23 11:30:00", "prioritaire", 1, 0, "DSPCT", 0.92, 0,
                "En vertu du Décret 2.21.968, la Direction de la Stratégie, des Programmes et de la Coordination des Transports (DSPCT) coordonne l'élaboration et la mise en œuvre de la stratégie nationale logistique.",
                "Validé", "En attente", "Casablanca-Settat"
            ),
            (
                "Idrissi", "Karim",
                "Je signale des insultes graves de la part d'un fonctionnaire.",
                "Je signale des insultes graves de la part d'un fonctionnaire.",
                "2026-07-10 14:00:00", "2026-09-08 14:00:00", "aucune", 1, 0, "DAAJJ", 0.78, 0,
                "En vertu du Décret 2.21.968, la Direction des Affaires Administratives, Juridiques et Générales (DAAJJ) est compétente pour le traitement des affaires juridiques, des requêtes et de la gestion administrative.",
                "Validé", "En attente", "Rabat-Salé-Kénitra"
            )
        ]
        cursor.executemany("""
        INSERT INTO demandes (
            nom, prenom, message_original, message_nettoye, date_depot, date_echeance, type_alerte,
            contenu_valide, mot_interdit_detecte, direction_predite, score_confiance, confiance_faible,
            argumentaire, decision_responsable, statut_demande, region
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, demandes_seed)
        conn.commit()

    conn.close()

    try:
        from backend.sync_base_reglementaire import rattacher_articles_heritage
        resultat = rattacher_articles_heritage()
        if resultat["rattaches"] > 0:
            print(f"[SYNC RAG] {resultat['rattaches']} article(s) hérité(s) rattaché(s) au JSON.")
    except Exception as e:
        print(f"[SYNC RAG] Echec du rattachement rétroactif : {e}")

    try:
        from backend.sync_mots_interdits import synchroniser_mots_interdits
        sync_mots = synchroniser_mots_interdits()
        if sync_mots.get("sync_ok"):
            print(f"[SYNC MOTS] {sync_mots['mots_exportes']} mot(s) interdit(s) synchronisé(s).")
    except Exception as e:
        print(f"[SYNC MOTS] Echec synchronisation mots interdits : {e}")

if __name__ == "__main__":
    init_db()
    print("Base de données initialisée avec succès.")
