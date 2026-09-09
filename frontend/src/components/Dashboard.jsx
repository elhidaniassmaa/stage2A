import React, { useState, useEffect } from 'react';
import { Upload, RefreshCw, CheckCircle2 } from 'lucide-react';

const API_URL = "http://localhost:8000/api";

export default function Dashboard({ user }) {
  const [stats, setStats] = useState({ total_demandes: 0, demandes_traitees: 0, en_attente: 0, urgent_depasse: 0 });
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [messageUpload, setMessageUpload] = useState('');
  const [uploadProgress, setUploadProgress] = useState({
    en_cours: false,
    total: 0,
    traites: 0,
    pourcentage: 0,
    etape: '',
    message: ''
  });

  const loadStats = async () => {
    try {
      const statsRes = await fetch(`${API_URL}/dashboard/stats`);
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
    } catch (error) {
      console.error("Erreur de chargement :", error);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
    setMessageUpload('');
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setMessageUpload('');
    setUploadProgress({
      en_cours: true,
      total: 0,
      traites: 0,
      pourcentage: 0,
      etape: "Initialisation de l'importation...",
      message: ''
    });

    // Polling du statut d'importation
    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/demandes/upload-status`);
        if (res.ok) {
          const statusData = await res.json();
          setUploadProgress(statusData);
        }
      } catch (err) {
        console.error("Erreur suivi progression d'upload :", err);
      }
    }, 300);

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
      setUploadProgress(prev => ({
        ...prev,
        en_cours: false,
        pourcentage: 100,
        etape: 'Traitement terminé avec succès !'
      }));
      loadStats();
    } catch (error) {
      setMessageUpload(`❌ ${error.message}`);
      setUploadProgress(prev => ({
        ...prev,
        en_cours: false,
        etape: "Échec de l'importation"
      }));
    } finally {
      clearInterval(pollInterval);
      setUploading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-title-area">
          <h1>Tableau de Bord des Demandes</h1>
          <p>Supervisez et routez automatiquement les réclamations et requêtes des citoyens.</p>
        </div>
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

      {/* Zone d'Importation Excel */}
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
                borderRadius: 'var(--radius-sm, 6px)',
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

        {/* Barre de Progression & Taux de Progression */}
        {(uploading || uploadProgress.en_cours || uploadProgress.pourcentage > 0) && (
          <div style={{ 
            marginTop: '20px', 
            padding: '16px 20px', 
            backgroundColor: '#F8FAFC', 
            borderRadius: '8px', 
            border: '1px solid #E2E8F0',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {uploadProgress.en_cours || uploading ? (
                  <RefreshCw size={16} className="animate-spin" style={{ color: 'var(--primary-color)' }} />
                ) : (
                  <CheckCircle2 size={16} style={{ color: 'var(--success-color)' }} />
                )}
                <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--secondary-color)' }}>
                  {uploadProgress.etape || "Traitement IA des demandes en cours..."}
                </span>
              </div>
              <span style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--primary-color)' }}>
                {uploadProgress.pourcentage}%
              </span>
            </div>

            {/* Visual Progress Bar */}
            <div style={{
              width: '100%',
              height: '10px',
              backgroundColor: '#E2E8F0',
              borderRadius: '5px',
              overflow: 'hidden',
              marginTop: '6px',
              marginBottom: '8px'
            }}>
              <div style={{
                height: '100%',
                width: `${uploadProgress.pourcentage}%`,
                background: uploadProgress.pourcentage === 100 
                  ? 'linear-gradient(90deg, #059669 0%, #10B981 100%)' 
                  : 'linear-gradient(90deg, #1E40AF 0%, #3B82F6 100%)',
                borderRadius: '5px',
                transition: 'width 0.3s ease-in-out'
              }} />
            </div>

            {/* Info / Taux de progression */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              <span>Taux de progression : <strong style={{ color: 'var(--secondary-color)' }}>{uploadProgress.pourcentage}%</strong></span>
              {uploadProgress.total > 0 && (
                <span>Demandes traitées : <strong style={{ color: 'var(--secondary-color)' }}>{uploadProgress.traites} / {uploadProgress.total}</strong></span>
              )}
            </div>
          </div>
        )}

        {messageUpload && (
          <div style={{ 
            marginTop: '16px', 
            fontSize: '0.85rem', 
            fontWeight: 600, 
            color: messageUpload.startsWith('❌') ? 'var(--danger-color)' : 'var(--success-color)' 
          }}>
            {messageUpload}
          </div>
        )}
      </div>
    </div>
  );
}
