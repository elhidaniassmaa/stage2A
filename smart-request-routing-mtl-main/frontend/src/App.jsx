import React, { useState, useEffect, useRef } from 'react';
import { 
  LayoutDashboard, 
  Users, 
  FileText, 
  History, 
  AlertOctagon, 
  Bell, 
  Settings, 
  LogOut,
  FolderLock,
  Lock,
  ChevronRight
} from 'lucide-react';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import Responsables from './components/Responsables';
import BaseReglementaire from './components/BaseReglementaire';
import Historique from './components/Historique';
import MotsInterdits from './components/MotsInterdits';
import RapportsPage from './components/RapportsPage';

const API_URL = "http://localhost:8000/api";

export default function App() {
  const [user, setUser] = useState(null); // userData from login endpoint
  const [activeTab, setActiveTab] = useState('Tableau de bord'); // Active sidebar tab
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [demandeCibleeId, setDemandeCibleeId] = useState(null);
  const audioRef = useRef(null);
  const anciennesPrioritaires = useRef(new Set());

  useEffect(() => {
    if (!user) return;

    const verifierNotifications = () => {
      fetch(`${API_URL}/notifications`)
        .then(res => res.json())
        .then(data => {
          const prioritaires = data.notifications.filter(n => n.type_alerte === "prioritaire");
          const nouveaux = prioritaires.filter(n => !anciennesPrioritaires.current.has(n.id));
          if (nouveaux.length > 0 && audioRef.current) {
            audioRef.current.play().catch(() => {});
          }
          anciennesPrioritaires.current = new Set(prioritaires.map(n => n.id));
          setNotifications(data.notifications);
        })
        .catch(err => console.error("Erreur notifications :", err));
    };

    verifierNotifications();
    const interval = setInterval(verifierNotifications, 60000);
    window.addEventListener('gedec:refresh-notifications', verifierNotifications);
    return () => {
      clearInterval(interval);
      window.removeEventListener('gedec:refresh-notifications', verifierNotifications);
    };
  }, [user]);

  const handleNotifClick = (n) => {
    setActiveTab('Tableau de bord');
    setDemandeCibleeId(n.id);
    setShowNotifications(false);
  };

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    // Rediriger vers l'écran approprié
    if (userData.role === 'Administrateur') {
      setActiveTab('Gestion des Responsables');
    } else {
      setActiveTab('Tableau de bord');
    }
  };
  
  const handleLogout = async () => {
    if (!user) return;
    try {
      await fetch(`${API_URL}/auth/logout?user_name=${encodeURIComponent(user.nom_complet)}&user_role=${encodeURIComponent(user.role)}`, {
        method: 'POST'
      });
    } catch (e) {
      console.error(e);
    } finally {
      setUser(null);
      setActiveTab('Tableau de bord');
    }
  };

  // Rendu de l'écran actif
  const renderContent = () => {
    switch (activeTab) {
      case 'Tableau de bord':
        return (
          <Dashboard
            user={user}
            demandeCibleeId={demandeCibleeId}
            clearDemandeCiblee={() => setDemandeCibleeId(null)}
          />
        );
      case 'Gestion des Responsables':
        return <Responsables user={user} />;
      case 'Base réglementaire':
        return <BaseReglementaire user={user} />;
      case 'Historique':
        return <Historique />;
      case 'Mots interdits':
        return <MotsInterdits user={user} />;
      case 'Rapports':
        return <RapportsPage user={user} />;
      case "Seuils d'alerte":
        return (
          <div className="table-container" style={{ padding: '30px' }}>
            <h2 style={{ fontFamily: 'Outfit', fontWeight: 700, color: 'var(--secondary-color)', marginBottom: '16px' }}>
              Seuils d'alerte légaux
            </h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: 1.6 }}>
              Configurez ici les délais réglementaires par défaut et les seuils de rappel pour le traitement des requêtes des citoyens.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              <div className="form-group">
                <label className="form-label">Délai d'échéance légal (jours)</label>
                <input type="number" className="form-input" defaultValue="60" disabled />
              </div>
              <div className="form-group">
                <label className="form-label">Seuil alerte prioritaire (jours restants)</label>
                <input type="number" className="form-input" defaultValue="5" disabled />
              </div>
              <div className="form-group">
                <label className="form-label">Seuil alerte rappel (jours restants)</label>
                <input type="number" className="form-input" defaultValue="15" disabled />
              </div>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '16px', fontStyle: 'italic' }}>
              * Seul l'Administrateur principal peut modifier ces variables système de manière persistante.
            </p>
          </div>
        );
      case 'Paramètres':
        return (
          <div className="table-container" style={{ padding: '30px' }}>
            <h2 style={{ fontFamily: 'Outfit', fontWeight: 700, color: 'var(--secondary-color)', marginBottom: '16px' }}>
              Paramètres système
            </h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Ajustez les configurations générales de la plateforme GEDEC.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', borderBottom: '1px solid var(--border-color)' }}>
                <strong>Version du système</strong>
                <span>GEDEC v2.4.0 (FastAPI + React)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', borderBottom: '1px solid var(--border-color)' }}>
                <strong>Environnement</strong>
                <span className="badge badge-green">Production</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', borderBottom: '1px solid var(--border-color)' }}>
                <strong>Sécurité de transmission</strong>
                <span>SSL / TLS Activé</span>
              </div>
            </div>
          </div>
        );
      default:
        return (
          <Dashboard
            user={user}
            demandeCibleeId={demandeCibleeId}
            clearDemandeCiblee={() => setDemandeCibleeId(null)}
          />
        );
    }
  };

  // Si l'utilisateur n'est pas connecté, afficher l'écran de login
  if (!user) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  // Définir les éléments de menu selon le rôle
  const menuItems = [
    { name: 'Tableau de bord', icon: <LayoutDashboard size={18} />, roles: ['Responsable', 'Administrateur'] },
    { name: 'Rapports', icon: <FileText size={18} />, roles: ['Responsable', 'Administrateur'] },
    { name: 'Historique', icon: <History size={18} />, roles: ['Administrateur'] },
    { name: 'Gestion des Responsables', icon: <Users size={18} />, roles: ['Administrateur'] },
    { name: 'Base réglementaire', icon: <FolderLock size={18} />, roles: ['Responsable', 'Administrateur'] },
    { name: 'Mots interdits', icon: <Lock size={18} />, roles: ['Administrateur'] },
    { name: "Seuils d'alerte", icon: <AlertOctagon size={18} />, roles: ['Administrateur'] },
    { name: 'Paramètres', icon: <Settings size={18} />, roles: ['Administrateur', 'Responsable'] }
  ];

  const filteredMenu = menuItems.filter(item => item.roles.includes(user.role));

  return (
    <div className="app-container">
      {/* Sidebar navigation */}
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="sidebar-logo">
            <div className="logo-icon">
              <FolderLock size={20} />
            </div>
            <div className="logo-text">
              <h2>GEDEC</h2>
              <p>Gestion des Demandes</p>
            </div>
          </div>

          <nav className="sidebar-menu">
            {filteredMenu.map(item => (
              <button
                key={item.name}
                className={`menu-item ${activeTab === item.name ? 'active' : ''}`}
                onClick={() => setActiveTab(item.name)}
              >
                {item.icon}
                <span>{item.name}</span>
              </button>
            ))}
          </nav>
        </div>

        <div className="sidebar-bottom">
          <button className="logout-btn" onClick={handleLogout}>
            <LogOut size={18} />
            <span>Déconnexion</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Top Header */}
        <header className="top-header">
          <div className="header-left">
            <a href="#" className="header-title-link">
              GEDEC <span>| {user.role === 'Administrateur' ? 'Administration Centrale' : 'Portail Responsable'}</span>
            </a>
            
            <div className="header-tabs">
              <span 
                className={`header-tab ${activeTab === 'Tableau de bord' ? 'active' : ''}`}
                onClick={() => setActiveTab('Tableau de bord')}
              >
                Tableau de bord
              </span>
              <span 
                className={`header-tab ${activeTab === 'Rapports' ? 'active' : ''}`}
                onClick={() => setActiveTab('Rapports')}
              >
                Rapports
              </span>
            </div>
          </div>

          <div className="header-right">
            <div className="search-box">
              <input 
                type="text" 
                placeholder="Rechercher..." 
                disabled 
                style={{ opacity: 0.6, cursor: 'not-allowed' }}
              />
            </div>

            <div className="notifications-container">
              <button 
                className="header-icon-btn" 
                title="Notifications" 
                onClick={() => setShowNotifications(!showNotifications)}
              >
                <Bell size={18} />
                {notifications.length > 0 && <span className="notification-dot"></span>}
              </button>

              {showNotifications && (
                <div className="notifications-dropdown">
                  <div className="notifications-header">
                    <h3>Notifications</h3>
                    {notifications.length > 0 && (
                      <span className="notifications-count-badge">
                        {notifications.length}
                      </span>
                    )}
                  </div>
                  <div className="notifications-list">
                    {notifications.length === 0 ? (
                      <div className="notification-empty-state">
                        Aucune alerte en attente.
                      </div>
                    ) : (
                      notifications.map((notif) => {
                        let badgeColor = "#2563EB"; // rappel (blue)
                        let badgeLabel = "Rappel";
                        if (notif.type_alerte === "prioritaire") {
                          badgeColor = "#EA580C"; // prioritaire (orange)
                          badgeLabel = "Prioritaire";
                        } else if (notif.type_alerte === "depasse") {
                          badgeColor = "#DC2626"; // depasse (red)
                          badgeLabel = "Échéance Dépassée";
                        }

                        return (
                          <div 
                            key={notif.id} 
                            className="notification-item"
                            onClick={() => handleNotifClick(notif)}
                            style={{ cursor: 'pointer' }}
                          >
                            <span className="notification-item-title">
                              {notif.numero}
                            </span>
                            <span className="notification-item-desc">
                              Affectée à : {notif.direction}
                            </span>
                            <div className="notification-badge-row">
                              <span 
                                style={{
                                  fontSize: '0.7rem',
                                  fontWeight: 700,
                                  color: badgeColor,
                                  backgroundColor: badgeColor + '15',
                                  padding: '2px 8px',
                                  borderRadius: '4px'
                                }}
                              >
                                {badgeLabel}
                              </span>
                              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                Échéance : {notif.date_echeance.split(' ')[0]}
                              </span>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              )}
            </div>

            <button className="header-icon-btn" title="Paramètres" onClick={() => setActiveTab('Paramètres')}>
              <Settings size={18} />
            </button>

            {/* Profile circular icon with names */}
            <div className="user-profile">
              <div className="avatar">
                {user.nom_complet.split(' ').map(p => p[0]).join('').toUpperCase()}
              </div>
              <div className="user-info">
                <span className="user-name">{user.nom_complet}</span>
                <span className="user-role">{user.role}</span>
              </div>
            </div>
          </div>
        </header>

        {/* Dynamic page content */}
        <div className="page-container">
          {renderContent()}
        </div>

        {/* Footer */}
        <footer className="footer-bar">
          <div>
            <strong>GEDEC ADMIN</strong> &copy; 2026 Ministère du Transport et de la Logistique - Royaume du Maroc
          </div>
          <div className="footer-links">
            <a href="#" className="footer-link">Mentions Légales</a>
            <a href="#" className="footer-link">Contact</a>
            <a href="#" className="footer-link">Politique de Confidentialité</a>
          </div>
        </footer>
      </main>
    </div>
  );
}
