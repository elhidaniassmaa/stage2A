import React, { useState, useEffect } from 'react';
import { Search, Plus, Trash, Globe, Languages, Users, AlertTriangle, FileText } from 'lucide-react';

const API_URL = "http://localhost:8000/api";
const CATEGORIES = ["Vulgarité A", "Injure spécifique B", "Terme non-conforme C", "Obscénité", "Calomnie", "Corruption", "Exploit"];

export default function MotsInterdits({ user }) {
  const [langue, setLangue] = useState('Français');
  const [mots, setMots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('Toutes');
  
  // États d'ajout
  const [nouveauMot, setNouveauMot] = useState('');
  const [nouvelleCategorie, setNouvelleCategorie] = useState('Vulgarité A');
  const [message, setMessage] = useState('');

  // Charger les mots selon la langue
  const loadMots = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/mots-interdits?langue=${encodeURIComponent(langue)}`);
      if (response.ok) {
        const data = await response.json();
        setMots(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMots();
  }, [langue]);

  // Ajouter un ou plusieurs mots
  const handleAddMots = async (e) => {
    e.preventDefault();
    if (!nouveauMot.strip || !nouveauMot.trim()) return;

    try {
      const response = await fetch(`${API_URL}/mots-interdits?user_name=${encodeURIComponent(user.nom_complet)}&user_role=${encodeURIComponent(user.role)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mot: nouveauMot,
          langue: langue,
          categorie: nouvelleCategorie
        })
      });

      if (response.ok) {
        const resData = await response.json();
        if (resData.moderation_sync === false) {
          setMessage("Mot ajouté en base, mais la synchronisation avec le moteur de modération a échoué.");
        } else {
          setMessage(`✅ ${resData.message} — actif immédiatement pour la modération des demandes.`);
        }
        setNouveauMot('');
        loadMots();
        setTimeout(() => setMessage(''), 4000);
      }
    } catch (error) {
      console.error(error);
      setMessage("❌ Erreur lors de l'ajout.");
    }
  };

  // Supprimer un mot interdit
  const handleDeleteMot = async (id) => {
    try {
      const response = await fetch(`${API_URL}/mots-interdits/${id}?user_name=${encodeURIComponent(user.nom_complet)}&user_role=${encodeURIComponent(user.role)}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        const resData = await response.json();
        setMessage(
          resData.moderation_sync === false
            ? "Mot supprimé de la liste, mais synchronisation modération incomplète."
            : "✅ Mot supprimé — ne sera plus détecté lors du traitement des demandes."
        );
        loadMots();
        setTimeout(() => setMessage(''), 4000);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Exporter en PDF (simulé ou print)
  const handleExportPDF = () => {
    window.print();
  };

  // Filtrer les mots localement
  const filteredMots = mots.filter(m => {
    const matchesSearch = m.mot.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCat = selectedCategory === 'Toutes' || m.categorie === selectedCategory;
    return matchesSearch && matchesCat;
  });

  return (
    <div>
      <div className="page-header">
        <div className="page-title-area">
          <h1>Gestion des mots interdits</h1>
          <p>Modérez les lexiques utilisés dans les formulaires et les demandes officielles.</p>
        </div>
        <div style={{
          backgroundColor: 'var(--primary-color)',
          color: '#FFFFFF',
          padding: '8px 16px',
          borderRadius: 'var(--radius-sm)',
          fontSize: '0.85rem',
          fontWeight: 700
        }}>
          {mots.length} mots enregistrés ({langue})
        </div>
      </div>

      <div className="lexicon-layout">
        {/* Languages Selection Panel */}
        <div className="lexicon-languages-card">
          <h4 style={{ fontFamily: 'Outfit', fontWeight: 700, color: 'var(--secondary-color)', fontSize: '0.95rem' }}>
            Langue du lexique
          </h4>

          <button
            onClick={() => setLangue('Français')}
            className={`lexicon-lang-btn ${langue === 'Français' ? 'active' : ''}`}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Languages size={16} />
              <span>Français</span>
            </div>
            <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>FR</span>
          </button>

          <button
            onClick={() => setLangue('Arabe standard')}
            className={`lexicon-lang-btn ${langue === 'Arabe standard' ? 'active' : ''}`}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Globe size={16} />
              <span>Arabe standard</span>
            </div>
            <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>AR</span>
          </button>

          <button
            onClick={() => setLangue('Darija')}
            className={`lexicon-lang-btn ${langue === 'Darija' ? 'active' : ''}`}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Users size={16} />
              <span>Darija</span>
            </div>
            <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>DAR</span>
          </button>

          <div className="lexicon-info-box">
            <AlertTriangle size={24} style={{ flexShrink: 0 }} />
            <span>
              Les mots saisis ici seront automatiquement censurés ou rejetés lors du dépôt de dossier dans le système GEDEC.
            </span>
          </div>
        </div>

        {/* Word Tags panel */}
        <div className="lexicon-main-card">
          {/* Header controls inside card */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <div className="search-box" style={{ flex: 1, minWidth: '200px' }}>
              <Search size={16} />
              <input
                type="text"
                placeholder="Rechercher un mot..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ paddingY: '8px', fontSize: '0.8rem' }}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <select
                className="filter-select"
                style={{ padding: '8px 10px', fontSize: '0.8rem' }}
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                <option value="Toutes">Toutes les catégories</option>
                {CATEGORIES.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>

              <button className="btn btn-secondary" onClick={handleExportPDF} style={{ padding: '8px 12px' }}>
                <FileText size={16} />
                Exporter PDF
              </button>
            </div>
          </div>

          {/* Tags list */}
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
              Chargement du lexique...
            </div>
          ) : filteredMots.length === 0 ? (
            <div className="tags-grid" style={{ justifyContent: 'center', alignItems: 'center', color: 'var(--text-muted)' }}>
              Aucun mot interdit dans cette liste.
            </div>
          ) : (
            <div className="tags-grid">
              {filteredMots.map((word) => (
                <div key={word.id} className="word-tag">
                  <span>{word.mot}</span>
                  <span style={{ fontSize: '0.65rem', opacity: 0.6, fontWeight: 700, marginLeft: '2px' }}>
                    ({word.categorie})
                  </span>
                  <button 
                    className="word-tag-delete"
                    onClick={() => handleDeleteMot(word.id)}
                    title="Supprimer"
                  >
                    <Trash size={10} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add Form */}
          <div className="add-words-box">
            <h4 style={{ fontFamily: 'Outfit', fontWeight: 700, color: 'var(--secondary-color)', fontSize: '0.9rem', marginBottom: '12px' }}>
              Ajouter de nouveaux mots interdits
            </h4>

            <form onSubmit={handleAddMots} style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <div className="form-group" style={{ flex: 2, minWidth: '200px', marginBottom: 0 }}>
                <label className="form-label" style={{ fontSize: '0.7rem' }}>Saisir un mot (séparez par des virgules)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="ex: fraude, corrompu, insulte"
                  value={nouveauMot}
                  onChange={(e) => setNouveauMot(e.target.value)}
                  required
                />
              </div>

              <div className="form-group" style={{ flex: 1, minWidth: '130px', marginBottom: 0 }}>
                <label className="form-label" style={{ fontSize: '0.7rem' }}>Catégorie</label>
                <select
                  className="filter-select"
                  style={{ width: '100%', padding: '9px 10px', fontSize: '0.8rem' }}
                  value={nouvelleCategorie}
                  onChange={(e) => setNouvelleCategorie(e.target.value)}
                >
                  {CATEGORIES.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>

              <button type="submit" className="btn btn-primary" style={{ height: '38px', padding: '8px 16px' }}>
                <Plus size={16} />
                Ajouter
              </button>
            </form>

            {message && (
              <p style={{ 
                marginTop: '10px', 
                fontSize: '0.8rem', 
                fontWeight: 600, 
                color: message.startsWith('✅') ? 'var(--success-color)' : 'var(--danger-color)'
              }}>
                {message}
              </p>
            )}

            <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '8px' }}>
              * Vous pouvez saisir plusieurs termes à censurer simultanément en les séparant par des virgules (,).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
