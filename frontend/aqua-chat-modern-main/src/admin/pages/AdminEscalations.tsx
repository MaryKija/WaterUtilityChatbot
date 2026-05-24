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

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "urgent": return "bg-red-100 text-red-800 border-red-200";
      case "high": return "bg-orange-100 text-orange-800 border-orange-200";
      case "medium": return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "low": return "bg-green-100 text-green-800 border-green-200";
      default: return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "waiting": return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "active": return "bg-blue-100 text-blue-800 border-blue-200";
      case "closed": return "bg-green-100 text-green-800 border-green-200";
      default: return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "urgent": return "";
      case "high": return "";
      case "medium": return "";
      case "low": return "";
      default: return "";
    }
  };

  return (
    <div className="grid gap-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="m-0 text-2xl font-bold text-slate-900">Escalation Inbox</h2>
        <div className="flex gap-2">
          <button
            className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            onClick={() => void load()}
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-2xl font-bold text-slate-900">{items.length}</div>
          <div className="text-sm text-slate-600">Total Escalations</div>
        </div>
        <div className="bg-red-50 rounded-lg border border-red-200 p-4">
          <div className="text-2xl font-bold text-red-800">
            {items.filter(e => e.priority === 'URGENT').length}
          </div>
          <div className="text-sm text-red-600">Urgent</div>
        </div>
        <div className="bg-yellow-50 rounded-lg border border-yellow-200 p-4">
          <div className="text-2xl font-bold text-yellow-800">
            {items.filter(e => e.status === 'WAITING').length}
          </div>
          <div className="text-sm text-yellow-600">Waiting</div>
        </div>
        <div className="bg-blue-50 rounded-lg border border-blue-200 p-4">
          <div className="text-2xl font-bold text-blue-800">
            {items.filter(e => e.status === 'ACTIVE').length}
          </div>
          <div className="text-sm text-blue-600">Active</div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Enhanced Escalation Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead className="bg-slate-50">
              <tr className="text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                <th className="px-6 py-4 font-medium">ID</th>
                <th className="px-6 py-4 font-medium">User</th>
                <th className="px-6 py-4 font-medium">Priority</th>
                <th className="px-6 py-4 font-medium">Reason</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Created</th>
                <th className="px-6 py-4 font-medium text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.escalation_id} className="border-t border-slate-100 hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4">
                    <span className="font-mono text-sm font-semibold text-primary">{e.escalation_id}</span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium">{e.user_id}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold border ${getPriorityColor(e.priority || 'medium')}`}>
                      <span>{e.priority || 'Medium'}</span>
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm max-w-xs truncate" title={e.reason}>{e.reason}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold border ${getStatusColor(e.status)}`}>
                      <span>{e.status}</span>
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-slate-600">
                      {new Date(e.created_at).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex justify-center gap-2">
                      <Link
                        className={`inline-flex rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                          e.status === 'WAITING' 
                            ? 'border-green-200 bg-green-600 text-white hover:bg-green-700'
                            : 'border-primary bg-primary text-primary-foreground hover:brightness-95'
                        }`}
                        to={`/admin/escalations/${encodeURIComponent(e.escalation_id)}`}
                      >
                        {e.status === 'WAITING' ? 'Take Over' : 'Continue Chat'}
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td className="px-6 py-8 text-center text-slate-500" colSpan={7}>
                    <div className="text-lg font-medium">No escalations found</div>
                    <div className="text-sm text-slate-400 mt-1">
                      All customer interactions are being handled by the AI assistant
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

