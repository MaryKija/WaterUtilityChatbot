import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { adminApi, EscalationSummary } from "../api";

export default function AdminEscalations() {
  const [items, setItems] = useState<EscalationSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setError(null);
      setItems(await adminApi.listEscalations());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="grid gap-3">
      <div className="flex items-center gap-2">
        <h2 className="m-0 text-xl font-extrabold text-slate-900">Escalations</h2>
        <button
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
          onClick={() => void load()}
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>
      )}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <table className="w-full border-collapse">
          <thead className="bg-slate-50">
            <tr className="text-left text-xs font-semibold text-slate-600">
              <th className="px-4 py-3">Escalation</th>
              <th className="px-4 py-3">User</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Reason</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {items.map((e) => (
              <tr key={e.escalation_id} className="border-t border-slate-100">
                <td className="px-4 py-3 font-mono text-sm">{e.escalation_id}</td>
                <td className="px-4 py-3 font-mono text-sm">{e.user_id}</td>
                <td className="px-4 py-3 text-sm">
                  <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs">
                    {e.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">{e.reason}</td>
                <td className="px-4 py-3 text-right">
                  <Link
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
                    to={`/admin/escalations/${encodeURIComponent(e.escalation_id)}`}
                  >
                    Open
                  </Link>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td className="px-4 py-4 text-sm text-slate-500" colSpan={5}>
                  No escalations yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

