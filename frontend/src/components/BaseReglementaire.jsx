import React, { useState, useEffect } from 'react';
import { Plus, Search, Edit2, Trash2, X } from 'lucide-react';

const API_URL = "http://localhost:8000/api";
const DIRECTIONS = ["DTR", "DSPCT", "DAAJJ", "DMM", "DJAC", "DSI", "Cabinet du Ministère"];
const DIRECTION_LABELS = {
  "DTR": "DTR",
  "DSPCT": "DSPCT",
  "DAAJJ": "DAAJJ",
  "DMM": "DMM",
  "DJAC": "DJAC",
  "DSI": "DSI",
  "Cabinet du Ministère": "Cabinet du Ministère"
};


export default function BaseReglementaire({ user }) {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterDecret, setFilterDecret] = useState('Tous');
  const [filterDate, setFilterDate] = useState('');
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  // États Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [numeroArticle, setNumeroArticle] = useState('');
  const [texteExtrait, setTexteExtrait] = useState('');
  const [decretSource, setDecretSource] = useState('Décret 2.21.968');
  const [codeDirection, setCodeDirection] = useState('DTR');
  const [errorModal, setErrorModal] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Charger les articles de loi
  const loadArticles = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/base-reglementaire`);
      if (response.ok) {
        const data = await response.json();
        setArticles(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadArticles();
  }, []);

  const handleOpenAdd = () => {
    setEditingId(null);
    setNumeroArticle('');
    setTexteExtrait('');
    setDecretSource('Décret 2.21.968');
    setCodeDirection('DTR');
    setErrorModal('');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (art) => {
    setEditingId(art.id);
    setNumeroArticle(art.numero_article);
    setTexteExtrait(art.texte_extrait);
    setDecretSource(art.decret_source);
    setCodeDirection(art.code_direction);
    setErrorModal('');
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!numeroArticle || !texteExtrait || !decretSource) {
      setErrorModal("Veuillez remplir tous les champs.");
      return;
    }

    const payload = {
      numero_article: numeroArticle,
      texte_extrait: texteExtrait,
      decret_source: decretSource,
      date_version: new Date().toLocaleDateString('fr-FR'), // Date du jour
      code_direction: codeDirection
    };

    try {
      let response;
      if (editingId) {
        response = await fetch(`${API_URL}/base-reglementaire/${editingId}?user_name=${encodeURIComponent(user.nom_complet)}&user_role=${encodeURIComponent(user.role)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        response = await fetch(`${API_URL}/base-reglementaire?user_name=${encodeURIComponent(user.nom_complet)}&user_role=${encodeURIComponent(user.role)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Erreur lors de l'enregistrement.");
      }

      const resData = await response.json();
      setIsModalOpen(false);
      if (resData.rag_sync === false) {
        setSuccessMessage("Article enregistré, mais la synchronisation avec le moteur d'argumentaire a échoué.");
      } else {
        setSuccessMessage(
          editingId
            ? "Article modifié — le moteur d'argumentaire utilisera la nouvelle version."
            : "Article ajouté — disponible immédiatement pour la génération d'argumentaire."
        );
      }
      loadArticles();
    } catch (err) {
      setErrorModal(err.message);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Êtes-vous sûr de vouloir supprimer cet article réglementaire ?")) return;
    try {
      const response = await fetch(`${API_URL}/base-reglementaire/${id}?user_name=${encodeURIComponent(user.nom_complet)}&user_role=${encodeURIComponent(user.role)}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        const resData = await response.json();
        if (resData.rag_sync === false) {
          setSuccessMessage("Article supprimé de l'interface, mais introuvable dans la base RAG (article de démo hors décret).");
        } else {
          setSuccessMessage("Article supprimé — retiré de la base utilisée par le moteur d'argumentaire.");
        }
        loadArticles();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Filtrer les articles
  const filteredArticles = articles.filter(art => {
    const matchesSearch = 
      art.numero_article.toLowerCase().includes(searchQuery.toLowerCase()) ||
      art.texte_extrait.toLowerCase().includes(searchQuery.toLowerCase()) ||
      art.code_direction.toLowerCase().includes(searchQuery.toLowerCase());
      
    const matchesDecret = filterDecret === 'Tous' || art.decret_source.toLowerCase().includes(filterDecret.toLowerCase());
    
    // Filtre date (simplifié)
    const matchesDate = !filterDate || art.date_version.includes(filterDate);

    return matchesSearch && matchesDecret && matchesDate;
  });

  // Liste des décrets uniques pour les filtres
  const decretOptions = ['Tous', ...new Set(articles.map(a => a.decret_source))];

  // Calcul pagination
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentArticles = filteredArticles.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(filteredArticles.length / itemsPerPage);

  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
  };

  const isAdmin = user?.role === 'Administrateur';

  return (
    <div>
      <div className="page-header">
        <div className="page-title-area">
          <h1>Base réglementaire</h1>
          <p>Consultez et gérez les articles, décrets et textes de loi régissant le transport.</p>
        </div>
        {isAdmin && (
          <button className="btn btn-primary" onClick={handleOpenAdd}>
            <Plus size={16} />
            Ajouter un article
          </button>
        )}
      </div>

      {successMessage && (
        <div style={{
          backgroundColor: 'var(--success-bg, #ecfdf5)',
          border: '1px solid var(--success-border, #6ee7b7)',
          color: 'var(--success-color, #047857)',
          padding: '12px 16px',
          borderRadius: 'var(--radius-sm)',
          fontSize: '0.85rem',
          fontWeight: 600,
          marginBottom: '16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{successMessage}</span>
          <button className="btn-icon-only" onClick={() => setSuccessMessage('')} title="Fermer">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Filters Bar */}
      <div className="filters-bar">
        <div className="filters-left" style={{ gap: '16px' }}>
          <div className="search-box" style={{ flex: 2 }}>
            <Search size={18} />
            <input 
              type="text" 
              placeholder="Rechercher par numéro d'article ou contenu..." 
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
            />
          </div>

          <select
            className="filter-select"
            style={{ flex: 1 }}
            value={filterDecret}
            onChange={(e) => { setFilterDecret(e.target.value); setCurrentPage(1); }}
          >
            {decretOptions.map(dec => (
              <option key={dec} value={dec}>{dec === 'Tous' ? 'Tous les décrets' : dec}</option>
            ))}
          </select>

          <input 
            type="text" 
            placeholder="Date de modif." 
            className="filter-input"
            style={{ flex: 1 }}
            value={filterDate}
            onChange={(e) => { setFilterDate(e.target.value); setCurrentPage(1); }}
          />
        </div>
      </div>

      {/* Articles Table */}
      <div className="table-container">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
            Chargement de la base réglementaire...
          </div>
        ) : currentArticles.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
            Aucun article trouvé.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '120px' }}>Numéro</th>
                <th>Extrait du texte</th>
                <th style={{ width: '180px' }}>Décret source</th>
                <th style={{ width: '140px' }}>Dernière modif.</th>
                {isAdmin && <th style={{ width: '100px' }}>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {currentArticles.map((art) => (
                <tr key={art.id}>
                  <td style={{ fontWeight: 700, color: 'var(--primary-color)' }}>
                    {art.numero_article}
                  </td>
                  <td style={{ lineHeight: 1.5, color: '#334155', maxWidth: '400px' }}>
                    {art.texte_extrait}
                  </td>
                  <td>
                    <span className="badge badge-blue">
                      {art.decret_source}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
                    {art.date_version}
                  </td>
                  {isAdmin && (
                    <td>
                      <div className="actions-cell">
                        <button className="btn-icon-only" title="Modifier" onClick={() => handleOpenEdit(art)}>
                          <Edit2 size={16} />
                        </button>
                        <button className="btn-icon-only btn-delete" title="Supprimer" onClick={() => handleDelete(art.id)}>
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {filteredArticles.length > 0 && (
        <div className="pagination">
          <span className="pagination-info">
            Affichage de {indexOfFirstItem + 1} à {Math.min(indexOfLastItem, filteredArticles.length)} sur {filteredArticles.length} articles
          </span>
          <div className="pagination-controls">
            <button 
              className="page-btn" 
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
            >
              &lt;
            </button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button
                key={i + 1}
                className={`page-btn ${currentPage === i + 1 ? 'active' : ''}`}
                onClick={() => handlePageChange(i + 1)}
              >
                {i + 1}
              </button>
            ))}
            <button 
              className="page-btn" 
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
            >
              &gt;
            </button>
          </div>
        </div>
      )}

      {/* Modal Add/Edit */}
      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ width: '550px' }}>
            <div className="modal-header">
              <h3>{editingId ? 'Modifier l\'article' : 'Ajouter un article'}</h3>
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
                  <label className="form-label">Numéro d'article</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Ex: Art. 12-A"
                    value={numeroArticle}
                    onChange={(e) => setNumeroArticle(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Décret source / Texte de loi</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Ex: Décret 2.21.968"
                    value={decretSource}
                    onChange={(e) => setDecretSource(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Direction administrative concernée</label>
                  <select
                    className="filter-select"
                    style={{ width: '100%' }}
                    value={codeDirection}
                    onChange={(e) => setCodeDirection(e.target.value)}
                  >
                    {DIRECTIONS.map(dir => (
                      <option key={dir} value={dir}>{DIRECTION_LABELS[dir] || dir}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Texte de l'article / Extrait de clause</label>
                  <textarea
                    className="form-input form-textarea"
                    placeholder="Une seule clause/tiret à la fois. Répétez l'opération pour chaque tiret d'un même article."
                    value={texteExtrait}
                    onChange={(e) => setTexteExtrait(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
                  Annuler
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingId ? 'Enregistrer les modifications' : 'Ajouter à la base'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
