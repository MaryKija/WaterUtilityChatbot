import { useEffect, useState } from "react";
import { adminApi, ComplaintSummary, EscalationSummary } from "../api";

export default function AdminDashboard() {
  const [complaints, setComplaints] = useState<ComplaintSummary[]>([]);
  const [escalations, setEscalations] = useState<EscalationSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setError(null);
        const [c, e] = await Promise.all([adminApi.listComplaints(), adminApi.listEscalations()]);
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
    <div className="grid gap-3">
      <h2 className="m-0 text-xl font-extrabold text-slate-900">Admin Dashboard</h2>
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>
      )}

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="text-xs font-medium text-slate-500">Escalations</div>
          <div className="text-3xl font-extrabold text-slate-900">{escalations.length}</div>
          <div className="mt-2 inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs">
            WAITING: {waitingEscalations}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="text-xs font-medium text-slate-500">Open Complaints</div>
          <div className="text-3xl font-extrabold text-slate-900">{openComplaints}</div>
          <div className="mt-2 inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs">
            RESOLVED: {resolved}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="text-xs font-medium text-slate-500">Resolved Today</div>
          <div className="text-3xl font-extrabold text-slate-900">0</div>
          <div className="text-xs text-slate-500">(simple demo counter)</div>
        </div>
      </div>
    </div>
  );
}

