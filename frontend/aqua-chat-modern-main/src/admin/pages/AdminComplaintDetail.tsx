import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { adminApi, Complaint, ComplaintStatus } from "../api";

const STATUSES: ComplaintStatus[] = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"];

export default function AdminComplaintDetail() {
  const params = useParams();
  const ticketId = useMemo(() => params.ticketId || "", [params.ticketId]);
  const [data, setData] = useState<Complaint | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");

  const load = async () => {
    if (!ticketId) return;
    try {
      setError(null);
      setData(await adminApi.getComplaint(ticketId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    void load();
  }, [ticketId]);

  const onStatusChange = async (status: ComplaintStatus) => {
    try {
      const res = await adminApi.updateComplaintStatus(ticketId, status);
      setData(res.complaint);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onAddNote = async () => {
    const msg = note.trim();
    if (!msg) return;
    try {
      const res = await adminApi.addComplaintNote(ticketId, msg);
      setData(res.complaint);
      setNote("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="m-0 text-xl font-extrabold text-slate-900">Complaint Detail</h2>
        <span className="inline-flex rounded-full border border-slate-200 bg-white px-2 py-1 font-mono text-xs">
          {ticketId}
        </span>
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

      {data && (
        <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4">
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <div className="text-xs font-medium text-slate-500">Name</div>
              <div className="text-sm font-bold text-slate-900">{data.name}</div>
            </div>
            <div>
              <div className="text-xs font-medium text-slate-500">Area</div>
              <div className="text-sm font-bold text-slate-900">{data.area}</div>
            </div>
          </div>

          <div>
            <div className="text-xs font-medium text-slate-500">Issue</div>
            <div className="text-sm font-bold text-slate-900">{data.issue}</div>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <div className="text-xs font-medium text-slate-500">Status</div>
              <select
                className="mt-1 w-full rounded-xl border border-slate-200 bg-white p-2 text-sm"
                value={data.status as ComplaintStatus}
                onChange={(e) => void onStatusChange(e.target.value as ComplaintStatus)}
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <div className="text-xs font-medium text-slate-500">Updated</div>
              <div className="mt-1 font-mono text-xs text-slate-700">{data.updated_at}</div>
            </div>
          </div>

          <div>
            <div className="text-xs font-medium text-slate-500">Notes</div>
            <div className="mt-2 grid gap-2">
              {(data.notes ?? []).map((n, idx) => (
                <div key={idx} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                    <span className="inline-flex rounded-full border border-slate-200 bg-white px-2 py-0.5">{n.author}</span>
                    <span className="font-mono">{n.created_at}</span>
                  </div>
                  <div className="mt-2 text-sm text-slate-900">{n.note}</div>
                </div>
              ))}

              {(data.notes ?? []).length === 0 && <div className="text-sm text-slate-500">No notes yet.</div>}
            </div>
          </div>

          <div className="flex flex-col gap-2 md:flex-row md:items-end">
            <div className="flex-1">
              <div className="text-xs font-medium text-slate-500">Add Note</div>
              <input
                className="mt-1 w-full rounded-xl border border-slate-200 bg-white p-2 text-sm"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Technician assigned"
              />
            </div>
            <button
              className="rounded-xl border border-sky-600 bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700"
              onClick={() => void onAddNote()}
            >
              Add
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

