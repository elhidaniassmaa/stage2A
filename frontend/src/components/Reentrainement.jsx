import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Brain, RefreshCw, CheckCircle, AlertTriangle } from 'lucide-react';

const API_URL = "http://localhost:8000/api";
const POLL_INTERVAL_MS = 2500;

export default function Reentrainement({ user }) {
  const [statut, setStatut] = useState({
    en_cours: false,
    pourcentage: 0,
    epoch_actuelle: 0,
    epoch_totale: 15,
    message_statut: 'Inactif',
    erreur: null,
  });
  const [lancement, setLancement] = useState(false);
  const [message, setMessage] = useState('');
  const pollRef = useRef(null);

  const fetchStatut = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/reentrainement/statut`);
      if (res.ok) {
        const data = await res.json();
        setStatut(data);
        return data;
      }
    } catch (e) {
      console.error(e);
    }
    return null;
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      const data = await fetchStatut();
      if (data && !data.en_cours) {
        stopPolling();
        setLancement(false);
        if (data.erreur) {
          setMessage(`❌ ${data.erreur}`);
        } else {
          setMessage('✅ Réentraînement terminé avec succès. Le modèle de classification a été mis à jour.');
        }
      }
    }, POLL_INTERVAL_MS);
  }, [fetchStatut, stopPolling]);

  useEffect(() => {
    fetchStatut().then((data) => {
      if (data?.en_cours) {
        setLancement(true);
        startPolling();
      }
    });
    return () => stopPolling();
  }, [fetchStatut, startPolling, stopPolling]);

  const handleLancer = async () => {
    setMessage('');
    setLancement(true);
    try {
      const res = await fetch(
        `${API_URL}/reentrainement/lancer?user_name=${encodeURIComponent(user.nom_complet)}&user_role=${encodeURIComponent(user.role)}`,
        { method: 'POST' }
      );
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Impossible de lancer le réentraînement.");
      }
      setMessage('⏳ Réentraînement démarré en arrière-plan...');
      await fetchStatut();
      startPolling();
    } catch (error) {
      setLancement(false);
      setMessage(`❌ ${error.message}`);
    }
  };

  const { en_cours, pourcentage, epoch_actuelle, epoch_totale, message_statut, erreur } = statut;

  return (
    <div>
      <div className="page-header">
        <div className="page-title-area">
          <h1>Réentraînement du modèle IA</h1>
          <p>
            Relancez l'entraînement XLM-RoBERTa à partir du dataset enrichi (corrections des responsables)
            pour améliorer la classification des demandes citoyennes.
          </p>
        </div>
      </div>

      <div className="table-container" style={{ padding: '30px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px', marginBottom: '24px' }}>
          <div style={{
            backgroundColor: 'var(--primary-light)',
            borderRadius: '12px',
            padding: '14px',
            color: 'var(--primary-color)',
          }}>
            <Brain size={28} />
          </div>
          <div>
            <h3 style={{ fontFamily: 'Outfit', fontWeight: 700, color: 'var(--secondary-color)', marginBottom: '8px' }}>
              Pipeline de réentraînement
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6, maxWidth: '680px' }}>
              Le processus fusionne le dataset de base avec <code>historique_corrections.xlsx</code>,
              affine le classificateur déjà en production (fine-tuning), compare les performances
              avant/après, puis déploie automatiquement le nouveau modèle (avec sauvegarde de l'ancien).
            </p>
          </div>
        </div>

        <button
          className="btn btn-primary"
          onClick={handleLancer}
          disabled={en_cours || lancement}
          style={{ marginBottom: '24px' }}
        >
          {en_cours || lancement ? (
            <>
              <RefreshCw size={16} className="animate-spin" />
              Réentraînement en cours...
            </>
          ) : (
            <>
              <Brain size={16} />
              Lancer le réentraînement
            </>
          )}
        </button>

        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '-16px', marginBottom: '20px' }}>
          Recommandé après 20-30 corrections accumulées, ou environ tous les 6 mois — pas à chaque correction isolée.
        </p>

        {(en_cours || lancement || pourcentage > 0) && (
          <div style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Progression
              </span>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary-color)' }}>
                {pourcentage}%
                {epoch_actuelle > 0 && ` — Époque ${epoch_actuelle}/${epoch_totale}`}
              </span>
            </div>
            <div style={{
              width: '100%',
              height: '12px',
              backgroundColor: '#E2E8F0',
              borderRadius: '6px',
              overflow: 'hidden',
            }}>
              <div style={{
                width: `${pourcentage}%`,
                height: '100%',
                backgroundColor: erreur ? 'var(--danger-color)' : 'var(--primary-color)',
                borderRadius: '6px',
                transition: 'width 0.4s ease',
              }} />
            </div>
            <p style={{
              marginTop: '10px',
              fontSize: '0.85rem',
              color: erreur ? 'var(--danger-color)' : 'var(--text-secondary)',
              fontWeight: 500,
            }}>
              {en_cours && <RefreshCw size={14} className="animate-spin" style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }} />}
              {message_statut}
            </p>
          </div>
        )}

        {message && !en_cours && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 16px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: message.startsWith('❌') ? 'var(--danger-bg, #FEE2E2)' : 'var(--success-bg, #DCFCE7)',
            border: `1px solid ${message.startsWith('❌') ? 'var(--danger-border, #FECACA)' : 'var(--success-border, #BBF7D0)'}`,
            fontSize: '0.85rem',
            fontWeight: 600,
            color: message.startsWith('❌') ? 'var(--danger-color)' : 'var(--success-color)',
          }}>
            {message.startsWith('❌') ? <AlertTriangle size={16} /> : <CheckCircle size={16} />}
            {message}
          </div>
        )}

        <div style={{ marginTop: '28px', padding: '16px', backgroundColor: '#F8FAFC', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic', lineHeight: 1.5 }}>
            * Le réentraînement s'exécute en arrière-plan et peut prendre plusieurs minutes selon la taille du dataset.
            Ne fermez pas l'application pendant le processus. Seuls les administrateurs peuvent lancer cette opération.
          </p>
        </div>
      </div>
    </div>
  );
}
