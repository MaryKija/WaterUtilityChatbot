import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, EscalationSummary } from "../api";

export default function Escalations() {
  const [items, setItems] = useState<EscalationSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setError(null);
      setItems(await api.listEscalations());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <h2 style={{ margin: 0 }}>Escalations</h2>
        <button className="btn" onClick={() => void load()}>Refresh</button>
      </div>
      {error && <div className="card" style={{ borderColor: "#fecaca", color: "#991b1b" }}>{error}</div>}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Escalation</th>
              <th>User</th>
              <th>Status</th>
              <th>Reason</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((e) => (
              <tr key={e.escalation_id}>
                <td className="mono">{e.escalation_id}</td>
                <td className="mono">{e.user_id}</td>
                <td><span className="pill">{e.status}</span></td>
                <td>{e.reason}</td>
                <td>
                  <Link className="btn" to={`/escalations/${encodeURIComponent(e.escalation_id)}`}>Open</Link>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={5} style={{ color: "#64748b" }}>No escalations yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

