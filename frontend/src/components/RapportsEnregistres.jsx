import { useEffect, useState, useRef } from "react";
import { Trash2, FileText, BarChart3, Download, Eye, X, Loader2 } from "lucide-react";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";

const API_URL = "http://localhost:8000/api";

export default function RapportsEnregistres() {
  const [rapports, setRapports] = useState([]);
  const [chargement, setChargement] = useState(true);
  const [rapportSelectionne, setRapportSelectionne] = useState(null);
  const [chargementDetails, setChargementDetails] = useState(false);
  const [exportEnCours, setExportEnCours] = useState(false);
  const snapshotRef = useRef(null);

  const charger = () => {
    setChargement(true);
    fetch(`${API_URL}/rapports-historique`)
      .then(res => res.json())
      .then(data => { setRapports(data); setChargement(false); })
      .catch(err => { console.error(err); setChargement(false); });
  };

  useEffect(() => { charger(); }, []);

  const supprimer = async (id) => {
    if (!window.confirm("Supprimer ce rapport de l'historique ?")) return;
    try {
      const res = await fetch(`${API_URL}/rapports-historique/${id}`, { method: "DELETE" });
      if (res.ok) charger();
    } catch (e) {
      console.error(e);
    }
  };

  const ouvrirRapport = async (id) => {
    setChargementDetails(true);
    try {
      const res = await fetch(`${API_URL}/rapports-historique/${id}`);
      if (res.ok) {
        const data = await res.json();
        setRapportSelectionne(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setChargementDetails(false);
    }
  };

  const telechargerPDFSnapshot = async () => {
    if (!snapshotRef.current || !rapportSelectionne) return;
    setExportEnCours(true);
    try {
      const canvas = await html2canvas(snapshotRef.current, { scale: 2, backgroundColor: "#ffffff" });
      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF("p", "mm", "a4");
      const largeurPage = pdf.internal.pageSize.getWidth();
      const hauteurImg = (canvas.height * largeurPage) / canvas.width;
      pdf.addImage(imgData, "PNG", 0, 0, largeurPage, hauteurImg);
      pdf.save(`${rapportSelectionne.nom.toLowerCase().replace(/ /g, '_')}_snapshot_${rapportSelectionne.id}.pdf`);
    } catch (e) {
      console.error(e);
    } finally {
      setExportEnCours(false);
    }
  };

  const libellePeriode = (r) => {
    if (r.date_debut && r.date_fin) return `${r.date_debut} → ${r.date_fin}`;
    if (r.date_debut) return `Depuis ${r.date_debut}`;
    if (r.date_fin) return `Jusqu'à ${r.date_fin}`;
    return "Toutes périodes";
  };

  return (
    <div style={styles.page}>
      <h1 style={styles.titre}>Rapports enregistrés</h1>
      <p style={styles.sousTitre}>
        Historique des rapports sauvegardés avec snapshot de données au moment de leur génération.
      </p>

      {chargement ? (
        <p style={styles.texteVide}>Chargement de l'historique...</p>
      ) : rapports.length === 0 ? (
        <p style={styles.texteVide}>Aucun rapport enregistré pour le moment.</p>
      ) : (
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Type</th>
              <th style={styles.th}>Nom</th>
              <th style={styles.th}>Période couverte</th>
              <th style={styles.th}>Généré le</th>
              <th style={styles.th}>Par</th>
              <th style={styles.th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rapports.map((r, i) => (
              <tr key={r.id} style={i % 2 === 0 ? styles.trPair : styles.trImpair}>
                <td style={styles.td}>
                  {r.type_rapport === "bilan" ? <FileText size={16} color="#005DAA" /> : <BarChart3 size={16} color="#005DAA" />}
                </td>
                <td style={styles.td}>{r.nom}</td>
                <td style={styles.td}>{libellePeriode(r)}</td>
                <td style={styles.td}>{r.date_generation}</td>
                <td style={styles.td}>{r.genere_par}</td>
                <td style={styles.td}>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button 
                      style={styles.btnAction} 
                      onClick={() => ouvrirRapport(r.id)} 
                      title="Visualiser et régénérer le PDF"
                    >
                      <Eye size={16} /> Régénérer PDF
                    </button>
                    <button style={styles.btnSupprimer} onClick={() => supprimer(r.id)} title="Supprimer">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Modal d'aperçu et régénération PDF */}
      {(rapportSelectionne || chargementDetails) && (
        <div style={styles.overlay}>
          <div style={styles.modal}>
            <div style={styles.modalHeader}>
              <div>
                <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#1B365D' }}>
                  {rapportSelectionne?.nom || "Chargement..."}
                </h2>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#64748B' }}>
                  Snapshot enregistré le {rapportSelectionne?.date_generation} par {rapportSelectionne?.genere_par}
                </p>
              </div>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                {rapportSelectionne && (
                  <button 
                    style={styles.btnPrimary} 
                    onClick={telechargerPDFSnapshot} 
                    disabled={exportEnCours}
                  >
                    {exportEnCours ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                    {exportEnCours ? "Génération PDF..." : "Télécharger PDF"}
                  </button>
                )}
                <button style={styles.btnClose} onClick={() => setRapportSelectionne(null)}>
                  <X size={18} />
                </button>
              </div>
            </div>

            <div style={styles.modalBody}>
              {chargementDetails ? (
                <p style={{ padding: '40px', textAlign: 'center', color: '#64748B' }}>Chargement du snapshot...</p>
              ) : (
                <div ref={snapshotRef} style={styles.snapshotContainer}>
                  <div style={{ borderBottom: '2px solid #005DAA', paddingBottom: '12px', marginBottom: '16px' }}>
                    <h3 style={{ margin: 0, color: '#005DAA', fontSize: '1.1rem' }}>{rapportSelectionne.nom}</h3>
                    <span style={{ fontSize: '0.8rem', color: '#64748B' }}>Période : {libellePeriode(rapportSelectionne)}</span>
                  </div>

                  {rapportSelectionne.donnees_json ? (
                    <div>
                      {rapportSelectionne.type_rapport === 'bilan' && rapportSelectionne.donnees_json.indicateurs_generaux && (
                        <div>
                          <h4 style={{ color: '#1B365D', margin: '0 0 10px 0' }}>Indicateurs Généraux</h4>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '20px' }}>
                            <div style={styles.kpiCard}>
                              <div style={styles.kpiVal}>{rapportSelectionne.donnees_json.indicateurs_generaux.recues}</div>
                              <div style={styles.kpiLbl}>Reçues</div>
                            </div>
                            <div style={styles.kpiCard}>
                              <div style={styles.kpiVal}>{rapportSelectionne.donnees_json.indicateurs_generaux.cloturees}</div>
                              <div style={styles.kpiLbl}>Clôturées</div>
                            </div>
                            <div style={styles.kpiCard}>
                              <div style={styles.kpiVal}>{rapportSelectionne.donnees_json.indicateurs_generaux.en_cours}</div>
                              <div style={styles.kpiLbl}>En cours</div>
                            </div>
                            <div style={styles.kpiCard}>
                              <div style={styles.kpiVal}>{rapportSelectionne.donnees_json.indicateurs_generaux.non_concernees}</div>
                              <div style={styles.kpiLbl}>Non concernées</div>
                            </div>
                          </div>
                        </div>
                      )}

                      {rapportSelectionne.donnees_json.par_direction && (
                        <div style={{ marginBottom: '20px' }}>
                          <h4 style={{ color: '#1B365D', margin: '0 0 10px 0' }}>Répartition par Direction</h4>
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                            <thead>
                              <tr style={{ backgroundColor: '#F1F5F9' }}>
                                <th style={{ padding: '8px', textAlign: 'left' }}>Direction</th>
                                <th style={{ padding: '8px', textAlign: 'center' }}>Reçues</th>
                                <th style={{ padding: '8px', textAlign: 'center' }}>Clôturées</th>
                                <th style={{ padding: '8px', textAlign: 'center' }}>En retard</th>
                              </tr>
                            </thead>
                            <tbody>
                              {rapportSelectionne.donnees_json.par_direction.map((d, idx) => (
                                <tr key={idx} style={{ borderBottom: '1px solid #E2E8F0' }}>
                                  <td style={{ padding: '8px' }}>{d.direction || d.nom}</td>
                                  <td style={{ padding: '8px', textAlign: 'center' }}>{d.recues || d.nombre}</td>
                                  <td style={{ padding: '8px', textAlign: 'center' }}>{d.cloturees ?? '-'}</td>
                                  <td style={{ padding: '8px', textAlign: 'center' }}>{d.en_retard ?? '-'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p style={{ color: '#94A3B8' }}>Aucune donnée dans le snapshot.</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <p style={styles.note}>
        Note : Vous pouvez régénérer et télécharger un PDF fidèle à n'importe quel moment en cliquant sur "Régénérer PDF".
      </p>
    </div>
  );
}

const styles = {
  page: { fontFamily: "Inter, sans-serif", padding: "24px", maxWidth: "1100px", margin: "0 auto" },
  titre: { fontSize: "1.8rem", fontWeight: 700, color: "#1B365D", margin: 0 },
  sousTitre: { fontSize: "0.9rem", color: "#64748B", margin: "6px 0 20px 0" },
  texteVide: { fontSize: "0.9rem", color: "#94A3B8", fontStyle: "italic", padding: "20px 0" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", backgroundColor: "#fff", borderRadius: "10px", overflow: "hidden", border: "1px solid #E2E8F0" },
  th: { textAlign: "left", padding: "12px 16px", backgroundColor: "#F1F5F9", color: "#475569", fontWeight: 700, textTransform: "uppercase", fontSize: "0.72rem", letterSpacing: "0.03em" },
  td: { padding: "12px 16px", color: "#334155", borderBottom: "1px solid #F1F5F9" },
  trPair: { backgroundColor: "#fff" },
  trImpair: { backgroundColor: "#FAFBFC" },
  btnAction: { display: "inline-flex", alignItems: "center", gap: "6px", backgroundColor: "#EFF6FF", color: "#005DAA", border: "1px solid #BFDBFE", padding: "6px 12px", borderRadius: "6px", fontSize: "0.78rem", fontWeight: 600, cursor: "pointer" },
  btnSupprimer: { background: "transparent", border: "none", color: "#94A3B8", cursor: "pointer", padding: "6px", borderRadius: "6px" },
  btnPrimary: { display: "inline-flex", alignItems: "center", gap: "6px", backgroundColor: "#005DAA", color: "#fff", border: "none", padding: "8px 16px", borderRadius: "6px", fontSize: "0.85rem", fontWeight: 600, cursor: "pointer" },
  btnClose: { background: "transparent", border: "none", color: "#64748B", cursor: "pointer", padding: "6px" },
  note: { fontSize: "0.78rem", color: "#94A3B8", marginTop: "20px", fontStyle: "italic" },
  overlay: { position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(15, 23, 42, 0.65)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000, padding: "20px" },
  modal: { backgroundColor: "#fff", borderRadius: "12px", width: "700px", maxWidth: "90vw", maxHeight: "85vh", display: "flex", flexDirection: "column", boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)" },
  modalHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 20px", borderBottom: "1px solid #E2E8F0" },
  modalBody: { padding: "20px", overflowY: "auto" },
  snapshotContainer: { backgroundColor: "#fff", padding: "16px", borderRadius: "8px", border: "1px solid #E2E8F0" },
  kpiCard: { backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", padding: "12px", borderRadius: "8px", textAlign: "center" },
  kpiVal: { fontSize: "1.4rem", fontWeight: 700, color: "#005DAA" },
  kpiLbl: { fontSize: "0.75rem", color: "#64748B", marginTop: "4px" },
};
