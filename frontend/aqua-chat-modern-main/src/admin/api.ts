const API_URL = (() => {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && !envUrl.includes("127.0.0.1") && !envUrl.includes("localhost")) {
    return envUrl.replace(/\/$/, "");
  }
  // Fallback to live Render production backend if hosted on Vercel or in production
  if (typeof window !== "undefined" && (window.location.hostname.includes("vercel.app") || !import.meta.env.DEV)) {
    return "https://waterutilitychatbot.onrender.com";
  }
  return ""; // dev/prod fallback: use relative path / Vite proxy
})();


function getAdminAuthHeader(): Record<string, string> {
  if (typeof window !== "undefined") {
    const storedToken = window.localStorage.getItem("admin_token");
    if (storedToken) {
      return { Authorization: `Bearer ${storedToken}` };
    }
  }
  return {};
}

/** Clear stored credentials and redirect to login. */
export function adminLogout() {
  window.localStorage.removeItem("admin_token");
  window.localStorage.removeItem("admin_role");
  window.location.replace("/admin/login");
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...getAdminAuthHeader(),
      ...(init?.headers || {}),
    },
  });

  // Token expired or revoked - clear storage and redirect to login
  if (res.status === 401 || res.status === 403) {
    adminLogout();
    throw new Error(`Session expired. Please log in again.`);
  }

  const contentType = res.headers.get("content-type") || "";
  const bodyText = await res.text().catch(() => "");

  if (!res.ok) {
    let detail = bodyText;
    if (contentType.includes("application/json") && bodyText) {
      try {
        const parsed = JSON.parse(bodyText) as { detail?: unknown; message?: unknown };
        detail = String(parsed.detail || parsed.message || bodyText);
      } catch {
        detail = bodyText;
      }
    }
    throw new Error(`HTTP ${res.status}: ${detail || res.statusText}`);
  }

  if (!contentType.includes("application/json")) {
    const snippet = bodyText.trim().slice(0, 80) || "empty response";
    throw new Error(`Expected JSON from ${path}, but received ${contentType || "unknown content type"}: ${snippet}`);
  }

  return JSON.parse(bodyText) as T;
}

export type ComplaintStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";
export type ComplaintPriority = "LOW" | "NORMAL" | "HIGH" | "URGENT";

export type ComplaintSummary = {
  ticket_id: string;
  issue: string;
  status: string;
  area: string;
  name: string;
  created_at: string;
  updated_at: string;
  assigned_to: string | null;
  category: string;
  priority: ComplaintPriority;
  sla_due_at: string | null;
};

export type Complaint = {
  ticket_id: string;
  name: string;
  area: string;
  issue: string;
  status: string;
  created_at: string;
  updated_at: string;
  phone: string | null;
  assigned_to: string | null;
  category: string;
  priority: ComplaintPriority;
  sla_due_at: string | null;
  notes: Array<{ note: string; author: string; created_at: string }>;
};

export type EscalationSummary = {
  escalation_id: string;
  ticket_id: string;
  user_id: string;
  reason: string;
  status: string;
  priority: string;
  created_at: string;
  updated_at: string;
};

export type Escalation = {
  escalation_id: string;
  ticket_id: string;
  user_id: string;
  reason: string;
  status: string;
  messages: Array<{ sender: "user" | "bot" | "agent"; text: string; created_at?: string }>;
  created_at: string;
  updated_at: string;
};

export type FeedbackItem = {
  feedback_id: string;
  session_id: string;
  user_id: string;
  rating: number;
  text_feedback: string | null;
  helpful: boolean;
  timestamp: string;
};

export type DashboardMetrics = {
  total_complaints: number;
  open_complaints: number;
  resolved_complaints: number;
  resolved_today: number;
  escalations: number;
  urgent_cases: number;
  avg_response_time_ms: number;
  avg_satisfaction: number;
  common_intents: Array<{ intent: string; count: number }>;
  cases_by_category: Array<{ category: string; count: number }>;
  cases_by_area: Array<{ area: string; count: number }>;
  needs_attention: ComplaintSummary[];
  recent_feedback: FeedbackItem[];
};

export const adminApi = {
  getDashboard: () => http<DashboardMetrics>("/admin/dashboard"),
  listComplaints: () => http<ComplaintSummary[]>("/admin/complaints"),
  getComplaint: (ticketId: string) => http<Complaint>(`/admin/complaints/${encodeURIComponent(ticketId)}`),
  updateComplaintStatus: (ticketId: string, status: ComplaintStatus) =>
    http<{ success: boolean; complaint: Complaint }>(
      `/admin/complaints/${encodeURIComponent(ticketId)}/status`,
      { method: "POST", body: JSON.stringify({ status }) },
    ),
  addComplaintNote: (ticketId: string, note: string) =>
    http<{ success: boolean; complaint: Complaint }>(
      `/admin/complaints/${encodeURIComponent(ticketId)}/note`,
      { method: "POST", body: JSON.stringify({ note }) },
    ),
  assignComplaint: (ticketId: string, assignedTo: string) =>
    http<{ success: boolean; complaint: Complaint }>(
      `/admin/complaints/${encodeURIComponent(ticketId)}/assign`,
      { method: "POST", body: JSON.stringify({ assigned_to: assignedTo }) },
    ),
  updateComplaintPriority: (ticketId: string, priority: ComplaintPriority) =>
    http<{ success: boolean; complaint: Complaint }>(
      `/admin/complaints/${encodeURIComponent(ticketId)}/priority`,
      { method: "POST", body: JSON.stringify({ priority }) },
    ),
  listFeedback: (limit = 20) => http<FeedbackItem[]>(`/admin/feedback?limit=${encodeURIComponent(String(limit))}`),

  listEscalations: () => http<EscalationSummary[]>("/admin/escalations"),
  getEscalation: (escalationId: string) => http<Escalation>(`/admin/escalations/${encodeURIComponent(escalationId)}`),
  replyEscalation: (escalationId: string, message: string) =>
    http<{ success: boolean; escalation: Escalation }>(
      `/admin/escalations/${encodeURIComponent(escalationId)}/reply`,
      { method: "POST", body: JSON.stringify({ message }) },
    ),
  closeEscalation: (escalationId: string) =>
    http<{ success: boolean; escalation: Escalation }>(
      `/admin/escalations/${encodeURIComponent(escalationId)}/close`,
      { method: "POST" },
    ),
};

