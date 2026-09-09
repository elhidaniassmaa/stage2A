import React, { useState, useEffect, useRef } from 'react';
import { 
  LayoutDashboard, 
  Users, 
  FileText, 
  ClipboardList,
  Brain,
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
import ListeDemandes from './components/ListeDemandes';
import Reentrainement from './components/Reentrainement';
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
  const [totalNonVues, setTotalNonVues] = useState(0);
  const [totalAujourdhui, setTotalAujourdhui] = useState(0);
  const [notifFiltre, setNotifFiltre] = useState('non_vues'); // 'non_vues', 'aujourdhui', 'toutes'
  const [showNotifications, setShowNotifications] = useState(false);
  const [demandeCibleeId, setDemandeCibleeId] = useState(null);
  const meAlertesSonores = useRef(new Set());
  const anciennesAlertesSonores = useRef(new Set());

  // TODO: remplacer par un fichier audio professionnel (frontend/public/alert-notification.mp3) si fourni manuellement
  const jouerSonAlerte = () => {
    try {
      const audioFichier = new Audio('/alert-notification.mp3');
      audioFichier.volume = 0.4;
      const playPromise = audioFichier.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {
          // Si le fichier audio n'existe pas ou la lecture est bloquée, basculer sur le son Web Audio API
          genererSonDouxWebAudio();
        });
      }
    } catch (_) {
      genererSonDouxWebAudio();
    }
  };

  // Son de notification très doux et professionnel via la Web Audio API (type chime/clochette administrative)
  const genererSonDouxWebAudio = () => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      const maintenant = ctx.currentTime;
      const volumeMaster = 0.35; // Volume modéré (entre 0.3 et 0.5)

      // Chime à deux notes douces et harmonieuses (Sol5: 783.99 Hz, Do6: 1046.50 Hz)
      const notes = [
        { freq: 783.99, start: 0, duree: 0.30 },
        { freq: 1046.50, start: 0.12, duree: 0.45 }
      ];

      notes.forEach(({ freq, start, duree }) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sine'; // Onde sinusoïdale pure et extrêmement douce
        osc.frequency.setValueAtTime(freq, maintenant + start);

        const tStart = maintenant + start;
        const tEnd = tStart + duree;

        // Enveloppe d'amplitude ADSR douce (attaque progressive sans clic, extinction douce)
        gain.gain.setValueAtTime(0.0001, tStart);
        gain.gain.exponentialRampToValueAtTime(volumeMaster, tStart + 0.02); // Attaque 20ms
        gain.gain.exponentialRampToValueAtTime(0.0001, tEnd); // Extinction progressive

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(tStart);
        osc.stop(tEnd);
      });
    } catch (_) {
      // Ignorer silencieusement si la politique audio du navigateur bloque la lecture sans geste utilisateur
    }
  };

  useEffect(() => {
    if (!user) return;

    if (window.Notification && Notification.permission === 'default') {
      Notification.requestPermission().catch(() => {});
    }

    const verifierNotifications = () => {
      fetch(`${API_URL}/notifications?user_id=${user.id}`)
        .then(res => res.json())
        .then(data => {
          const alertes = data.notifications || [];
          setTotalNonVues(data.total_non_vues || 0);
          setTotalAujourdhui(data.total_aujourdhui || 0);
          
          const nouveaux = alertes.filter(
            a => !a.vue && !anciennesAlertesSonores.current.has(`${a.id}-${a.type_alerte}`)
          );

          if (nouveaux.length > 0) {
            jouerSonAlerte();

            if (window.Notification && Notification.permission === 'granted') {
              const titre = nouveaux.length === 1 
                ? `Alerte Échéance GEDEC : ${nouveaux[0].numero}` 
                : `${nouveaux.length} Nouvelles alertes d'échéances GEDEC`;
              const corps = nouveaux.length === 1 
                ? `Demande affectée à ${nouveaux[0].direction}`
                : `Plusieurs dossiers nécessitent votre attention rapide.`;
              try {
                new Notification(titre, { body: corps, icon: '/favicon.ico' });
              } catch (_) {}
            }
          }

          anciennesAlertesSonores.current = new Set(
            alertes.map(a => `${a.id}-${a.type_alerte}`)
          );

          setNotifications(alertes);
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

  const handleMarquerVue = async (demandeId) => {
    if (!user) return;
    try {
      await fetch(`${API_URL}/notifications/marquer-vue?demande_id=${demandeId}&user_id=${user.id}`, { method: 'POST' });
      setNotifications(prev => prev.map(n => n.id === demandeId ? { ...n, vue: true } : n));
      setTotalNonVues(prev => Math.max(0, prev - 1));
    } catch (e) {
      console.error(e);
    }
  };

  const handleToutMarquerVu = async () => {
    if (!user) return;
    try {
      await fetch(`${API_URL}/notifications/tout-marquer-vu?user_id=${user.id}`, { method: 'POST' });
      setNotifications(prev => prev.map(n => ({ ...n, vue: true })));
      setTotalNonVues(0);
    } catch (e) {
      console.error(e);
    }
  };

  const handleNotifClick = (n) => {
    if (!n.vue) {
      handleMarquerVue(n.id);
    }
    setActiveTab('Liste des demandes');
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
        return <Dashboard user={user} />;
      case 'Liste des demandes':
        return (
          <ListeDemandes
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
      case 'Réentraînement IA':
        return <Reentrainement user={user} />;
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
              Informations d'environnement et de configuration du prototype GEDEC.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', borderBottom: '1px solid var(--border-color)' }}>
                <strong>Version du système</strong>
                <span>GEDEC v2.4.0 (FastAPI + React)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', borderBottom: '1px solid var(--border-color)', alignItems: 'center' }}>
                <strong>Environnement</strong>
                <span className="badge badge-blue">Développement / Prototype de stage</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', borderBottom: '1px solid var(--border-color)', alignItems: 'center' }}>
                <strong>Sécurité de transmission</strong>
                <span style={{ fontSize: '0.85rem', color: '#D97706', fontWeight: 600 }}>
                  Connexion locale non chiffrée (HTTP) — à sécuriser avant tout déploiement réel
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', borderBottom: '1px solid var(--border-color)' }}>
                <strong>Base de données</strong>
                <span>SQLite locale (backend/gedec.db)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', borderBottom: '1px solid var(--border-color)' }}>
                <strong>Cadre du projet</strong>
                <span>ENSIAS — Stage Ministère du Transport et de la Logistique</span>
              </div>
            </div>
          </div>
        );
      default:
        return <Dashboard user={user} />;
    }
  };

  // Si l'utilisateur n'est pas connecté, afficher l'écran de login
  if (!user) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  // Définir les éléments de menu selon le rôle
  const menuItems = [
    { name: 'Tableau de bord', icon: <LayoutDashboard size={18} />, roles: ['Responsable', 'Administrateur'] },
    { name: 'Liste des demandes', icon: <ClipboardList size={18} />, roles: ['Responsable', 'Administrateur'] },
    { name: 'Rapports', icon: <FileText size={18} />, roles: ['Responsable', 'Administrateur'] },
    { name: 'Historique', icon: <History size={18} />, roles: ['Administrateur'] },
    { name: 'Gestion des Responsables', icon: <Users size={18} />, roles: ['Administrateur'] },
    { name: 'Base réglementaire', icon: <FolderLock size={18} />, roles: ['Responsable', 'Administrateur'] },
    { name: 'Mots interdits', icon: <Lock size={18} />, roles: ['Administrateur'] },
    { name: 'Réentraînement IA', icon: <Brain size={18} />, roles: ['Administrateur'] },
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
                {totalNonVues > 0 && (
                  <span className="notifications-count-badge" style={{ backgroundColor: '#DC2626' }}>
                    {totalNonVues}
                  </span>
                )}
              </button>

              {showNotifications && (
                <div className="notifications-dropdown" style={{ width: '380px' }}>
                  <div className="notifications-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3>Notifications</h3>
                    {totalNonVues > 0 && (
                      <button 
                        onClick={handleToutMarquerVu}
                        style={{ background: 'none', border: 'none', color: '#005DAA', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
                      >
                        Tout marquer comme vu
                      </button>
                    )}
                  </div>

                  {/* Tabs Non vues / Aujourd'hui / Toutes */}
                  <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', backgroundColor: '#F8FAFC', padding: '4px', gap: '2px' }}>
                    <button 
                      style={{ flex: 1, padding: '6px 2px', border: 'none', background: notifFiltre === 'non_vues' ? '#fff' : 'transparent', fontWeight: notifFiltre === 'non_vues' ? 700 : 500, fontSize: '0.72rem', borderRadius: '4px', cursor: 'pointer', color: notifFiltre === 'non_vues' ? '#005DAA' : '#64748B', boxShadow: notifFiltre === 'non_vues' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none' }}
                      onClick={() => setNotifFiltre('non_vues')}
                    >
                      Non vues ({totalNonVues})
                    </button>
                    <button 
                      style={{ flex: 1, padding: '6px 2px', border: 'none', background: notifFiltre === 'aujourdhui' ? '#fff' : 'transparent', fontWeight: notifFiltre === 'aujourdhui' ? 700 : 500, fontSize: '0.72rem', borderRadius: '4px', cursor: 'pointer', color: notifFiltre === 'aujourdhui' ? '#005DAA' : '#64748B', boxShadow: notifFiltre === 'aujourdhui' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none' }}
                      onClick={() => setNotifFiltre('aujourdhui')}
                    >
                      Aujourd'hui ({totalAujourdhui})
                    </button>
                    <button 
                      style={{ flex: 1, padding: '6px 2px', border: 'none', background: notifFiltre === 'toutes' ? '#fff' : 'transparent', fontWeight: notifFiltre === 'toutes' ? 700 : 500, fontSize: '0.72rem', borderRadius: '4px', cursor: 'pointer', color: notifFiltre === 'toutes' ? '#005DAA' : '#64748B', boxShadow: notifFiltre === 'toutes' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none' }}
                      onClick={() => setNotifFiltre('toutes')}
                    >
                      Toutes ({notifications.length})
                    </button>
                  </div>

                  <div className="notifications-list">
                    {(() => {
                      const notifsAffichees = notifications.filter(n => {
                        if (notifFiltre === 'non_vues') return !n.vue;
                        if (notifFiltre === 'aujourdhui') return n.est_aujourdhui;
                        return true;
                      });

                      if (notifsAffichees.length === 0) {
                        return (
                          <div className="notification-empty-state">
                            {notifFiltre === 'non_vues' ? "Aucune notification non vue." : notifFiltre === 'aujourdhui' ? "Aucune alerte aujourd'hui." : "Aucune alerte."}
                          </div>
                        );
                      }

                      return notifsAffichees.map((notif) => {
                        let badgeColor = "#2563EB";
                        let badgeLabel = "Rappel";
                        if (notif.type_alerte === "prioritaire") {
                          badgeColor = "#EA580C";
                          badgeLabel = "Prioritaire";
                        } else if (notif.type_alerte === "depasse") {
                          badgeColor = "#DC2626";
                          badgeLabel = "Échéance Dépassée";
                        }

                        return (
                          <div 
                            key={notif.id} 
                            className="notification-item"
                            onClick={() => handleNotifClick(notif)}
                            style={{ 
                              cursor: 'pointer',
                              backgroundColor: notif.vue ? '#FFFFFF' : '#F0F7FF',
                              borderLeft: notif.vue ? '3px solid transparent' : '3px solid #005DAA',
                              opacity: notif.vue ? 0.75 : 1
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span className="notification-item-title" style={{ fontWeight: notif.vue ? 500 : 700 }}>
                                {!notif.vue && <span style={{ display: 'inline-block', width: '6px', height: '6px', backgroundColor: '#005DAA', borderRadius: '50%', marginRight: '6px' }}></span>}
                                {notif.numero}
                              </span>
                              {notif.est_aujourdhui && (
                                <span style={{ fontSize: '0.65rem', backgroundColor: '#FEF3C7', color: '#D97706', padding: '1px 5px', borderRadius: '4px', fontWeight: 600 }}>
                                  Aujourd'hui
                                </span>
                              )}
                            </div>
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
                                Échéance : {notif.date_echeance ? notif.date_echeance.split(' ')[0] : 'Indéterminée'}
                              </span>
                            </div>
                          </div>
                        );
                      });
                    })()}
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
            <strong>GEDEC</strong> — Prototype réalisé dans le cadre d'un projet de fin d'année (ENSIAS) — Stage au Ministère du Transport et de la Logistique
          </div>
          <div className="footer-links">
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              Environnement local de démonstration
            </span>
          </div>
        </footer>
      </main>
    </div>
  );
}
