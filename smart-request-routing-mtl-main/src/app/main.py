import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import sys
from datetime import datetime

# Ajouter le dossier src au chemin de recherche pour pouvoir importer les modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from preprocessing.clean_text import clean_text
from moderation.moderation import verifier_contenu
from classification.predict import predire_direction
from argumentaire.generer_argumentaire import generer_argumentaire
from app.echeance import calculer_echeance, verifier_alerte
from app.rapport import generer_rapport, generer_graphiques

# Configuration globale de la page
st.set_page_config(
    layout="wide",
    page_title="🏛️ Portail Citoyen - Gestion des Demandes",
    page_icon="🏛️"
)

# Style CSS personnalisé pour l'interface premium
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1E3A8A, #3B82F6);
        padding: 20px 30px;
        border-radius: 10px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        margin: 0;
        font-family: 'Outfit', 'Inter', sans-serif;
        font-weight: 700;
        font-size: 2.2rem;
    }
    .main-header p {
        margin: 5px 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    .card-title {
        font-size: 1.1rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 5px;
    }
    .badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.85rem;
        display: inline-block;
        margin-top: 5px;
    }
    .badge-ok {
        color: #15803D;
        background-color: #DCFCE7;
        border: 1px solid #86EFAC;
    }
    .badge-toxic {
        color: #991B1B;
        background-color: #FEE2E2;
        border: 1px solid #FCA5A5;
    }
    .badge-warning {
        color: #C2410C;
        background-color: #FFEDD5;
        border: 1px solid #FDBA74;
    }
    .badge-danger {
        color: #991B1B;
        background-color: #FEE2E2;
        border: 1px solid #FCA5A5;
    }
</style>
""", unsafe_allow_html=True)

# En-tête principal
st.markdown("""
<div class="main-header">
    <h1>🏛️ Plateforme de Traitement des Demandes Citoyennes</h1>
    <p>Ministère du Transport et de la Logistique - Administration Centrale</p>
</div>
""", unsafe_allow_html=True)

# Initialisation du session_state
if 'processed_df' not in st.session_state:
    st.session_state['processed_df'] = None
if 'uploaded_file_name' not in st.session_state:
    st.session_state['uploaded_file_name'] = ""
if 'decisions' not in st.session_state:
    st.session_state['decisions'] = {}
if 'statuts' not in st.session_state:
    st.session_state['statuts'] = {}
if 'argumentaires' not in st.session_state:
    st.session_state['argumentaires'] = {}

def get_columns(df):
    """
    Identifie de manière robuste les colonnes 'Message' et 'Date de dépôt'.
    """
    msg_col = None
    date_col = None
    
    for col in df.columns:
        col_lower = str(col).lower()
        if 'message' in col_lower:
            msg_col = col
        elif 'depot' in col_lower or 'dépôt' in col_lower or 'date' in col_lower:
            date_col = col
            
    if msg_col is None:
        msg_col = df.columns[0]
        
    return msg_col, date_col

def process_data(df):
    """
    Traite automatiquement chaque ligne en exécutant séquentiellement les modules du projet.
    """
    msg_col, date_col = get_columns(df)
    processed_rows = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_rows = len(df)
    
    for idx, row in df.iterrows():
        status_text.text(f"Analyse automatique de la demande {idx+1}/{total_rows}...")
        
        # Récupération et conversion du message et de la date
        raw_msg = str(row[msg_col]) if not pd.isna(row[msg_col]) else ""
        date_val = row[date_col] if date_col else None
        
        if pd.isna(date_val) or not date_val:
            date_depot = datetime.now()
        else:
            try:
                date_depot = pd.to_datetime(date_val)
                if isinstance(date_depot, pd.Timestamp):
                    date_depot = date_depot.to_pydatetime()
            except Exception:
                date_depot = datetime.now()
                
        # 1. Prétraitement (clean_text)
        cleaning_res = clean_text(raw_msg)
        cleaned_msg = cleaning_res["texte_nettoye"]
        
        # 2. Modération (verifier_contenu)
        mod_res = verifier_contenu(cleaned_msg)
        contenu_valide = mod_res["contenu_valide"]
        
        # 3. Classification (predire_direction)
        pred_res = predire_direction(cleaned_msg)
        dir_predite = pred_res["direction_predite"]
        score_confiance = pred_res["score_confiance"]
        confiance_faible = pred_res["indicateur_confiance_faible"]
        
        # 4. Génération d'argumentaire
        arg_text = generer_argumentaire(dir_predite, cleaned_msg)
        
        # 5. Délais & Échéances (calculer_echeance & verifier_alerte)
        date_echeance = calculer_echeance(date_depot)
        alerte_res = verifier_alerte(date_depot)
        type_alerte = alerte_res["type_alerte"]
        
        # Stockage
        row_dict = row.to_dict()
        row_dict['_raw_msg'] = raw_msg
        row_dict['_cleaned_msg'] = cleaned_msg
        row_dict['_contenu_valide'] = contenu_valide
        row_dict['_dir_predite'] = dir_predite
        row_dict['_score_confiance'] = score_confiance
        row_dict['_confiance_faible'] = confiance_faible
        row_dict['_arg_initial'] = arg_text
        row_dict['_date_echeance'] = date_echeance
        row_dict['_type_alerte'] = type_alerte
        
        processed_rows.append(row_dict)
        progress_bar.progress((idx + 1) / total_rows)
        
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(processed_rows)

def on_decision_change(idx, val, msg):
    """
    Met à jour la décision et régénère l'argumentaire à la volée en cas de correction.
    """
    st.session_state['decisions'][idx] = val
    if val == "Validé":
        # Rétablir la justification originale du modèle
        st.session_state['argumentaires'][idx] = st.session_state['processed_df'].loc[idx, '_arg_initial']
    else:
        # Extraire la direction corrigée
        new_dir = val.replace("Corriger : ", "")
        with st.spinner(f"Régénération de la base légale pour {new_dir}..."):
            st.session_state['argumentaires'][idx] = generer_argumentaire(new_dir, msg)

# --- ZONE D'IMPORTATION ---
# --- ZONE D'ONGLETS ---
tab_traitement, tab_rapport = st.tabs(["📋 Traitement des Demandes", "📊 Rapport trimestriel"])

with tab_traitement:
    st.subheader("1. Chargement des demandes citoyennes")
    uploaded_file = st.file_uploader(
        "Veuillez sélectionner un fichier Excel (.xlsx) contenant les réclamations citoyennes",
        type=["xlsx"]
    )

    if uploaded_file is not None:
        # Réinitialisation si nouveau fichier
        if st.session_state['uploaded_file_name'] != uploaded_file.name:
            st.session_state['uploaded_file_name'] = uploaded_file.name
            st.session_state['processed_df'] = None
            st.session_state['decisions'] = {}
            st.session_state['statuts'] = {}
            st.session_state['argumentaires'] = {}
            
        # Traitement initial
        if st.session_state['processed_df'] is None:
            try:
                df_raw = pd.read_excel(uploaded_file)
                st.session_state['processed_df'] = process_data(df_raw)
                
                # Initialiser les décisions, statuts et justifications
                for idx, row in st.session_state['processed_df'].iterrows():
                    st.session_state['decisions'][idx] = "Validé"
                    st.session_state['statuts'][idx] = "En attente"
                    st.session_state['argumentaires'][idx] = row['_arg_initial']
            except Exception as e:
                st.error(f"Erreur lors de la lecture du fichier : {e}")

    # --- TABLEAU DE BORD INTERACTIF ---
    if st.session_state['processed_df'] is not None:
        df_proc = st.session_state['processed_df']
        
        # Indicateurs clés de performance (KPIs)
        total_demandes = len(df_proc)
        statuts_values = list(st.session_state['statuts'].values())
        repondues = statuts_values.count("Répondue")
        en_attente = total_demandes - repondues
        
        # Compter les alertes
        alertes_prioritaires = len(df_proc[df_proc['_type_alerte'].isin(['prioritaire', 'depasse'])])
        
        st.write("---")
        st.subheader("2. Vue d'ensemble et statistiques")
        
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        with kpi_col1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{total_demandes}</div><div class="metric-label">Total Demandes</div></div>', unsafe_allow_html=True)
        with kpi_col2:
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #10B981;">{repondues}</div><div class="metric-label">Demandes Traitées</div></div>', unsafe_allow_html=True)
        with kpi_col3:
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #3B82F6;">{en_attente}</div><div class="metric-label">En Attente</div></div>', unsafe_allow_html=True)
        with kpi_col4:
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color: #EF4444;">{alertes_prioritaires}</div><div class="metric-label">Urgent / Dépassé</div></div>', unsafe_allow_html=True)
            
        st.write("---")
        st.subheader("3. Traitement détaillé des réclamations")
        
        # Filtres interactifs
        filtre_col1, filtre_col2 = st.columns(2)
        with filtre_col1:
            filtre_statut = st.radio("Filtrer par statut :", ["Toutes", "En attente", "Répondue"], horizontal=True)
        with filtre_col2:
            filtre_urgence = st.checkbox("Afficher uniquement les dossiers urgents (≤ 5j ou dépassés)", value=False)
            
        # Liste des demandes
        for idx, row in df_proc.iterrows():
            curr_statut = st.session_state['statuts'][idx]
            type_alerte = row['_type_alerte']
            
            # Application des filtres
            if filtre_statut != "Toutes" and curr_statut != filtre_statut:
                continue
            if filtre_urgence and type_alerte not in ['prioritaire', 'depasse']:
                continue
                
            # Conteneur pour chaque carte de demande
            with st.container(border=True):
                col_msg, col_info, col_action = st.columns([5, 4, 3])
                
                with col_msg:
                    # Message tronqué
                    raw_message = row['_raw_msg']
                    truncated = raw_message[:200] + "..." if len(raw_message) > 200 else raw_message
                    st.markdown(f"**Message de la demande :**\n*{truncated}*")
                    
                    # Modération
                    if not row['_contenu_valide']:
                        st.markdown('<span class="badge badge-toxic">🚨 Contenu Suspect ou Toxique détecté</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="badge badge-ok">✅ Modération OK</span>', unsafe_allow_html=True)
                        
                    st.caption(f"📅 Échéance légale : {row['_date_echeance'].strftime('%d/%m/%Y')}")
                    
                with col_info:
                    # Direction Proposée
                    dir_predite = row['_dir_predite']
                    score = row['_score_confiance']
                    confiance_label = "Confiance Faible ⚠️" if row['_confiance_faible'] else "Confiance Élevée ✅"
                    color_confiance = "#C2410C" if row['_confiance_faible'] else "#15803D"
                    
                    st.markdown(f"**Direction proposée :** `{dir_predite}`")
                    st.markdown(f"<span style='color: {color_confiance}; font-size: 0.9rem;'>{confiance_label} ({score:.2%})</span>", unsafe_allow_html=True)
                    
                    # Alerte délai
                    if type_alerte == "depasse":
                        st.markdown('<span class="badge badge-danger">🚨 DÉCHET DÉPASSÉ</span>', unsafe_allow_html=True)
                    elif type_alerte == "prioritaire":
                        st.markdown('<span class="badge badge-warning">⚠️ PRIORITAIRE (≤ 5 jours)</span>', unsafe_allow_html=True)
                    elif type_alerte == "rappel":
                        st.markdown('<span class="badge" style="color: #0369A1; background-color: #E0F2FE; border: 1px solid #7DD3FC;">🕒 Rappel (6-15 jours)</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="badge" style="color: #15803D; background-color: #F0FDF4; border: 1px solid #BBF7D0;">🟢 Délais confortables</span>', unsafe_allow_html=True)
                        
                    # Argumentaire
                    st.markdown(f"**Justification réglementaire :**\n*{st.session_state['argumentaires'][idx]}*")
                    
                with col_action:
                    # Menu de décision
                    dir_options = ["Validé", "Corriger : DSI", "Corriger : DSPCT", "Corriger : DAAJJ", "Corriger : DMM", "Corriger : DTR", "Corriger : DJAC", "Corriger : Cabinet du Ministère", "Corriger : Non concerné"]
                    
                    curr_decision = st.session_state['decisions'][idx]
                    selected_decision = st.selectbox(
                        "Action du responsable :",
                        dir_options,
                        index=dir_options.index(curr_decision) if curr_decision in dir_options else 0,
                        key=f"sel_{idx}"
                    )
                    
                    if selected_decision != curr_decision:
                        on_decision_change(idx, selected_decision, row['_cleaned_msg'])
                        st.rerun()
                        
                    # Statut & Bouton validation finale
                    if curr_statut == "Répondue":
                        st.markdown("<div style='text-align: center; color: #15803D; font-weight: bold; padding: 8px;'>✅ RÉPONDUE</div>", unsafe_allow_html=True)
                    else:
                        if st.button("Marquer comme répondue", key=f"btn_{idx}", use_container_width=True):
                            st.session_state['statuts'][idx] = "Répondue"
                            st.success("Demande marquée comme répondue !")
                            st.rerun()
                            
        # --- ZONE D'EXPORTATION ---
        st.write("---")
        st.subheader("4. Finalisation et Exportation")
        
        # Construction du DataFrame d'export
        export_rows = []
        for idx, row in df_proc.iterrows():
            # Conserver les colonnes d'origine uniquement
            orig_row = {k: v for k, v in row.items() if not k.startswith('_')}
            
            # Ajouter les nouvelles colonnes d'analyse
            orig_row["Direction proposée"] = row["_dir_predite"]
            orig_row["Score de confiance"] = row["_score_confiance"]
            orig_row["Argumentaire"] = st.session_state['argumentaires'][idx]
            
            # Traduction de la décision du responsable
            decision = st.session_state['decisions'][idx]
            if decision == "Validé":
                orig_row["Décision du Responsable"] = f"Validé ({row['_dir_predite']})"
            else:
                orig_row["Décision du Responsable"] = decision.replace("Corriger : ", "")
                
            orig_row["Statut"] = st.session_state['statuts'][idx]
            export_rows.append(orig_row)
            
        export_df = pd.DataFrame(export_rows)
        
        # Écriture en mémoire du fichier Excel
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name='Suivi Demandes')
        excel_data = excel_buffer.getvalue()
        
        # Bouton de téléchargement
        st.download_button(
            label="📥 Exporter les résultats au format Excel",
            data=excel_data,
            file_name=f"demandes_traitees_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

with tab_rapport:
    st.subheader("📊 Rapport trimestriel d'activité et performance")
    
    # Fichier source pour le rapport
    df_rapport = None
    
    # Option d'importation d'historique dédié
    uploader_rapport = st.file_uploader(
        "Charger un fichier d'historique ou d'export de traitement (.xlsx)",
        type=["xlsx"],
        key="uploader_rapport_exclusif"
    )
    
    if uploader_rapport is not None:
        try:
            df_rapport = pd.read_excel(uploader_rapport)
            st.success("Fichier d'historique importé avec succès pour analyse.")
        except Exception as e:
            st.error(f"Erreur lors du chargement du fichier : {e}")
    elif st.session_state['processed_df'] is not None:
        df_rapport = st.session_state['processed_df']
        st.info("Utilisation des données en cours de traitement issues de l'onglet principal.")
    else:
        # Essai de pré-chargement par défaut de data/dataset.xlsx pour la démonstration
        default_paths = ["data/dataset.xlsx", "data/dataset_final_fusionne.xlsx"]
        for path in default_paths:
            if os.path.exists(path):
                try:
                    df_rapport = pd.read_excel(path)
                    st.success(f"Données de démonstration chargées par défaut depuis {path}.")
                    break
                except Exception:
                    pass
                    
    if df_rapport is not None:
        # Calcul des statistiques
        resultats_rapport = generer_rapport(df_rapport)
        
        # Affichage des métriques clés
        rep_c1, rep_c2, rep_c3, rep_c4 = st.columns(4)
        with rep_c1:
            st.metric("Total Demandes Analysées", f"{resultats_rapport['total_demandes']}")
        with rep_c2:
            st.metric("Respect des Délais (60j)", f"{resultats_rapport['taux_respect']:.1f}%")
        with rep_c3:
            concordance = resultats_rapport["taux_concordance"]
            concordance_str = f"{concordance:.1f}%" if concordance is not None else "N/A"
            st.metric("Concordance IA / Décision", concordance_str)
        with rep_c4:
            conf_val = resultats_rapport["score_confiance_moyen"]
            conf_str = f"{conf_val:.1f}%" if conf_val > 1.0 else f"{conf_val:.2%}"
            st.metric("Confiance Moyenne IA", conf_str)
            
        # Affichage des graphiques
        st.write("---")
        fig_direction, fig_evolution = generer_graphiques(resultats_rapport)
        
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.pyplot(fig_direction)
        with chart_col2:
            st.pyplot(fig_evolution)
            
        # Tableaux de données détaillés sous les graphiques
        st.write("---")
        detail_col1, detail_col2 = st.columns(2)
        
        with detail_col1:
            st.write("#### 📍 Répartition par Région")
            if resultats_rapport["repartition_region"]:
                region_df = pd.DataFrame(
                    list(resultats_rapport["repartition_region"].items()), 
                    columns=["Région", "Nombre de Demandes"]
                ).sort_values(by="Nombre de Demandes", ascending=False)
                st.dataframe(region_df, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune information de région disponible.")
                
        with detail_col2:
            st.write("#### 📁 Répartition par Direction")
            if resultats_rapport["repartition_direction"]:
                direction_rows = []
                for d, metrics_dir in resultats_rapport["repartition_direction"].items():
                    direction_rows.append({
                        "Direction": d,
                        "Nombre": metrics_dir["nombre"],
                        "Pourcentage": f"{metrics_dir['pourcentage']:.1f}%"
                    })
                direction_df = pd.DataFrame(direction_rows).sort_values(by="Nombre", ascending=False)
                st.dataframe(direction_df, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune information de direction disponible.")
    else:
        st.warning("Aucune donnée disponible. Veuillez importer un fichier ou charger des demandes dans le premier onglet.")
