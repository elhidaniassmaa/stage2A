import { useEffect, useState } from "react";
import { Trash2, FileText, BarChart3 } from "lucide-react";

const API_URL = "http://localhost:8000/api";

export default function RapportsEnregistres() {
  const [rapports, setRapports] = useState([]);
  const [chargement, setChargement] = useState(true);

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
        Historique des rapports explicitement sauvegardés via la case "Garder dans l'historique des rapports".
      </p>

      {chargement ? (
        <p style={styles.texteVide}>Chargement...</p>
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
                  <button style={styles.btnSupprimer} onClick={() => supprimer(r.id)} title="Supprimer">
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p style={styles.note}>
        Note : cet écran liste les rapports sauvegardés (métadonnées + snapshot des données au moment de la
        génération). Le téléchargement PDF direct depuis cette liste n'est pas encore disponible — pour l'instant,
        régénérez le rapport avec les mêmes dates dans l'onglet correspondant si vous avez besoin du PDF.
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
  btnSupprimer: { background: "transparent", border: "none", color: "#94A3B8", cursor: "pointer", padding: "6px", borderRadius: "6px" },
  note: { fontSize: "0.78rem", color: "#94A3B8", marginTop: "20px", fontStyle: "italic" },
};
