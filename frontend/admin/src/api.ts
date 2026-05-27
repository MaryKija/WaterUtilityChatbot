const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("admin_token");
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${detail || res.statusText}`);
  }

  return (await res.json()) as T;
}

export type ComplaintStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";

export type ComplaintSummary = {
  ticket_id: string;
  issue: string;
  status: string;
  area: string;
};

export type Complaint = {
  ticket_id: string;
  name: string;
  area: string;
  issue: string;
  status: string;
  created_at: string;
  updated_at: string;
  assigned_to: string | null;
  notes: Array<{ note: string; author: string; created_at: string }>;
};

export type EscalationSummary = {
  escalation_id: string;
  ticket_id: string;
  user_id: string;
  reason: string;
  status: string;
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

export const api = {
  listComplaints: () => http<ComplaintSummary[]>("/admin/complaints"),
  getComplaint: (ticketId: string) => http<Complaint>(`/admin/complaints/${encodeURIComponent(ticketId)}`),
  updateComplaintStatus: (ticketId: string, status: ComplaintStatus) =>
    http<{ success: boolean; complaint: Complaint }>(
      `/admin/complaints/${encodeURIComponent(ticketId)}/status`,
      {
        method: "POST",
        body: JSON.stringify({ status }),
      },
    ),
  addComplaintNote: (ticketId: string, note: string) =>
    http<{ success: boolean; complaint: Complaint }>(
      `/admin/complaints/${encodeURIComponent(ticketId)}/note`,
      {
        method: "POST",
        body: JSON.stringify({ note }),
      },
    ),

  listEscalations: () => http<EscalationSummary[]>("/admin/escalations"),
  getEscalation: (escalationId: string) => http<Escalation>(`/admin/escalations/${encodeURIComponent(escalationId)}`),
  replyEscalation: (escalationId: string, message: string) =>
    http<{ success: boolean; escalation: Escalation }>(
      `/admin/escalations/${encodeURIComponent(escalationId)}/reply`,
      {
        method: "POST",
        body: JSON.stringify({ message }),
      },
    ),
  closeEscalation: (escalationId: string) =>
    http<{ success: boolean; escalation: Escalation }>(
      `/admin/escalations/${encodeURIComponent(escalationId)}/close`,
      { method: "POST" },
    ),
  login: (username: string, password: string) =>
    http<{ success: boolean; token?: string; user_id?: string; role?: string; message?: string }>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ username, password }),
      }
    ),
  getDashboardMetrics: () => http<any>("/admin/dashboard"),
};

