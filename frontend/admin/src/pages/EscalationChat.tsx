import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api, Escalation } from "../api";

export default function EscalationChat() {
  const params = useParams();
  const escalationId = useMemo(() => params.escalationId || "", [params.escalationId]);
  const [data, setData] = useState<Escalation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reply, setReply] = useState("");

  const load = async () => {
    if (!escalationId) return;
    try {
      setError(null);
      setData(await api.getEscalation(escalationId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    void load();
    // Light polling for updates
    const t = window.setInterval(() => void load(), 2000);
    return () => window.clearInterval(t);
  }, [escalationId]);

  const onSend = async () => {
    const msg = reply.trim();
    if (!msg) return;
    try {
      await api.replyEscalation(escalationId, msg);
      setReply("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onClose = async () => {
    try {
      await api.closeEscalation(escalationId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <h2 style={{ margin: 0 }}>Escalation Chat</h2>
        <span className="pill mono">{escalationId}</span>
        <div style={{ flex: 1 }} />
        <button className="btn" onClick={() => void load()}>Refresh</button>
        <button className="btn btn-danger" onClick={() => void onClose()}>Close</button>
      </div>

      {error && <div className="card" style={{ borderColor: "#fecaca", color: "#991b1b" }}>{error}</div>}

      {data && (
        <div className="card" style={{ display: "grid", gap: 8 }}>
          <div className="row">
            <div className="pill">Status: {data.status}</div>
            <div className="pill mono">Ticket: {data.ticket_id}</div>
            <div className="pill mono">User: {data.user_id}</div>
            <div className="pill">Reason: {data.reason}</div>
          </div>

          <div style={{ border: "1px solid #e2e8f0", borderRadius: 12, padding: 12, maxHeight: 420, overflow: "auto", background: "#f8fafc" }}>
            {(data.messages ?? []).map((m, idx) => (
              <div key={idx} style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 12, color: "#475569", marginBottom: 4 }}>
                  <span className="pill" style={{ marginRight: 8 }}>{m.sender.toUpperCase()}</span>
                </div>
                <div className="card" style={{ padding: 10 }}>{m.text}</div>
              </div>
            ))}
            {(data.messages ?? []).length === 0 && (
              <div style={{ color: "#64748b" }}>No messages recorded.</div>
            )}
          </div>

          <div className="row" style={{ alignItems: "flex-end" }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 12, color: "#475569" }}>Type reply...</label>
              <textarea value={reply} onChange={(e) => setReply(e.target.value)} rows={3} />
            </div>
            <button className="btn btn-primary" onClick={() => void onSend()}>Send</button>
          </div>
        </div>
      )}
    </div>
  );
}

