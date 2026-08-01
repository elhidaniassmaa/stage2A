import React, { useState, useEffect } from 'react';
import { Upload, Download, AlertTriangle, CheckCircle, Clock, Search, RefreshCw, FileText } from 'lucide-react';

const API_URL = "http://localhost:8000/api";
const DIRECTIONS = ["DSI", "DSPCT", "DAAJJ", "DMM", "DTR", "DJAC", "Cabinet du Ministère", "Non concerné"];

export default function Dashboard({ user, demandeCibleeId, clearDemandeCiblee }) {
  const [stats, setStats] = useState({ total_demandes: 0, demandes_traitees: 0, en_attente: 0, urgent_depasse: 0 });
  const [demandes, setDemandes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [filterStatut, setFilterStatut] = useState('Toutes');
  const [filterUrgent, setFilterUrgent] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [messageUpload, setMessageUpload] = useState('');
  const [highlightedId, setHighlightedId] = useState(null);

  // Charger les stats et les demandes au démarrage et lors du changement de filtres
  const loadData = async () => {
    setLoading(true);
    try {
      // 1. Charger les KPIs
      const statsRes = await fetch(`${API_URL}/dashboard/stats`);
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      // 2. Charger les demandes
      let url = `${API_URL}/demandes?`;
      if (filterStatut !== 'Toutes') url += `statut=${filterStatut}&`;
      if (filterUrgent) url += `urgent=true&`;
      if (searchQuery) url += `q=${encodeURIComponent(searchQuery)}&`;

      const demandesRes = await fetch(url);
      if (demandesRes.ok) {
        const demandesData = await demandesRes.json();
        setDemandes(demandesData);
      }
    } catch (error) {
      console.error("Erreur de chargement :", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [filterStatut, filterUrgent, searchQuery]);

  useEffect(() => {
    if (!demandeCibleeId || demandes.length === 0) return;
    const el = document.getElementById(`demande-${demandeCibleeId}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setHighlightedId(demandeCibleeId);
      const timer = setTimeout(() => {
        setHighlightedId(null);
        if (clearDemandeCiblee) clearDemandeCiblee();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [demandeCibleeId, demandes]);

  // Gérer l'upload du fichier Excel
  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
    setMessageUpload('');
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setMessageUpload('');
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`${API_URL}/demandes/upload?user_name=${encodeURIComponent(user.nom_complet)}&user_role=${encodeURIComponent(user.role)}`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Erreur d'importation.");
      }

      const resData = await response.json();
      const icon = resData.importees === 0 && resData.doublons_ignores > 0 ? '⚠️' : '✅';
      setMessageUpload(`${icon} ${resData.message}`);
      setSelectedFile(null);
      // Recharger les données
      loadData();
    } catch (error) {
      setMessageUpload(`❌ ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  // Gérer le changement de décision (direction corrigée)
  const handleDecisionChange = async (id, decision) => {
    try {
      const response = await fetch(`${API_URL}/demandes/${id}/decision?user_name=${encodeURIComponent(user.nom_complet)}&user_role=${encodeURIComponent(user.role)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision_responsable: decision })
      });

      if (response.ok) {
        loadData();
      }
    } catch (error) {
      console.error("Erreur lors du changement de direction :", error);
    }
  };

  // Gérer la validation finale (marquer comme répondue)
  const handleMarkAsAnswered = async (id) => {
    try {
      const response = await fetch(`${API_URL}/demandes/${id}/statut?user_name=${encodeURIComponent(user.nom_complet)}&user_role=${encodeURIComponent(user.role)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ statut_demande: 'Répondue' })
      });

      if (response.ok) {
        loadData();
        window.dispatchEvent(new Event('gedec:refresh-notifications'));
      }
    } catch (error) {
      console.error("Erreur lors de la mise à jour du statut :", error);
    }
  };

  // Gérer l'export Excel
  const handleExport = () => {
    window.open(`${API_URL}/demandes/export`, '_blank');
  };

  // Formater les dates
  const formatDate = (dateStr) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('fr-FR');
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-title-area">
          <h1>Tableau de Bord des Demandes</h1>
          <p>Supervisez et routez automatiquement les réclamations et requêtes des citoyens.</p>
        </div>
        <button className="btn btn-primary" onClick={handleExport}>
          <Download size={16} />
          Exporter le suivi (Excel)
        </button>
      </div>

      {/* KPIs Grid */}
      <div className="kpis-grid">
        <div className="kpi-card">
          <span className="kpi-title">Total Demandes</span>
          <div className="kpi-val-row">
            <span className="kpi-value">{stats.total_demandes}</span>
            <span className="kpi-badge kpi-badge-blue">Total</span>
          </div>
          <span className="kpi-label">Dossiers enregistrés en base</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-title">Demandes Traitées</span>
          <div className="kpi-val-row">
            <span className="kpi-value" style={{ color: 'var(--success-color)' }}>{stats.demandes_traitees}</span>
            <span className="kpi-badge kpi-badge-green">Répondues</span>
          </div>
          <span className="kpi-label">Marquées comme traitées</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-title">En Attente</span>
          <div className="kpi-val-row">
            <span className="kpi-value" style={{ color: 'var(--primary-color)' }}>{stats.en_attente}</span>
            <span className="kpi-badge" style={{ backgroundColor: '#DBEAFE', color: 'var(--primary-color)' }}>À traiter</span>
          </div>
          <span className="kpi-label">Nouveaux dossiers non résolus</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-title">Urgent / Dépassé</span>
          <div className="kpi-val-row">
            <span className="kpi-value" style={{ color: 'var(--danger-color)' }}>{stats.urgent_depasse}</span>
            <span className="kpi-badge kpi-badge-red">Prioritaires</span>
          </div>
          <span className="kpi-label">Échéance courte (≤ 5j ou dépassée)</span>
        </div>
      </div>

      {/* Upload Zone */}
      <div className="table-container" style={{ padding: '24px', marginBottom: '24px' }}>
        <h3 style={{ fontFamily: 'Outfit', fontWeight: 700, color: 'var(--secondary-color)', marginBottom: '12px' }}>
           Importer de nouvelles demandes citoyennes
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          Sélectionnez un fichier Excel (.xlsx) contenant les réclamations à soumettre au pipeline de modération, classification et génération d'argumentaires légaux.
        </p>

        <form onSubmit={handleUpload} style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', display: 'flex', flex: 1, minWidth: '250px' }}>
            <input 
              type="file" 
              accept=".xlsx" 
              onChange={handleFileChange}
              id="excel-file-input"
              style={{ display: 'none' }}
            />
            <label 
              htmlFor="excel-file-input"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                border: '1px dashed var(--border-color)',
                backgroundColor: '#F8FAFC',
                padding: '12px 20px',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                width: '100%',
                fontSize: '0.85rem',
                fontWeight: 500,
                color: 'var(--text-secondary)'
              }}
            >
              <Upload size={18} />
              {selectedFile ? selectedFile.name : "Glisser ou cliquer pour charger le fichier .xlsx"}
            </label>
          </div>
          
          <button 
            type="submit" 
            className="btn btn-primary"
            disabled={!selectedFile || uploading}
            style={{ height: '45px' }}
          >
            {uploading ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                Traitement en cours...
              </>
            ) : "Lancer le traitement IA"}
          </button>
        </form>

        {messageUpload && (
          <div style={{ 
            marginTop: '12px', 
            fontSize: '0.85rem', 
            fontWeight: 600, 
            color: messageUpload.startsWith('❌') ? 'var(--danger-color)' : 'var(--success-color)' 
          }}>
            {messageUpload}
          </div>
        )}
      </div>

      {/* Detailed Treatment Section */}
      <h2 style={{ fontFamily: 'Outfit', fontWeight: 700, color: 'var(--secondary-color)', marginBottom: '16px' }}>
        Traitement détaillé des réclamations
      </h2>

      {/* Filter and Search bar */}
      <div className="filters-bar">
        <div className="filters-left">
          <div className="search-box" style={{ width: '100%' }}>
            <Search size={18} />
            <input 
              type="text" 
              placeholder="Rechercher par message ou direction..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        <div className="filters-right">
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Statut :
          </span>
          <div style={{ display: 'flex', gap: '6px' }}>
            {['Toutes', 'En attente', 'Répondue'].map(st => (
              <button
                key={st}
                onClick={() => setFilterStatut(st)}
                className={`btn ${filterStatut === st ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '6px 12px', fontSize: '0.8rem' }}
              >
                {st}
              </button>
            ))}
          </div>
          
          <div style={{ borderLeft: '1px solid var(--border-color)', height: '24px', margin: '0 8px' }}></div>

          <label className="checkbox-label">
            <input 
              type="checkbox" 
              checked={filterUrgent}
              onChange={(e) => setFilterUrgent(e.target.checked)}
            />
            <span>Dossiers urgents uniquement</span>
          </label>
        </div>
      </div>

      {/* Requests List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)', fontWeight: 600 }}>
          <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 10px auto' }} />
          Chargement des réclamations...
        </div>
      ) : demandes.length === 0 ? (
        <div className="table-container" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
          Aucune réclamation ne correspond aux critères de recherche.
        </div>
      ) : (
        demandes.map((dem) => {
          // Déterminer la classe et l'alerte
          let alertBadgeClass = "badge-green";
          let alertLabel = "Délais confortables";
          if (dem.type_alerte === "depasse") {
            alertBadgeClass = "badge-red";
            alertLabel = "ÉCHÉANCE DÉPASSÉE";
          } else if (dem.type_alerte === "prioritaire") {
            alertBadgeClass = "badge-orange";
            alertLabel = "PRIORITAIRE (≤ 5 jours)";
          } else if (dem.type_alerte === "rappel") {
            alertBadgeClass = "badge-blue";
            alertLabel = "Rappel (6-15 jours)";
          }

          // Déduire le label de confiance
          const confianceLabel = dem.confiance_faible === 1 ? "Confiance Faible ⚠️" : "Confiance Élevée ✅";
          const colorConfiance = dem.confiance_faible === 1 ? "#C2410C" : "#15803D";

          return (
            <div key={dem.id} id={`demande-${dem.id}`} className="demande-card" style={dem.id === highlightedId ? { outline: '3px solid #F59E0B', outlineOffset: '2px' } : {}}>
              <div className="demande-row">
                {/* Message & Moderation */}
                <div className="demande-message-col">
                  <div>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                      DEMANDE #GEDEC-2026-{String(dem.id).padStart(3, '0')} — {dem.prenom} {dem.nom || 'Non renseigné'} (Région: {dem.region})
                    </span>
                    <p className="demande-message-text">
                      "{dem.message_original}"
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {dem.contenu_valide === 1 ? (
                      <span className="badge badge-green">
                        <CheckCircle size={12} /> Modération OK
                      </span>
                    ) : (
                      <span className="badge badge-red">
                        <AlertTriangle size={12} /> Contenu Suspect / Censuré
                      </span>
                    )}
                    {dem.mot_interdit_detecte === 1 ? (
                      <span className="badge badge-red">
                        <AlertTriangle size={12} /> Mot interdit détecté
                      </span>
                    ) : (
                      <span className="badge badge-green">
                        <CheckCircle size={12} /> Aucun mot interdit
                      </span>
                    )}
                    <span className="badge" style={{ backgroundColor: '#F1F5F9', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}>
                      Echéance : {formatDate(dem.date_echeance)}
                    </span>
                  </div>
                </div>

                {/* AI Routing & Legal justifications */}
                <div className="demande-info-col">
                  <div>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                      Direction proposée par l'IA :
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                      <code style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--primary-color)', backgroundColor: 'var(--primary-light)', padding: '2px 8px', borderRadius: '4px' }}>
                        {dem.direction_predite}
                      </code>
                      <span style={{ color: colorConfiance, fontSize: '0.8rem', fontWeight: 600 }}>
                        {confianceLabel} ({Math.round(dem.score_confiance * 100)}%)
                      </span>
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                      Alerte délai :
                    </span>
                    <span className={`badge ${alertBadgeClass}`}>
                      <Clock size={12} /> {alertLabel}
                    </span>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '2px' }}>
                      Justification réglementaire :
                    </span>
                    <p style={{ fontSize: '0.8rem', fontStyle: 'italic', color: 'var(--text-primary)', borderLeft: '2px solid var(--primary-color)', paddingLeft: '8px', lineHeight: 1.4 }}>
                      {dem.argumentaire}
                    </p>
                  </div>
                </div>

                {/* Responsible Actions */}
                <div className="demande-action-col">
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Action du responsable :</label>
                    <select
                      className="filter-select"
                      style={{ width: '100%', padding: '8px 10px', fontSize: '0.8rem' }}
                      value={dem.decision_responsable}
                      onChange={(e) => handleDecisionChange(dem.id, e.target.value)}
                    >
                      <option value="Validé">Validé ({dem.direction_predite})</option>
                      {DIRECTIONS.map(dir => (
                        <option key={dir} value={`Corriger : ${dir}`}>
                          Corriger : {dir}
                        </option>
                      ))}
                    </select>
                  </div>

                  {dem.statut_demande === 'Répondue' ? (
                    <div style={{
                      textAlign: 'center',
                      color: 'var(--success-color)',
                      fontWeight: 700,
                      fontSize: '0.85rem',
                      padding: '8px',
                      backgroundColor: 'var(--success-bg)',
                      border: '1px solid var(--success-border)',
                      borderRadius: 'var(--radius-sm)'
                    }}>
                      ✅ RÉPONDUE
                    </div>
                  ) : (
                    <button
                      className="btn btn-secondary"
                      style={{ width: '100%', borderColor: 'var(--success-color)', color: 'var(--success-color)', fontWeight: 700 }}
                      onClick={() => handleMarkAsAnswered(dem.id)}
                    >
                      Marquer comme répondue
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
