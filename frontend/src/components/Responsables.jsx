import React, { useState, useEffect } from 'react';
import { Plus, Search, Edit2, Ban, CheckCircle, Download, X, HelpCircle, Users } from 'lucide-react';

const API_URL = "http://localhost:8000/api";
const DIRECTIONS = ["DTR", "DSPCT", "DAAJJ", "DMM", "DJAC", "DSI", "Cabinet du Ministère"];
const DIRECTION_LABELS = {
  "DTR": "Transport Routier",
  "DSPCT": "Logistique & Ports",
  "DAAJJ": "Affaires Générales",
  "DMM": "Marine Marchande",
  "DJAC": "Aérien & Civil",
  "DSI": "DSI (Systèmes d'Information)",
  "Cabinet du Ministère": "Cabinet du Ministère"
};

export default function Responsables({ user }) {
  const [responsables, setResponsables] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterDirection, setFilterDirection] = useState('Toutes');
  
  // États pour le modal d'ajout/modification
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [nomComplet, setNomComplet] = useState('');
  const [email, setEmail] = useState('');
  const [direction, setDirection] = useState('DTR');
  const [role, setRole] = useState('Responsable');
  const [statut, setStatut] = useState('ACTIF');
  const [errorModal, setErrorModal] = useState('');

  // Charger les responsables
  const loadResponsables = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/responsables`);
      if (response.ok) {
        const data = await response.json();
        setResponsables(data);
      }
    } catch (e) {
      console.error("Erreur de chargement des responsables :", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadResponsables();
  }, []);

  // Ouvrir le modal pour ajouter
  const handleOpenAdd = () => {
    setEditingId(null);
    setNomComplet('');
    setEmail('');
    setDirection('DTR');
    setRole('Responsable');
    setStatut('ACTIF');
    setErrorModal('');
    setIsModalOpen(true);
  };

  // Ouvrir le modal pour éditer
  const handleOpenEdit = (res) => {
    setEditingId(res.id);
    setNomComplet(res.nom_complet);
    setEmail(res.email);
    // Trouver le code_direction à partir du label s'il n'est pas déjà un code
    let codeDir = res.direction;
    for (const [k, v] of Object.entries(DIRECTION_LABELS)) {
      if (v === res.direction || k === res.direction) {
        codeDir = k;
        break;
      }
    }
    setDirection(codeDir);
    setRole(res.role);
    setStatut(res.statut);
    setErrorModal('');
    setIsModalOpen(true);
  };

  // Soumettre le modal (Ajouter/Modifier)
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!nomComplet || !email) {
      setErrorModal('Veuillez remplir tous les champs.');
      return;
    }

    const payload = {
      email,
      nom_complet: nomComplet,
      direction: DIRECTION_LABELS[direction] || direction,
      role,
      statut
    };

    try {
      let response;
      if (editingId) {
        // Mode modification
        response = await fetch(`${API_URL}/responsables/${editingId}?user_name=${encodeURIComponent(user.nom_complet)}&user_role=${encodeURIComponent(user.role)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        // Mode création
        response = await fetch(`${API_URL}/responsables?user_name=${encodeURIComponent(user.nom_complet)}&user_role=${encodeURIComponent(user.role)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Erreur lors de la sauvegarde.');
      }

      setIsModalOpen(false);
      loadResponsables();
    } catch (err) {
      setErrorModal(err.message);
    }
  };

  // Activer/Désactiver le statut
  const handleToggleStatus = async (id) => {
    try {
      const response = await fetch(`${API_URL}/responsables/${id}/toggle-status?user_name=${encodeURIComponent(user.nom_complet)}&user_role=${encodeURIComponent(user.role)}`, {
        method: 'POST'
      });
      if (response.ok) {
        loadResponsables();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Filtrer les responsables
  const filteredResponsables = responsables.filter(res => {
    const matchesSearch = 
      res.nom_complet.toLowerCase().includes(searchQuery.toLowerCase()) ||
      res.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      res.direction.toLowerCase().includes(searchQuery.toLowerCase());
      
    if (filterDirection === 'Toutes') return matchesSearch;
    
    // Vérifier si le filtre correspond au label ou au code
    const targetLabel = DIRECTION_LABELS[filterDirection] || filterDirection;
    return matchesSearch && (res.direction === targetLabel || res.direction === filterDirection);
  });

  // Obtenir les initiales du nom
  const getInitials = (name) => {
    if (!name) return "AB";
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  // KPIs
  const totalCount = responsables.length;
  const activeCount = responsables.filter(r => r.statut === 'ACTIF').length;
  const treatedAverage = 142; // KPI fixe de la maquette
  const reactivityRate = 94; // KPI fixe de la maquette

  return (
    <div>
      <div className="page-header">
        <div className="page-title-area">
          <h1>Gestion des Responsables</h1>
          <p>Administrez les accès et supervisez les performances des gestionnaires par direction.</p>
        </div>
        <button className="btn btn-primary" onClick={handleOpenAdd}>
          <Plus size={16} />
          Ajouter un responsable
        </button>
      </div>

      {/* KPIs Grid */}
      <div className="kpis-grid">
        <div className="kpi-card">
          <span className="kpi-title">Total Responsables</span>
          <div className="kpi-val-row">
            <span className="kpi-value">{totalCount}</span>
            <span className="kpi-badge kpi-badge-blue">+2 ce mois</span>
          </div>
          <span className="kpi-label">Utilisateurs enregistrés</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-title">Actifs en ligne</span>
          <div className="kpi-val-row">
            <span className="kpi-value" style={{ color: 'var(--success-color)' }}>{activeCount}</span>
            <span className="kpi-badge kpi-badge-green">Temps réel</span>
          </div>
          <span className="kpi-label">Utilisateurs avec accès actif</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-title">Moyenne Traitement</span>
          <div className="kpi-val-row">
            <span className="kpi-value">{treatedAverage}</span>
            <span className="kpi-badge" style={{ backgroundColor: '#F3F4F6', color: 'var(--text-secondary)' }}>KPI</span>
          </div>
          <span className="kpi-label">Demandes traitées par mois</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-title">Taux de Réactivité</span>
          <div className="kpi-val-row">
            <span className="kpi-value" style={{ color: 'var(--primary-color)' }}>{reactivityRate}%</span>
            <span className="kpi-badge kpi-badge-blue">Cible: 90%</span>
          </div>
          <span className="kpi-label">Respect du délai légal</span>
        </div>
      </div>

      {/* Filter and Search */}
      <div className="filters-bar">
        <div className="filters-left">
          <div className="search-box" style={{ width: '100%' }}>
            <Search size={18} />
            <input 
              type="text" 
              placeholder="Rechercher par nom, email ou direction..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        <div className="filters-right">
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Direction :
          </span>
          <select
            className="filter-select"
            value={filterDirection}
            onChange={(e) => setFilterDirection(e.target.value)}
          >
            <option value="Toutes">Toutes les directions</option>
            {DIRECTIONS.map(dir => (
              <option key={dir} value={dir}>{DIRECTION_LABELS[dir]}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Managers Table */}
      <div className="table-container">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
            Chargement des responsables...
          </div>
        ) : filteredResponsables.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
            Aucun responsable enregistré.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Nom complet</th>
                <th>Direction associée</th>
                <th>Demandes traitées (mois)</th>
                <th>Dernière connexion</th>
                <th>Statut</th>
                <th style={{ width: '100px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredResponsables.map((res) => (
                <tr key={res.id}>
                  <td>
                    <div className="avatar-cell">
                      <div className="cell-initials">
                        {getInitials(res.nom_complet)}
                      </div>
                      <div className="cell-info">
                        <span className="cell-title">{res.nom_complet}</span>
                        <span className="cell-subtitle">{res.email}</span>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className="badge badge-gray" style={{ fontWeight: 600, fontSize: '0.8rem' }}>
                      {res.direction}
                    </span>
                  </td>
                  <td>
                    <div style={{ textAlign: 'center', width: 'fit-content' }}>
                      <span className="count-circle">{res.demandes_traitees}</span>
                    </div>
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
                    {res.derniere_connexion || 'Aucune'}
                  </td>
                  <td>
                    {res.statut === 'ACTIF' ? (
                      <span className="badge badge-green">ACTIF</span>
                    ) : (
                      <span className="badge badge-gray">INACTIF</span>
                    )}
                  </td>
                  <td>
                    <div className="actions-cell">
                      <button className="btn-icon-only" title="Modifier" onClick={() => handleOpenEdit(res)}>
                        <Edit2 size={16} />
                      </button>
                      <button 
                        className={`btn-icon-only ${res.statut === 'ACTIF' ? '' : 'text-green'}`} 
                        title={res.statut === 'ACTIF' ? "Désactiver" : "Activer"}
                        onClick={() => handleToggleStatus(res.id)}
                        style={{ color: res.statut === 'ACTIF' ? 'var(--danger-color)' : 'var(--success-color)' }}
                      >
                        <Ban size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add / Edit Manager Modal */}
      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h3>{editingId ? 'Modifier le responsable' : 'Ajouter un responsable'}</h3>
              <button className="btn-icon-only" onClick={() => setIsModalOpen(false)}>
                <X size={18} />
              </button>
            </div>
            
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {errorModal && (
                  <div style={{
                    backgroundColor: 'var(--danger-bg)',
                    border: '1px solid var(--danger-border)',
                    color: 'var(--danger-color)',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    marginBottom: '16px'
                  }}>
                    {errorModal}
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Nom complet</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Ex: Ahmed Benali"
                    value={nomComplet}
                    onChange={(e) => setNomComplet(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Email Professionnel</label>
                  <input
                    type="email"
                    className="form-input"
                    placeholder="nom.prenom@transport.gov.ma"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Direction Associée</label>
                  <select
                    className="filter-select"
                    style={{ width: '100%' }}
                    value={direction}
                    onChange={(e) => setDirection(e.target.value)}
                  >
                    {DIRECTIONS.map(dir => (
                      <option key={dir} value={dir}>{DIRECTION_LABELS[dir]}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Rôle</label>
                  <select
                    className="filter-select"
                    style={{ width: '100%' }}
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                  >
                    <option value="Responsable">Responsable de Direction</option>
                    <option value="Administrateur">Administrateur Système</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Statut du compte</label>
                  <select
                    className="filter-select"
                    style={{ width: '100%' }}
                    value={statut}
                    onChange={(e) => setStatut(e.target.value)}
                  >
                    <option value="ACTIF">ACTIF (Accès autorisé)</option>
                    <option value="INACTIF">INACTIF (Accès bloqué)</option>
                  </select>
                </div>
                
                {!editingId && (
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '10px', fontStyle: 'italic' }}>
                    * Le mot de passe par défaut généré pour ce compte sera : <strong>password123</strong>
                  </p>
                )}
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
                  Annuler
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingId ? 'Enregistrer les modifications' : 'Créer le compte'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
