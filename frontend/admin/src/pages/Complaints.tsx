import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ComplaintSummary } from "../api";

export default function Complaints() {
  const [items, setItems] = useState<ComplaintSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setError(null);
      setItems(await api.listComplaints());
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
        <h2 style={{ margin: 0 }}>Complaints</h2>
        <button className="btn" onClick={() => void load()}>Refresh</button>
      </div>
      {error && <div className="card" style={{ borderColor: "#fecaca", color: "#991b1b" }}>{error}</div>}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Ticket</th>
              <th>Issue</th>
              <th>Status</th>
              <th>Area</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.ticket_id}>
                <td className="mono">{c.ticket_id}</td>
                <td>{c.issue}</td>
                <td><span className="pill">{c.status}</span></td>
                <td>{c.area}</td>
                <td>
                  <Link className="btn" to={`/complaints/${encodeURIComponent(c.ticket_id)}`}>Open</Link>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={5} style={{ color: "#64748b" }}>No complaints yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

