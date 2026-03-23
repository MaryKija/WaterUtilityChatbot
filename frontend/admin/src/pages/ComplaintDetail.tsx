import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api, Complaint, ComplaintStatus } from "../api";

const STATUSES: ComplaintStatus[] = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"];

export default function ComplaintDetail() {
  const params = useParams();
  const ticketId = useMemo(() => params.ticketId || "", [params.ticketId]);
  const [data, setData] = useState<Complaint | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");

  const load = async () => {
    if (!ticketId) return;
    try {
      setError(null);
      setData(await api.getComplaint(ticketId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    void load();
  }, [ticketId]);

  const onStatusChange = async (status: ComplaintStatus) => {
    try {
      const res = await api.updateComplaintStatus(ticketId, status);
      setData(res.complaint);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onAddNote = async () => {
    const msg = note.trim();
    if (!msg) return;
    try {
      const res = await api.addComplaintNote(ticketId, msg);
      setData(res.complaint);
      setNote("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <h2 style={{ margin: 0 }}>Complaint Detail</h2>
        <span className="pill mono">{ticketId}</span>
        <button className="btn" onClick={() => void load()}>Refresh</button>
      </div>
      {error && <div className="card" style={{ borderColor: "#fecaca", color: "#991b1b" }}>{error}</div>}

      {data && (
        <div className="card" style={{ display: "grid", gap: 10 }}>
          <div className="row">
            <div style={{ flex: "1 1 240px" }}>
              <div style={{ fontSize: 12, color: "#475569" }}>Name</div>
              <div style={{ fontWeight: 700 }}>{data.name}</div>
            </div>
            <div style={{ flex: "1 1 240px" }}>
              <div style={{ fontSize: 12, color: "#475569" }}>Area</div>
              <div style={{ fontWeight: 700 }}>{data.area}</div>
            </div>
          </div>

          <div>
            <div style={{ fontSize: 12, color: "#475569" }}>Issue</div>
            <div style={{ fontWeight: 700 }}>{data.issue}</div>
          </div>

          <div className="row" style={{ alignItems: "flex-end" }}>
            <div style={{ flex: "1 1 240px" }}>
              <div style={{ fontSize: 12, color: "#475569" }}>Status</div>
              <select value={data.status as ComplaintStatus} onChange={(e) => void onStatusChange(e.target.value as ComplaintStatus)}>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: "1 1 240px" }}>
              <div style={{ fontSize: 12, color: "#475569" }}>Updated</div>
              <div className="mono">{data.updated_at}</div>
            </div>
          </div>

          <div>
            <div style={{ fontSize: 12, color: "#475569", marginBottom: 6 }}>Notes</div>
            {(data.notes ?? []).map((n, idx) => (
              <div key={idx} className="card" style={{ marginBottom: 8, background: "#f8fafc" }}>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <span className="pill">{n.author}</span>
                  <span className="mono" style={{ fontSize: 12, color: "#64748b" }}>{n.created_at}</span>
                </div>
                <div style={{ marginTop: 8 }}>{n.note}</div>
              </div>
            ))}
            {(data.notes ?? []).length === 0 && (
              <div style={{ color: "#64748b" }}>No notes yet.</div>
            )}
          </div>

          <div className="row" style={{ alignItems: "flex-end" }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, color: "#475569" }}>Add Note</div>
              <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Technician assigned" />
            </div>
            <button className="btn btn-primary" onClick={() => void onAddNote()}>Add</button>
          </div>
        </div>
      )}
    </div>
  );
}

