import React, { useState, useEffect } from 'react';
import { Search, Download, Printer, RefreshCw, Calendar } from 'lucide-react';

const API_URL = "http://localhost:8000/api";

const ACTIONS = [
  "Toutes les actions",
  "Correction direction",
  "Importation massive",
  "Consultation Rapport",
  "Alerte de seuil",
  "Modif. Mots Interdits",
  "Validation Demande",
  "Création Compte",
  "Modification Compte",
  "Modif. Accès",
  "Ajout Article",
  "Modif. Article",
  "Suppr. Article",
  "Connexion",
  "Déconnexion"
];

export default function Historique() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Filtres
  const [filterAction, setFilterAction] = useState('Toutes les actions');
  const [searchUser, setSearchUser] = useState('');
  const [dateDebut, setDateDebut] = useState('');
  const [dateFin, setDateFin] = useState('');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [logsPerPage, setLogsPerPage] = useState(15);

  const loadLogs = async () => {
    setLoading(true);
    try {
      let url = `${API_URL}/logs?`;
      if (filterAction !== 'Toutes les actions') url += `action_type=${encodeURIComponent(filterAction)}&`;
      if (searchUser) url += `q=${encodeURIComponent(searchUser)}&`;

      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        setLogs(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [filterAction, searchQueryDebounced(searchUser)]);

  // Simple debounce helper
  function searchQueryDebounced(val) {
    return val;
  }

  // Filtrer localement par date en plus si fourni
  const filteredLogs = logs.filter(log => {
    if (!dateDebut && !dateFin) return true;
    
    try {
      // Formater la date du log "dd/mm/yyyy hh:mm:ss" en objet Date
      const parts = log.date_heure.split(' ')[0].split('/');
      const logDate = new Date(parts[2], parts[1] - 1, parts[0]);
      
      if (dateDebut) {
        const start = new Date(dateDebut);
        if (logDate < start) return false;
      }
      
      if (dateFin) {
        const end = new Date(dateFin);
        if (logDate > end) return false;
      }
    } catch (e) {
      return true;
    }
    return true;
  });

  const resetFilters = () => {
    setFilterAction('Toutes les actions');
    setSearchUser('');
    setDateDebut('');
    setDateFin('');
    setCurrentPage(1);
    loadLogs();
  };

  // Exporter en CSV
  const handleExportCSV = () => {
    window.open(`${API_URL}/logs/export`, '_blank');
  };

  // Imprimer les logs
  const handlePrint = () => {
    window.print();
  };

  // Initiales de l'utilisateur
  const getInitials = (name) => {
    if (!name) return "SA";
    const cleanName = name.replace('.', '').trim();
    const parts = cleanName.split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  // Obtenir le style de badge pour le rôle
  const getRoleBadgeClass = (role) => {
    switch (role.toUpperCase()) {
      case 'ADMINISTRATEUR':
        return 'badge-red';
      case 'CHEF DE DIVISION':
        return 'badge-blue';
      case 'SYSTEME':
      case 'SYSTEM':
        return 'badge-orange';
      case 'RESPONSABLE':
        return 'badge-green';
      default:
        return 'badge-gray';
    }
  };

  // Calcul pagination
  const indexOfLastLog = currentPage * logsPerPage;
  const indexOfFirstLog = indexOfLastLog - logsPerPage;
  const currentLogs = filteredLogs.slice(indexOfFirstLog, indexOfLastLog);
  const totalPages = Math.ceil(filteredLogs.length / logsPerPage);

  return (
    <div>
      <div className="page-header">
        <div className="page-title-area">
          <h1>Journal d'activité</h1>
          <p>Traçabilité de toutes les actions du système en temps réel.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={handleExportCSV}>
            <Download size={16} />
            Exporter le journal (CSV)
          </button>
          <button className="btn btn-primary" onClick={handlePrint}>
            <Printer size={16} />
            Imprimer
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="filters-bar" style={{ gap: '12px' }}>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', flex: 1 }}>
          <div className="form-group" style={{ marginBottom: 0, flex: 1, minWidth: '150px' }}>
            <label className="form-label" style={{ fontSize: '0.7rem' }}>Type d'action</label>
            <select
              className="filter-select"
              style={{ width: '100%', padding: '8px 10px', fontSize: '0.8rem' }}
              value={filterAction}
              onChange={(e) => { setFilterAction(e.target.value); setCurrentPage(1); }}
            >
              {ACTIONS.map(act => (
                <option key={act} value={act}>{act}</option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: 0, flex: 1, minWidth: '150px' }}>
            <label className="form-label" style={{ fontSize: '0.7rem' }}>Utilisateur</label>
            <div className="search-box" style={{ width: '100%' }}>
              <Search size={14} style={{ left: '8px' }} />
              <input 
                type="text" 
                placeholder="Rechercher..." 
                className="filter-input"
                style={{ paddingLeft: '28px', paddingY: '8px', fontSize: '0.8rem' }}
                value={searchUser}
                onChange={(e) => { setSearchUser(e.target.value); setCurrentPage(1); }}
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: 0, flex: 1.5, minWidth: '220px' }}>
            <label className="form-label" style={{ fontSize: '0.7rem' }}>Plage de dates</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <input 
                type="date" 
                className="filter-input"
                style={{ padding: '6px 8px', fontSize: '0.8rem' }}
                value={dateDebut}
                onChange={(e) => { setDateDebut(e.target.value); setCurrentPage(1); }}
              />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>au</span>
              <input 
                type="date" 
                className="filter-input"
                style={{ padding: '6px 8px', fontSize: '0.8rem' }}
                value={dateFin}
                onChange={(e) => { setDateFin(e.target.value); setCurrentPage(1); }}
              />
            </div>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px' }}>
            <button 
              className="btn btn-secondary" 
              style={{ padding: '8px 12px', height: '36px' }}
              onClick={resetFilters}
              title="Réinitialiser les filtres"
            >
              <RefreshCw size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Logs Table */}
      <div className="table-container">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
            Chargement du journal d'activité...
          </div>
        ) : currentLogs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
            Aucun log d'activité disponible.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '180px' }}>Date/Heure</th>
                <th style={{ width: '180px' }}>Utilisateur</th>
                <th style={{ width: '160px' }}>Rôle</th>
                <th style={{ width: '180px' }}>Action</th>
                <th style={{ width: '220px' }}>Élément concerné</th>
                <th>Détail</th>
              </tr>
            </thead>
            <tbody>
              {currentLogs.map((log) => (
                <tr key={log.id}>
                  <td style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
                    {log.date_heure}
                  </td>
                  <td>
                    <div className="avatar-cell">
                      <div className="cell-initials" style={{ width: '30px', height: '30px', fontSize: '0.75rem' }}>
                        {getInitials(log.utilisateur)}
                      </div>
                      <span className="cell-title" style={{ fontSize: '0.85rem' }}>{log.utilisateur}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${getRoleBadgeClass(log.role)}`}>
                      {log.role}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600, color: 'var(--primary-color)' }}>
                    {log.action}
                  </td>
                  <td style={{ fontWeight: 600, color: '#334155' }}>
                    {log.element_concerne}
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    {log.detail}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination & Config */}
      {filteredLogs.length > 0 && (
        <div className="pagination">
          <span className="pagination-info">
            Affichage de {indexOfFirstLog + 1} à {Math.min(indexOfLastLog, filteredLogs.length)} sur {filteredLogs.length} logs
          </span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Lignes par page :</span>
              <select
                className="filter-select"
                style={{ padding: '4px 8px', minWidth: '60px', fontSize: '0.8rem' }}
                value={logsPerPage}
                onChange={(e) => { setLogsPerPage(Number(e.target.value)); setCurrentPage(1); }}
              >
                <option value="10">10</option>
                <option value="15">15</option>
                <option value="30">30</option>
                <option value="50">50</option>
              </select>
            </div>

            <div className="pagination-controls">
              <button 
                className="page-btn" 
                onClick={() => setCurrentPage(currentPage - 1)}
                disabled={currentPage === 1}
              >
                &lt;
              </button>
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                // Montrer les pages proches
                return (
                  <button
                    key={i + 1}
                    className={`page-btn ${currentPage === i + 1 ? 'active' : ''}`}
                    onClick={() => setCurrentPage(i + 1)}
                  >
                    {i + 1}
                  </button>
                );
              })}
              {totalPages > 5 && <span style={{ padding: '6px' }}>...</span>}
              {totalPages > 5 && (
                <button
                  className={`page-btn ${currentPage === totalPages ? 'active' : ''}`}
                  onClick={() => setCurrentPage(totalPages)}
                >
                  {totalPages}
                </button>
              )}
              <button 
                className="page-btn" 
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                &gt;
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
