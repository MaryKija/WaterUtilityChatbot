import { useEffect, useState } from "react";
<<<<<<< HEAD
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
=======
import { Link } from "react-router-dom";
import { RefreshCw, Droplets } from "lucide-react";
import { adminApi, DashboardMetrics } from "../api";

const EMPTY_METRICS: DashboardMetrics = {
  total_complaints: 0,
  open_complaints: 0,
  resolved_complaints: 0,
  resolved_today: 0,
  escalations: 0,
  urgent_cases: 0,
  avg_response_time_ms: 0,
  avg_satisfaction: 0,
  common_intents: [],
  cases_by_category: [],
  cases_by_area: [],
  needs_attention: [],
  recent_feedback: [],
};

function metricHours(ms: number) {
  if (!ms) return "0h";
  return `${(ms / 1000 / 60 / 60).toFixed(1)}h`;
}

function labelize(value: string) {
  return value.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics>(EMPTY_METRICS);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setError(null);
      setMetrics(await adminApi.getDashboard());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const cards = [
    { label: "Total Complaints", value: metrics.total_complaints, tone: "text-slate-900" },
    { label: "Open Cases", value: metrics.open_complaints, tone: "text-amber-700" },
    { label: "Urgent / High", value: metrics.urgent_cases, tone: "text-red-700" },
    { label: "Escalations", value: metrics.escalations, tone: "text-orange-700" },
    { label: "Resolved Today", value: metrics.resolved_today, tone: "text-emerald-700" },
    { label: "Avg Response", value: metricHours(metrics.avg_response_time_ms), tone: "text-primary" },
    { label: "Satisfaction", value: metrics.avg_satisfaction ? `${metrics.avg_satisfaction.toFixed(1)}/5` : "No ratings", tone: "text-green-700" },
  ];

  return (
    <div className="grid gap-6">
      <div className="rounded-2xl border border-primary/10 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
              <Droplets className="h-6 w-6" />
            </span>
            <div>
              <p className="m-0 text-xs font-semibold uppercase tracking-normal text-primary">LgWSC admin</p>
              <h1 className="m-0 text-3xl font-bold text-slate-900">Operations dashboard</h1>
              <p className="mt-1 text-sm text-slate-600">Survey-aligned case workload, escalation, and feedback signals.</p>
            </div>
          </div>
          <button
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-primary/20 bg-white px-4 py-2 text-sm font-medium text-primary transition-colors hover:bg-primary/5"
            onClick={() => void load()}
          >
            <RefreshCw className="h-4 w-4" />
            Refresh data
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <strong>Error:</strong> {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
            <div key={card.label} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-primary/20">
            <div className="text-sm font-medium text-slate-600">{card.label}</div>
            <div className={`mt-2 text-2xl font-bold ${card.tone}`}>{card.value}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="m-0 text-lg font-semibold text-slate-900">Needs Attention</h2>
            <Link className="text-sm font-medium text-primary hover:brightness-90" to="/admin/complaints">
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {metrics.needs_attention.map((item) => (
              <Link
                key={item.ticket_id}
                to={`/admin/complaints/${encodeURIComponent(item.ticket_id)}`}
                className="block rounded-lg border border-slate-200 p-3 transition hover:bg-slate-50"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-mono text-sm font-semibold text-primary">{item.ticket_id}</span>
                  <span className="rounded-full bg-red-50 px-2 py-1 text-xs font-semibold text-red-700">{item.priority}</span>
                </div>
                <div className="mt-2 text-sm font-medium text-slate-900">{item.issue}</div>
                <div className="mt-1 text-xs text-slate-500">{item.area} | {item.status} | {item.assigned_to || "Unassigned"}</div>
              </Link>
            ))}
            {metrics.needs_attention.length === 0 && <div className="text-sm text-slate-500">No urgent unresolved cases.</div>}
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="m-0 text-lg font-semibold text-slate-900">Recent Feedback</h2>
          <div className="mt-4 space-y-3">
            {metrics.recent_feedback.map((item) => (
              <div key={item.feedback_id} className="rounded-lg border border-slate-200 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-900">{item.rating}/5</span>
                  <span className="text-xs text-slate-500">{new Date(item.timestamp).toLocaleString()}</span>
                </div>
                <div className="mt-1 text-sm text-slate-600">{item.text_feedback || "No written comment"}</div>
              </div>
            ))}
            {metrics.recent_feedback.length === 0 && <div className="text-sm text-slate-500">No feedback submitted yet.</div>}
          </div>
        </section>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="m-0 text-lg font-semibold text-slate-900">Cases by Category</h2>
          <div className="mt-4 space-y-2">
            {metrics.cases_by_category.map((item) => (
              <div key={item.category} className="flex items-center justify-between text-sm">
                <span className="text-slate-700">{labelize(item.category)}</span>
                <span className="font-semibold text-slate-900">{item.count}</span>
              </div>
            ))}
            {metrics.cases_by_category.length === 0 && <div className="text-sm text-slate-500">No complaint categories yet.</div>}
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="m-0 text-lg font-semibold text-slate-900">Cases by Area</h2>
          <div className="mt-4 space-y-2">
            {metrics.cases_by_area.map((item) => (
              <div key={item.area} className="flex items-center justify-between text-sm">
                <span className="text-slate-700">{item.area}</span>
                <span className="font-semibold text-slate-900">{item.count}</span>
              </div>
            ))}
            {metrics.cases_by_area.length === 0 && <div className="text-sm text-slate-500">No area data yet.</div>}
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="m-0 text-lg font-semibold text-slate-900">Top Intents</h2>
          <div className="mt-4 space-y-2">
            {metrics.common_intents.map((item) => (
              <div key={item.intent} className="flex items-center justify-between text-sm">
                <span className="text-slate-700">{labelize(item.intent)}</span>
                <span className="font-semibold text-slate-900">{item.count}</span>
              </div>
            ))}
            {metrics.common_intents.length === 0 && <div className="text-sm text-slate-500">No intent telemetry yet.</div>}
          </div>
        </section>
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
      </div>
    </div>
  );
}
<<<<<<< HEAD

=======
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
