import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sqlite3

def generer_rapport(df_historique: pd.DataFrame) -> dict:
    """
    Calcule les métriques clés d'activité et de performance à partir d'un DataFrame historique.
    
    Arguments :
    - df_historique : DataFrame contenant les demandes traitées.
    
    Retourne un dictionnaire de métriques.
    """
    total_demandes = len(df_historique)
    if total_demandes == 0:
        return {
            "total_demandes": 0,
            "repartition_direction": {},
            "repartition_region": {},
            "taux_respect": 100.0,
            "taux_concordance": None,
            "score_confiance_moyen": 0.0,
            "evolution_respect": {"periodes": [], "taux": []}
        }

    # 1. Répartition par direction (nombre et pourcentage)
    # Recherche de la colonne contenant les informations de direction
    dir_col = None
    for col in ["Direction proposée", "Entité responsable", "Entit responsable"]:
        for c in df_historique.columns:
            if c.lower() == col.lower() or (col == "Entité responsable" and "responsable" in c.lower()):
                dir_col = c
                break
        if dir_col:
            break
            
    repartition_direction = {}
    if dir_col:
        counts = df_historique[dir_col].value_counts()
        for d, count in counts.items():
            pct = (count / total_demandes) * 100
            repartition_direction[str(d)] = {"nombre": int(count), "pourcentage": float(pct)}

    # 2. Répartition par région
    region_col = None
    for c in df_historique.columns:
        if "région" in c.lower() or "region" in c.lower() or "rgion" in c.lower():
            region_col = c
            break
            
    repartition_region = {}
    if region_col:
        region_counts = df_historique[region_col].value_counts()
        for r, count in region_counts.items():
            repartition_region[str(r)] = int(count)

    # 3. Taux de respect du délai de 60 jours
    depot_col = None
    reponse_col = None
    echeance_col = None
    for c in df_historique.columns:
        c_lower = c.lower()
        if "dépôt" in c_lower or "depot" in c_lower or "dpt" in c_lower:
            depot_col = c
        elif "réponse" in c_lower or "reponse" in c_lower or "rponse" in c_lower:
            if "attendue" in c_lower or "echeance" in c_lower:
                echeance_col = c
            else:
                reponse_col = c

    taux_respect = 100.0
    periods = []
    rates = []
    
    if reponse_col and (echeance_col or depot_col):
        df_temp = df_historique.copy()
        df_temp[reponse_col] = pd.to_datetime(df_temp[reponse_col], errors='coerce')
        if echeance_col:
            df_temp[echeance_col] = pd.to_datetime(df_temp[echeance_col], errors='coerce')
        else:
            df_temp[depot_col] = pd.to_datetime(df_temp[depot_col], errors='coerce')
            df_temp['echeance_calc'] = df_temp[depot_col] + pd.to_timedelta(60, unit='D')
            echeance_col = 'echeance_calc'
            
        # Filtrer uniquement les lignes ayant reçu une réponse
        repondues_df = df_temp[df_temp[reponse_col].notna()].copy()
        total_repondues = len(repondues_df)
        
        if total_repondues > 0:
            respectees = repondues_df[repondues_df[reponse_col] <= repondues_df[echeance_col]]
            taux_respect = (len(respectees) / total_repondues) * 100
            
            # Évolution temporelle (regroupement par mois de dépôt)
            if depot_col:
                repondues_df[depot_col] = pd.to_datetime(repondues_df[depot_col], errors='coerce')
                repondues_df = repondues_df.dropna(subset=[depot_col])
                if len(repondues_df) > 0:
                    repondues_df['periode'] = repondues_df[depot_col].dt.to_period('M')
                    for period, group in sorted(repondues_df.groupby('periode')):
                        total_g = len(group)
                        resp_g = len(group[group[reponse_col] <= group[echeance_col]])
                        periods.append(str(period))
                        rates.append((resp_g / total_g) * 100)

    # 4. Taux de concordance (Validé vs Corrigé par le responsable)
    concordance_rate = None
    dec_col = None
    prop_col = None
    for c in df_historique.columns:
        if "décision" in c.lower() or "decision" in c.lower() or "dcision" in c.lower():
            dec_col = c
        elif "proposée" in c.lower() or "proposee" in c.lower() or "propose" in c.lower():
            prop_col = c
            
    if dec_col and prop_col:
        concordants = 0
        total_eval = len(df_historique)
        for _, row in df_historique.iterrows():
            dec_val = str(row[dec_col]).strip()
            prop_val = str(row[prop_col]).strip()
            
            # Si c'est une correction, on extrait le nom de la direction pour comparer
            if dec_val.startswith("Corriger : "):
                dec_val = dec_val.replace("Corriger : ", "").strip()
                
            if "valid" in dec_val.lower() or dec_val == prop_val:
                concordants += 1
        if total_eval > 0:
            concordance_rate = (concordants / total_eval) * 100

    # 5. Score de confiance moyen du modèle
    conf_col = None
    for c in df_historique.columns:
        if "confiance" in c.lower() or "score" in c.lower():
            if c != dec_col:
                conf_col = c
                break
                
    score_moyen = 0.0
    if conf_col:
        score_moyen = float(pd.to_numeric(df_historique[conf_col], errors='coerce').mean())
        if pd.isna(score_moyen):
            score_moyen = 0.0

    return {
        "total_demandes": total_demandes,
        "repartition_direction": repartition_direction,
        "repartition_region": repartition_region,
        "taux_respect": taux_respect,
        "taux_concordance": concordance_rate,
        "score_confiance_moyen": score_moyen,
        "evolution_respect": {"periodes": periods, "taux": rates}
    }

def generer_graphiques(resultats: dict) -> tuple:
    """
    Génère les graphiques matplotlib requis pour le rapport d'activité.
    
    Retourne (fig_direction, fig_evolution).
    """
    # 1. Graphique en barres de la répartition par direction
    fig_dir, ax_dir = plt.subplots(figsize=(8, 4))
    rep_dir = resultats.get("repartition_direction", {})
    
    if rep_dir:
        directions = list(rep_dir.keys())
        nombres = [val["nombre"] for val in rep_dir.values()]
        
        # Thème couleur premium
        colors = ['#1E3A8A', '#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE', '#DBEAFE', '#2563EB', '#1D4ED8']
        bars = ax_dir.bar(directions, nombres, color=colors[:len(directions)])
        
        ax_dir.set_ylabel("Nombre de demandes", fontsize=10, fontweight='bold')
        ax_dir.set_title("Répartition des demandes par direction", fontsize=12, fontweight='bold', pad=15)
        ax_dir.tick_params(axis='x', rotation=45, labelsize=9)
        ax_dir.spines['top'].set_visible(False)
        ax_dir.spines['right'].set_visible(False)
        
        # Ajouter les étiquettes de valeurs
        for bar in bars:
            height = bar.get_height()
            ax_dir.annotate(f'{height}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=8, fontweight='bold')
        plt.tight_layout()
    else:
        ax_dir.text(0.5, 0.5, "Aucune donnée de direction disponible", ha='center', va='center')
        
    # 2. Graphique en courbe de l'évolution du taux de respect
    fig_time, ax_time = plt.subplots(figsize=(8, 4))
    evol = resultats.get("evolution_respect", {})
    
    if evol and evol.get("periodes"):
        periodes = evol["periodes"]
        taux = evol["taux"]
        
        ax_time.plot(periodes, taux, marker='o', color='#EF4444', linewidth=2.5, label="Taux de respect")
        ax_time.set_ylabel("Taux de respect (%)", fontsize=10, fontweight='bold')
        ax_time.set_ylim(-5, 105)
        ax_time.set_title("Évolution du taux de respect du délai de 60 jours", fontsize=12, fontweight='bold', pad=15)
        ax_time.grid(True, linestyle='--', alpha=0.5)
        ax_time.spines['top'].set_visible(False)
        ax_time.spines['right'].set_visible(False)
        
        for i, val in enumerate(taux):
            ax_time.annotate(f'{val:.1f}%', (periodes[i], taux[i]), 
                             textcoords="offset points", xytext=(0, 10), 
                             ha='center', fontsize=8, fontweight='bold', color='#B91C1C')
        plt.tight_layout()
    else:
        ax_time.text(0.5, 0.5, "Données temporelles de réponse insuffisantes\n(requiert des dates de réponse)", 
                     ha='center', va='center', fontsize=10, color='gray')
        plt.tight_layout()
        
    return fig_dir, fig_time
