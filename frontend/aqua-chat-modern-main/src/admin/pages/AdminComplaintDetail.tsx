import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { adminApi, Complaint, ComplaintPriority, ComplaintStatus } from "../api";

const STATUSES: ComplaintStatus[] = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"];
const PRIORITIES: ComplaintPriority[] = ["LOW", "NORMAL", "HIGH", "URGENT"];

export default function AdminComplaintDetail() {
  const params = useParams();
  const ticketId = useMemo(() => params.ticketId || "", [params.ticketId]);
  const [data, setData] = useState<Complaint | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [assignedTo, setAssignedTo] = useState("");

  const load = async () => {
    if (!ticketId) return;
    try {
      setError(null);
      const complaint = await adminApi.getComplaint(ticketId);
      setData(complaint);
      setAssignedTo(complaint.assigned_to || "");
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

  const onPriorityChange = async (priority: ComplaintPriority) => {
    try {
      const res = await adminApi.updateComplaintPriority(ticketId, priority);
      setData(res.complaint);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onAssign = async () => {
    try {
      const res = await adminApi.assignComplaint(ticketId, assignedTo.trim());
      setData(res.complaint);
      setAssignedTo(res.complaint.assigned_to || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const [agentReply, setAgentReply] = useState("");
  const [isSendingReply, setIsSendingReply] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "open": return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "in_progress": return "bg-blue-100 text-blue-800 border-blue-200";
      case "resolved": return "bg-green-100 text-green-800 border-green-200";
      case "escalated": return "bg-red-100 text-red-800 border-red-200";
      default: return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case "open": return "";
      case "in_progress": return "";
      case "resolved": return "";
      case "escalated": return "";
      default: return "";
    }
  };

  const labelize = (value: string) =>
    value.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());

  const sendAgentReply = async () => {
    if (!agentReply.trim()) return;
    
    setIsSendingReply(true);
    try {
      // Here you would make an API call to send agent reply
      // Example: await adminApi.sendAgentReply(ticketId, agentReply);
      console.log('Agent reply sent:', agentReply);
      setAgentReply("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSendingReply(false);
    }
  };

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="m-0 text-3xl font-bold text-slate-900">Complaint Details</h1>
        <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1.5 font-mono text-sm font-semibold text-primary">
          {ticketId}
        </span>
        <button
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          onClick={() => void load()}
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <strong>Error:</strong> {error}
        </div>
      )}

      {data && (
        <>
          {/* Customer Information Card */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Customer Information</h2>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <div>
                  <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Customer Name</label>
                  <div className="mt-1 text-sm font-bold text-slate-900">{data.name}</div>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Area</label>
                  <div className="mt-1 text-sm font-bold text-slate-900">{data.area}</div>
                </div>
              </div>
              <div className="space-y-2">
                <div>
                  <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Phone/Contact</label>
                  <div className="mt-1 text-sm font-mono text-slate-900">{data.phone || 'Not provided'}</div>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Created Date</label>
                  <div className="mt-1 text-sm text-slate-900">
                    {new Date(data.created_at).toLocaleDateString('en-US', { 
                      weekday: 'long', 
                      year: 'numeric', 
                      month: 'long', 
                      day: 'numeric' 
                    })}
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Assigned To</label>
                  <div className="mt-1 text-sm font-bold text-slate-900">{data.assigned_to || "Unassigned"}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Issue Details Card */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Issue Details</h2>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Issue Description</label>
                <div className="mt-2 p-3 rounded-lg bg-slate-50 text-sm text-slate-900 leading-relaxed">
                  {data.issue}
                </div>
              </div>
              
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">Category</label>
                  <div className="mt-1 inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm font-semibold text-slate-800">
                    {labelize(data.category)}
                  </div>
                </div>
                <div>
                  <label htmlFor="complaint-priority" className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Priority
                  </label>
                  <select
                    id="complaint-priority"
                    className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary"
                    value={data.priority}
                    onChange={(e) => void onPriorityChange(e.target.value as ComplaintPriority)}
                  >
                    {PRIORITIES.map((priority) => (
                      <option key={priority} value={priority}>{priority}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="complaint-status" className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Current Status
                  </label>
                  <div className="mt-1">
                    <select
                      id="complaint-status"
                      className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary"
                      value={data.status as ComplaintStatus}
                      onChange={(e) => void onStatusChange(e.target.value as ComplaintStatus)}
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s.replace('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase() + char.toLowerCase().slice(1))}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                    Last Updated
                  </label>
                  <div className="mt-1 text-sm text-slate-900 font-mono">
                    {new Date(data.updated_at).toLocaleString()}
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                    SLA Due
                  </label>
                  <div className="mt-1 text-sm text-slate-900 font-mono">
                    {data.sla_due_at ? new Date(data.sla_due_at).toLocaleString() : "Not set"}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Staff Ownership</h2>
            <div className="flex flex-col gap-3 sm:flex-row">
              <input
                className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary"
                value={assignedTo}
                onChange={(e) => setAssignedTo(e.target.value)}
                placeholder="Technician, team, or staff member"
              />
              <button
                onClick={() => void onAssign()}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:brightness-95"
              >
                Save Assignment
              </button>
            </div>
          </div>

          {/* Agent Reply Box */}
          <div className="rounded-xl border border-primary/20 bg-primary/5 p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Agent Response</h2>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-primary uppercase tracking-wider">
                  Reply to Customer
                </label>
                <textarea
                  value={agentReply}
                  onChange={(e) => setAgentReply(e.target.value)}
                  placeholder="Type your response to the customer..."
                  className="mt-2 w-full rounded-lg border border-primary/30 bg-white px-4 py-3 text-sm resize-none focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary"
                  rows={4}
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => void sendAgentReply()}
                  disabled={!agentReply.trim() || isSendingReply}
                  className="flex-1 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isSendingReply ? 'Sending...' : 'Send Reply'}
                </button>
                <button
                  className="rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                  onClick={() => setAgentReply("")}
                >
                  Clear
                </button>
              </div>
            </div>
          </div>

          {/* Notes Section */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Internal Notes</h2>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                  Add Internal Note
                </label>
                <div className="mt-2 flex gap-3">
                  <input
                    className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Technician assigned, follow-up required, etc."
                  />
                  <button
                    onClick={() => void onAddNote()}
                    disabled={!note.trim()}
                    className="rounded-lg bg-slate-600 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Add Note
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                {(data.notes ?? []).map((n, idx) => (
                  <div key={idx} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2 text-xs text-slate-600">
                        <span className="inline-flex rounded-full border border-slate-300 bg-white px-2 py-1 font-medium">
                          {n.author}
                        </span>
                        <span className="font-mono">{new Date(n.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                    <div className="text-sm text-slate-900 leading-relaxed">{n.note}</div>
                  </div>
                ))}
                {(data.notes ?? []).length === 0 && (
                  <div className="text-center text-sm text-slate-500 py-8">
                    No internal notes yet
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

