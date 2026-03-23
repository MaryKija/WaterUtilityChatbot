import { useEffect, useState } from "react";
import { api, ComplaintSummary, EscalationSummary } from "../api";

export default function Dashboard() {
  const [complaints, setComplaints] = useState<ComplaintSummary[]>([]);
  const [escalations, setEscalations] = useState<EscalationSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setError(null);
        const [c, e] = await Promise.all([api.listComplaints(), api.listEscalations()]);
        setComplaints(c);
        setEscalations(e);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    })();
  }, []);

  const openComplaints = complaints.filter((c) => c.status === "OPEN" || c.status === "IN_PROGRESS").length;
  const resolved = complaints.filter((c) => c.status === "RESOLVED").length;
  const waitingEscalations = escalations.filter((e) => e.status === "WAITING").length;

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h2 style={{ margin: 0 }}>Admin Dashboard</h2>
      {error && <div className="card" style={{ borderColor: "#fecaca", color: "#991b1b" }}>{error}</div>}

      <div className="row">
        <div className="card" style={{ flex: "1 1 260px" }}>
          <div style={{ fontSize: 12, color: "#475569" }}>Escalations</div>
          <div style={{ fontSize: 32, fontWeight: 800 }}>{escalations.length}</div>
          <div style={{ marginTop: 6 }}>
            <span className="pill">WAITING: {waitingEscalations}</span>
          </div>
        </div>
        <div className="card" style={{ flex: "1 1 260px" }}>
          <div style={{ fontSize: 12, color: "#475569" }}>Open Complaints</div>
          <div style={{ fontSize: 32, fontWeight: 800 }}>{openComplaints}</div>
          <div style={{ marginTop: 6 }}>
            <span className="pill">RESOLVED: {resolved}</span>
          </div>
        </div>
        <div className="card" style={{ flex: "1 1 260px" }}>
          <div style={{ fontSize: 12, color: "#475569" }}>Resolved Today</div>
          <div style={{ fontSize: 32, fontWeight: 800 }}>0</div>
          <div style={{ fontSize: 12, color: "#64748b" }}>(simple demo counter)</div>
        </div>
      </div>
    </div>
  );
}

