import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { adminApi, ComplaintSummary } from "../api";

export default function AdminComplaints() {
  const [items, setItems] = useState<ComplaintSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setError(null);
      setItems(await adminApi.listComplaints());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");

  const filteredItems = items.filter((c) => {
    const matchesSearch = c.ticket_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         c.issue.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         c.area.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         c.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (c.assigned_to || "").toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" || c.status === statusFilter;
    const matchesPriority = priorityFilter === "all" || c.priority === priorityFilter;
    return matchesSearch && matchesStatus && matchesPriority;
  });

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "open": return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "in_progress": return "bg-blue-100 text-blue-800 border-blue-200";
      case "resolved": return "bg-green-100 text-green-800 border-green-200";
      case "escalated": return "bg-red-100 text-red-800 border-red-200";
      default: return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "urgent": return "bg-red-100 text-red-800 border-red-200";
      case "high": return "bg-orange-100 text-orange-800 border-orange-200";
      case "normal": return "bg-blue-100 text-blue-800 border-blue-200";
      default: return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  const labelize = (value: string) =>
    value.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case "open": return "";
      case "in_progress": return "";
      case "resolved": return "";
      case "escalated": return "";
      default: return "";
    }
  };

  return (
    <div className="grid gap-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="m-0 text-2xl font-bold text-slate-900">Complaints Management</h2>
        <div className="flex gap-2">
          <button
            className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            onClick={() => void load()}
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4 bg-white rounded-lg border border-slate-200 p-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search complaints..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <select
          aria-label="Filter complaints by status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="all">All Status</option>
          <option value="OPEN">Open</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="RESOLVED">Resolved</option>
          <option value="ESCALATED">Escalated</option>
        </select>
        <select
          aria-label="Filter complaints by priority"
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="all">All Priority</option>
          <option value="URGENT">Urgent</option>
          <option value="HIGH">High</option>
          <option value="NORMAL">Normal</option>
          <option value="LOW">Low</option>
        </select>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-2xl font-bold text-slate-900">{items.length}</div>
          <div className="text-sm text-slate-600">Total Complaints</div>
        </div>
        <div className="bg-white rounded-lg border border-yellow-200 p-4">
          <div className="text-2xl font-bold text-yellow-800">
            {items.filter(c => c.status === 'OPEN').length}
          </div>
          <div className="text-sm text-yellow-600">Open</div>
        </div>
        <div className="bg-white rounded-lg border border-blue-200 p-4">
          <div className="text-2xl font-bold text-blue-800">
            {items.filter(c => c.status === 'IN_PROGRESS').length}
          </div>
          <div className="text-sm text-blue-600">In Progress</div>
        </div>
        <div className="bg-white rounded-lg border border-green-200 p-4">
          <div className="text-2xl font-bold text-green-800">
            {items.filter(c => c.status === 'RESOLVED').length}
          </div>
          <div className="text-sm text-green-600">Resolved</div>
        </div>
        <div className="bg-white rounded-lg border border-red-200 p-4">
          <div className="text-2xl font-bold text-red-800">
            {items.filter(c => (c.priority === 'URGENT' || c.priority === 'HIGH') && c.status !== 'RESOLVED' && c.status !== 'CLOSED').length}
          </div>
          <div className="text-sm text-red-600">Needs Attention</div>
        </div>
      </div>

      {/* Enhanced Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead className="bg-slate-50">
              <tr className="text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                <th className="px-6 py-4 font-medium">Ticket ID</th>
                <th className="px-6 py-4 font-medium">Customer</th>
                <th className="px-6 py-4 font-medium">Issue</th>
                <th className="px-6 py-4 font-medium">Area</th>
                <th className="px-6 py-4 font-medium">Category</th>
                <th className="px-6 py-4 font-medium">Priority</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Assigned</th>
                <th className="px-6 py-4 font-medium">Created</th>
                <th className="px-6 py-4 font-medium text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((c) => (
                <tr key={c.ticket_id} className="border-t border-slate-100 hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4">
                    <span className="font-mono text-sm font-semibold text-primary">{c.ticket_id}</span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium">{c.name}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm max-w-xs truncate" title={c.issue}>{c.issue}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm">{c.area}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm">{labelize(c.category)}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold border ${getPriorityColor(c.priority)}`}>
                      {c.priority}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold border ${getStatusColor(c.status)}`}>
                      <span>{c.status}</span>
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-slate-700">{c.assigned_to || "Unassigned"}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-slate-600">
                      {new Date(c.created_at).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex justify-center gap-2">
                      <Link
                        className="inline-flex rounded-lg border border-primary bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:brightness-95"
                        to={`/admin/complaints/${encodeURIComponent(c.ticket_id)}`}
                      >
                        View Details
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredItems.length === 0 && (
                <tr>
                  <td className="px-6 py-8 text-center text-slate-500" colSpan={10}>
                    <div className="text-lg font-medium">No complaints found</div>
                    <div className="text-sm text-slate-400 mt-1">
                      {searchTerm || statusFilter !== "all" 
                        ? "Try adjusting your search or filter criteria"
                        : "No complaints have been submitted yet"}
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

