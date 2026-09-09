import { useEffect, useState, useRef } from "react";
import { Download, Save, Loader2 } from "lucide-react";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";

const API_URL = "http://localhost:8000/api";

export default function BilanReclamations({ user }) {
  const [data, setData] = useState(null);
  const [dateDebut, setDateDebut] = useState('');
  const [dateFin, setDateFin] = useState('');
  const [sauvegarderHistorique, setSauvegarderHistorique] = useState(false);
  const [exportEnCours, setExportEnCours] = useState(false);
  const [messageAction, setMessageAction] = useState('');
  const contenuRef = useRef(null);

  const chargerRapport = () => {
    let url = `${API_URL}/rapport`;
    const params = [];
    if (dateDebut) params.push(`date_debut=${dateDebut}`);
    if (dateFin) params.push(`date_fin=${dateFin}`);
    if (params.length > 0) url += `?${params.join('&')}`;

    fetch(url)
      .then(res => res.json())
      .then(setData)
      .catch(err => console.error("Erreur de chargement du rapport :", err));
  };

  useEffect(() => { chargerRapport(); }, []);

  const libellePeriode = () => {
    if (dateDebut && dateFin) return `Du ${dateDebut} au ${dateFin}`;
    if (dateDebut) return `Depuis le ${dateDebut}`;
    if (dateFin) return `Jusqu'au ${dateFin}`;
    return "Toutes périodes confondues";
  };

  const exporterPDF = async () => {
    if (!contenuRef.current) return;
    setExportEnCours(true);
    try {
      const canvas = await html2canvas(contenuRef.current, { scale: 2, backgroundColor: "#ffffff" });
      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF("p", "mm", "a4");
      const largeurPage = pdf.internal.pageSize.getWidth();
      const hauteurImg = (canvas.height * largeurPage) / canvas.width;
      pdf.addImage(imgData, "PNG", 0, 0, largeurPage, hauteurImg);
      const nomFichier = `bilan-reclamations_${dateDebut || 'debut'}_${dateFin || 'fin'}.pdf`;
      pdf.save(nomFichier);
    } catch (e) {
      console.error("Erreur d'export PDF :", e);
    } finally {
      setExportEnCours(false);
    }
  };

  const enregistrerDansHistorique = async () => {
    const params = new URLSearchParams({
      nom: "Bilan des Réclamations",
      type_rapport: "bilan",
      user_name: user?.nom_complet || "Utilisateur",
    });
    if (dateDebut) params.append("date_debut", dateDebut);
    if (dateFin) params.append("date_fin", dateFin);

    try {
      const res = await fetch(`${API_URL}/rapports-historique?${params.toString()}`, { method: "POST" });
      if (res.ok) {
        setMessageAction("✅ Rapport enregistré dans l'historique.");
        setTimeout(() => setMessageAction(''), 3000);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleTelecharger = async () => {
    if (sauvegarderHistorique) await enregistrerDansHistorique();
    await exporterPDF();
  };

  if (!data) return <p style={styles.chargement}>Chargement du rapport...</p>;

  return (
    <div style={styles.page}>
      <div style={styles.entete}>
        <div>
          <h1 style={styles.titre}>Bilan des Réclamations</h1>
          <p style={styles.sousTitre}>{libellePeriode()}</p>
        </div>
        <div style={styles.actionsBar}>
          <button style={styles.btnPrimary} onClick={exporterPDF} disabled={exportEnCours}>
            {exportEnCours ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
            {exportEnCours ? "Génération..." : "Télécharger en PDF"}
          </button>
        </div>
      </div>

      {messageAction && <div style={styles.messageOk}>{messageAction}</div>}

      <section style={styles.filtres}>
        <div>
          <label style={styles.label}>Du</label>
          <input type="date" value={dateDebut} onChange={e => setDateDebut(e.target.value)} style={styles.inputDate} />
        </div>
        <div>
          <label style={styles.label}>Au</label>
          <input type="date" value={dateFin} onChange={e => setDateFin(e.target.value)} style={styles.inputDate} />
        </div>
        <button style={styles.btnSecondary} onClick={chargerRapport}>Appliquer</button>
        <button style={styles.btnSecondary} onClick={() => { setDateDebut(''); setDateFin(''); setTimeout(chargerRapport, 0); }}>
          Toutes les périodes
        </button>
      </section>

      {/* Zone capturée pour le PDF */}
      <div ref={contenuRef} style={styles.zoneCapture}>
        <h2 style={styles.titrePdf}>Bilan des Réclamations — {libellePeriode()}</h2>

        <section style={styles.kpiGrid}>
          <KpiCard label="Reçues" valeur={data.indicateurs_generaux.recues} couleur="#1E3A8A" />
          <KpiCard label="Clôturées" valeur={data.indicateurs_generaux.cloturees} couleur="#15803D" />
          <KpiCard label="En cours" valeur={data.indicateurs_generaux.en_cours} couleur="#C2410C" />
          <KpiCard label="Non concernées" valeur={data.indicateurs_generaux.non_concernees} couleur="#64748B" />
        </section>

        <Section titre="Analyse par direction">
          <Table
            colonnes={["Direction", "Reçues", "Clôturées", "En retard", "Taux retard"]}
            lignes={data.par_direction.map(d => [d.direction, d.recues, d.cloturees, d.en_retard, `${d.taux_retard}%`])}
          />
        </Section>

        <Section titre="Respect des délais légaux (60 jours)">
          <p style={styles.texte}>
            Taux de respect :{" "}
            <strong style={styles.accent}>
              {data.respect_delais.taux_respect !== null ? `${data.respect_delais.taux_respect}%` : "Pas encore de données"}
            </strong>
          </p>
          <p style={styles.texteSecondaire}>
            {data.respect_delais.traitees_dans_delai} dans les délais / {data.respect_delais.hors_delai} hors délai
          </p>
        </Section>

        <Section titre="Délai moyen de traitement par direction">
          <Table
            colonnes={["Direction", "Délai légal", "Délai réel moyen"]}
            lignes={data.delais_moyens.map(d => [d.direction, `${d.delai_cible} jours`, `${d.delai_reel_moyen} jours`])}
          />
        </Section>

        {data.fiabilite_ia.length > 0 && (
          <Section titre="Fiabilité de la classification IA par direction">
            <Table
              colonnes={["Direction", "Confiance moyenne", "Taux de correction", "Contenus signalés"]}
              lignes={data.fiabilite_ia.map(f => [f.direction, `${f.score_confiance_moyen}%`, `${f.taux_correction}%`, f.contenus_signales])}
            />
          </Section>
        )}

        <Section titre="Dossiers critiques (en retard)">
          <Table
            colonnes={["Réclamation", "Direction", "Retard", "Statut"]}
            lignes={data.dossiers_critiques.map(c => [c.reclamation, c.direction, `${c.retard_jours} jours`, c.statut])}
          />
        </Section>
      </div>
    </div>
  );
}

function KpiCard({ label, valeur, couleur }) {
  return (
    <div style={styles.kpiCard}>
      <span style={{ ...styles.kpiValeur, color: couleur }}>{valeur}</span>
      <span style={styles.kpiLabel}>{label}</span>
    </div>
  );
}

function Section({ titre, children }) {
  return (
    <section style={styles.section}>
      <h3 style={styles.sectionTitre}>{titre}</h3>
      {children}
    </section>
  );
}

function Table({ colonnes, lignes }) {
  if (lignes.length === 0) return <p style={styles.texteVide}>Aucune donnée disponible.</p>;
  return (
    <table style={styles.table}>
      <thead>
        <tr>{colonnes.map(c => <th key={c} style={styles.th}>{c}</th>)}</tr>
      </thead>
      <tbody>
        {lignes.map((ligne, i) => (
          <tr key={i} style={i % 2 === 0 ? styles.trPair : styles.trImpair}>
            {ligne.map((val, j) => <td key={j} style={styles.td}>{val}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const styles = {
  page: { fontFamily: "Inter, sans-serif", padding: "24px", maxWidth: "1100px", margin: "0 auto" },
  chargement: { padding: "40px", textAlign: "center", color: "#64748B", fontFamily: "Inter, sans-serif" },
  entete: { display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: "16px", marginBottom: "16px" },
  titre: { fontSize: "1.8rem", fontWeight: 700, color: "#1B365D", margin: 0 },
  sousTitre: { fontSize: "0.95rem", color: "#64748B", margin: "4px 0 0 0" },
  actionsBar: { display: "flex", alignItems: "center", gap: "16px" },
  checkboxLabel: { display: "flex", alignItems: "center", gap: "6px", fontSize: "0.85rem", color: "#334155", cursor: "pointer" },
  btnPrimary: { display: "flex", alignItems: "center", gap: "8px", backgroundColor: "#005DAA", color: "#fff", border: "none", borderRadius: "8px", padding: "10px 18px", fontWeight: 600, fontSize: "0.85rem", cursor: "pointer" },
  btnSecondary: { backgroundColor: "#fff", color: "#1B365D", border: "1px solid #CBD5E1", borderRadius: "8px", padding: "8px 14px", fontWeight: 600, fontSize: "0.85rem", cursor: "pointer" },
  messageOk: { backgroundColor: "#DCFCE7", color: "#15803D", border: "1px solid #86EFAC", borderRadius: "8px", padding: "10px 14px", marginBottom: "16px", fontSize: "0.85rem", fontWeight: 600 },
  filtres: { display: "flex", alignItems: "flex-end", gap: "12px", marginBottom: "24px", flexWrap: "wrap" },
  label: { display: "block", fontSize: "0.8rem", fontWeight: 600, color: "#475569", marginBottom: "4px" },
  inputDate: { border: "1px solid #CBD5E1", borderRadius: "6px", padding: "8px 10px", fontSize: "0.85rem" },
  zoneCapture: { backgroundColor: "#fff", borderRadius: "12px", padding: "24px" },
  titrePdf: { fontSize: "1.2rem", fontWeight: 700, color: "#1B365D", marginBottom: "20px" },
  kpiGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "24px" },
  kpiCard: { backgroundColor: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: "10px", padding: "20px" },
  kpiValeur: { display: "block", fontSize: "2rem", fontWeight: 700 },
  kpiLabel: { fontSize: "0.85rem", color: "#64748B", fontWeight: 500 },
  section: { marginBottom: "24px" },
  sectionTitre: { fontSize: "1.05rem", fontWeight: 700, color: "#1B365D", marginBottom: "10px", borderBottom: "2px solid #E2E8F0", paddingBottom: "8px" },
  texte: { fontSize: "0.95rem", color: "#334155" },
  texteSecondaire: { fontSize: "0.85rem", color: "#64748B" },
  texteVide: { fontSize: "0.85rem", color: "#94A3B8", fontStyle: "italic" },
  accent: { color: "#005DAA", fontSize: "1.1rem" },
  table: { width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" },
  th: { textAlign: "left", padding: "10px 12px", backgroundColor: "#F1F5F9", color: "#475569", fontWeight: 700, textTransform: "uppercase", fontSize: "0.72rem", letterSpacing: "0.03em" },
  td: { padding: "10px 12px", color: "#334155", borderBottom: "1px solid #F1F5F9" },
  trPair: { backgroundColor: "#fff" },
  trImpair: { backgroundColor: "#FAFBFC" },
};
