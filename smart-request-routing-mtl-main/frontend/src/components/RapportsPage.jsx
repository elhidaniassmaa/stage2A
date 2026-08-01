import { useState } from "react";
import BilanReclamations from "./BilanReclamations";
import StatistiquesTendances from "./StatistiquesTendances";
import RapportsEnregistres from "./RapportsEnregistres";

export default function RapportsPage({ user }) {
  const [ongletActif, setOngletActif] = useState("bilan");

  return (
    <div>
      <div style={styles.tabs}>
        <button
          style={ongletActif === "bilan" ? styles.tabActive : styles.tab}
          onClick={() => setOngletActif("bilan")}
        >
          Bilan des Réclamations
        </button>
        <button
          style={ongletActif === "tendances" ? styles.tabActive : styles.tab}
          onClick={() => setOngletActif("tendances")}
        >
          Statistiques & Tendances
        </button>
        <button
          style={ongletActif === "historique" ? styles.tabActive : styles.tab}
          onClick={() => setOngletActif("historique")}
        >
          Rapports enregistrés
        </button>
      </div>

      {ongletActif === "bilan" && <BilanReclamations user={user} />}
      {ongletActif === "tendances" && <StatistiquesTendances user={user} />}
      {ongletActif === "historique" && <RapportsEnregistres />}
    </div>
  );
}

const styles = {
  tabs: { display: "flex", gap: "4px", padding: "16px 24px 0 24px", borderBottom: "1px solid #E2E8F0" },
  tab: { padding: "10px 18px", border: "none", background: "none", color: "#64748B", fontWeight: 600, fontSize: "0.9rem", cursor: "pointer", borderBottom: "3px solid transparent" },
  tabActive: { padding: "10px 18px", border: "none", background: "none", color: "#005DAA", fontWeight: 700, fontSize: "0.9rem", cursor: "pointer", borderBottom: "3px solid #005DAA" },
};
