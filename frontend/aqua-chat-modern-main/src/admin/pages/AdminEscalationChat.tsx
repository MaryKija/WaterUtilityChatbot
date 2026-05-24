import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { adminApi, Escalation } from "../api";

export default function AdminEscalationChat() {
  const params = useParams();
  const escalationId = useMemo(() => params.escalationId || "", [params.escalationId]);
  const [data, setData] = useState<Escalation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reply, setReply] = useState("");

  const load = async () => {
    if (!escalationId) return;
    try {
      setError(null);
      setData(await adminApi.getEscalation(escalationId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    void load();
    const t = window.setInterval(() => void load(), 2000);
    return () => window.clearInterval(t);
  }, [escalationId]);

  const onSend = async () => {
    const msg = reply.trim();
    if (!msg) return;
    try {
      await adminApi.replyEscalation(escalationId, msg);
      setReply("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onClose = async () => {
    try {
      await adminApi.closeEscalation(escalationId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="m-0 text-xl font-extrabold text-slate-900">Escalation Chat</h2>
        <span className="inline-flex rounded-full border border-slate-200 bg-white px-2 py-1 font-mono text-xs">
          {escalationId}
        </span>
        <div className="flex-1" />
        <button
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
          onClick={() => void load()}
        >
          Refresh
        </button>
        <button
          className="rounded-xl border border-red-300 bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-700"
          onClick={() => void onClose()}
        >
          Close
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>
      )}

      {data && (
        <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-1">Status: {data.status}</span>
            <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-1 font-mono">Ticket: {data.ticket_id}</span>
            <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-1 font-mono">User: {data.user_id}</span>
            <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-1">Reason: {data.reason}</span>
          </div>

          <div className="max-h-[440px] overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
            {(data.messages ?? []).map((m, idx) => (
              <div key={idx} className="mb-3">
                <div className="mb-1 flex items-center gap-2 text-xs text-slate-600">
                  <span className="inline-flex rounded-full border border-slate-200 bg-white px-2 py-0.5">
                    {m.sender.toUpperCase()}
                  </span>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-900">{m.text}</div>
              </div>
            ))}
            {(data.messages ?? []).length === 0 && <div className="text-sm text-slate-500">No messages recorded.</div>}
          </div>

          <div className="grid gap-2">
            <label htmlFor="reply-input" className="text-xs font-medium text-slate-600">
              Type reply…
            </label>
            <textarea
              id="reply-input"
              className="min-h-[90px] w-full rounded-xl border border-slate-200 bg-white p-3 text-sm"
              value={reply}
              onChange={(e) => setReply(e.target.value)}
            />
            <div className="flex justify-end">
              <button
                className="rounded-xl border border-primary bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:brightness-95"
                onClick={() => void onSend()}
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

