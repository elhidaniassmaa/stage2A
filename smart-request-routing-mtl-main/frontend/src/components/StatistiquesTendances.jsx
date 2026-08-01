import { useEffect, useState, useRef } from "react";
import { Download, Loader2 } from "lucide-react";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import {
  BarChart, Bar, PieChart, Pie, Cell, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";

const API_URL = "http://localhost:8000/api";
const COULEURS = ["#005DAA", "#1B365D", "#3B82F6", "#60A5FA", "#93C5FD", "#0EA5E9", "#0369A1", "#38BDF8"];

export default function StatistiquesTendances({ user }) {
  const [data, setData] = useState(null);
  const [dateDebut, setDateDebut] = useState('');
  const [dateFin, setDateFin] = useState('');
  const [exportEnCours, setExportEnCours] = useState(false);
  const contenuRef = useRef(null);

  const charger = () => {
    let url = `${API_URL}/rapport/tendances`;
    const params = [];
    if (dateDebut) params.push(`date_debut=${dateDebut}`);
    if (dateFin) params.push(`date_fin=${dateFin}`);
    if (params.length > 0) url += `?${params.join('&')}`;

    fetch(url).then(res => res.json()).then(setData).catch(console.error);
  };

  useEffect(() => { charger(); }, []);

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
      pdf.save(`statistiques-tendances_${dateDebut || 'debut'}_${dateFin || 'fin'}.pdf`);
    } finally {
      setExportEnCours(false);
    }
  };

  if (!data) return <p style={styles.chargement}>Chargement des statistiques...</p>;

  return (
    <div style={styles.page}>
      <div style={styles.entete}>
        <div>
          <h1 style={styles.titre}>Statistiques & Tendances</h1>
          <p style={styles.sousTitre}>Répartition géographique, par direction, et évolution dans le temps</p>
        </div>
        <button style={styles.btnPrimary} onClick={exporterPDF} disabled={exportEnCours}>
          {exportEnCours ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
          {exportEnCours ? "Génération..." : "Télécharger en PDF"}
        </button>
      </div>

      <section style={styles.filtres}>
        <div>
          <label style={styles.label}>Du</label>
          <input type="date" value={dateDebut} onChange={e => setDateDebut(e.target.value)} style={styles.inputDate} />
        </div>
        <div>
          <label style={styles.label}>Au</label>
          <input type="date" value={dateFin} onChange={e => setDateFin(e.target.value)} style={styles.inputDate} />
        </div>
        <button style={styles.btnSecondary} onClick={charger}>Appliquer</button>
        <button style={styles.btnSecondary} onClick={() => { setDateDebut(''); setDateFin(''); setTimeout(charger, 0); }}>
          Toutes les périodes
        </button>
      </section>

      <div ref={contenuRef} style={styles.zoneCapture}>
        <div style={styles.grille2col}>
          <Section titre="Répartition par direction">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.repartition_direction}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis dataKey="nom" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="nombre" fill="#005DAA" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Section>

          <Section titre="Répartition par région">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={data.repartition_region} dataKey="nombre" nameKey="nom" cx="50%" cy="50%" outerRadius={90} label={({ nom, pourcentage }) => `${nom} (${pourcentage}%)`}>
                  {data.repartition_region.map((_, i) => <Cell key={i} fill={COULEURS[i % COULEURS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Section>
        </div>

        <Section titre="Évolution du volume de demandes">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={data.evolution_demandes}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="periode" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="nombre" stroke="#005DAA" strokeWidth={2.5} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </Section>

        <Section titre="Délai moyen de réponse par direction">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data.delais_moyens_direction} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="direction" tick={{ fontSize: 11 }} width={100} />
              <Tooltip />
              <Bar dataKey="delai_moyen" fill="#1B365D" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
          {data.delais_moyens_direction.length === 0 && (
            <p style={styles.texteVide}>Pas encore de demandes répondues pour calculer un délai moyen.</p>
          )}
        </Section>
      </div>
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

const styles = {
  page: { fontFamily: "Inter, sans-serif", padding: "24px", maxWidth: "1100px", margin: "0 auto" },
  chargement: { padding: "40px", textAlign: "center", color: "#64748B", fontFamily: "Inter, sans-serif" },
  entete: { display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: "16px", marginBottom: "16px" },
  titre: { fontSize: "1.8rem", fontWeight: 700, color: "#1B365D", margin: 0 },
  sousTitre: { fontSize: "0.95rem", color: "#64748B", margin: "4px 0 0 0" },
  btnPrimary: { display: "flex", alignItems: "center", gap: "8px", backgroundColor: "#005DAA", color: "#fff", border: "none", borderRadius: "8px", padding: "10px 18px", fontWeight: 600, fontSize: "0.85rem", cursor: "pointer" },
  btnSecondary: { backgroundColor: "#fff", color: "#1B365D", border: "1px solid #CBD5E1", borderRadius: "8px", padding: "8px 14px", fontWeight: 600, fontSize: "0.85rem", cursor: "pointer" },
  filtres: { display: "flex", alignItems: "flex-end", gap: "12px", marginBottom: "24px", flexWrap: "wrap" },
  label: { display: "block", fontSize: "0.8rem", fontWeight: 600, color: "#475569", marginBottom: "4px" },
  inputDate: { border: "1px solid #CBD5E1", borderRadius: "6px", padding: "8px 10px", fontSize: "0.85rem" },
  zoneCapture: { backgroundColor: "#fff", borderRadius: "12px", padding: "24px" },
  grille2col: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" },
  section: { marginBottom: "28px" },
  sectionTitre: { fontSize: "1.05rem", fontWeight: 700, color: "#1B365D", marginBottom: "14px", borderBottom: "2px solid #E2E8F0", paddingBottom: "8px" },
  texteVide: { fontSize: "0.85rem", color: "#94A3B8", fontStyle: "italic", textAlign: "center" },
};
