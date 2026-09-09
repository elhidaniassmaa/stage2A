import React, { useState } from 'react';
import { Eye, EyeOff, ShieldAlert } from 'lucide-react';

const API_URL = "http://localhost:8000/api";

export default function Login({ onLoginSuccess }) {
  const [role, setRole] = useState('Responsable'); // 'Responsable' or 'Administrateur'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Veuillez remplir tous les champs.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, role })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erreur lors de la connexion.');
      }

      const userData = await response.json();
      onLoginSuccess(userData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-top">
          <img 
            src="/morocco-crest.jpg" 
            alt="Armoiries du Maroc" 
            className="login-coat-arms" 
          />
          <h1 className="login-title">Portail Logistique</h1>
          <p className="login-subtitle">MINISTÈRE DU TRANSPORT ET DE LA LOGISTIQUE<br/>Royaume du Maroc</p>
        </div>

        <div className="login-body">
          <h3 style={{ textAlign: 'center', marginBottom: '20px', fontFamily: 'Outfit', fontWeight: 600, color: '#334155' }}>
            Connexion
          </h3>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Rôle Utilisateur</label>
              <div className="login-tabs">
                <button
                  type="button"
                  className={`login-tab-btn ${role === 'Responsable' ? 'active' : ''}`}
                  onClick={() => setRole('Responsable')}
                >
                  Responsable
                </button>
                <button
                  type="button"
                  className={`login-tab-btn ${role === 'Administrateur' ? 'active' : ''}`}
                  onClick={() => setRole('Administrateur')}
                >
                  Administrateur
                </button>
              </div>
            </div>

            {error && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                backgroundColor: 'var(--danger-bg)',
                border: '1px solid var(--danger-border)',
                color: 'var(--danger-color)',
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.8rem',
                fontWeight: 600,
                marginBottom: '16px'
              }}>
                <ShieldAlert size={18} />
                <span>{error}</span>
              </div>
            )}

            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label className="form-label">Identifiant (Email / Matricule)</label>
              <input
                type="email"
                className="form-input"
                placeholder="nom.prenom@transport.gov.ma"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label className="form-label" style={{ marginBottom: 0 }}>Mot de passe</label>
                <a href="#" style={{ fontSize: '0.75rem', color: 'var(--primary-color)', textDecoration: 'none', fontWeight: 600 }}>
                  Mot de passe oublié ?
                </a>
              </div>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="form-input"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{ paddingRight: '40px' }}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer'
                  }}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ width: '100%', padding: '12px' }}
              disabled={loading}
            >
              {loading ? 'Connexion en cours...' : 'Se connecter'}
            </button>
          </form>
        </div>

        <div className="login-footer-info">
          Besoin d'assistance ? <a href="#">Support technique</a>
        </div>
      </div>
    </div>
  );
}
