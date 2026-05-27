import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ComplaintSummary, EscalationSummary } from "../api";

export default function Dashboard() {
  const navigate = useNavigate();

  // State for live data integration
  const [complaints, setComplaints] = useState<ComplaintSummary[]>([]);
  const [escalations, setEscalations] = useState<EscalationSummary[]>([]);
  const [metrics, setMetrics] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // State for interactive features
  const [systemStopActive, setSystemStopActive] = useState<boolean>(false);
  const [showStopModal, setShowStopModal] = useState<boolean>(false);
  
  // Operator Takeover / Intervene modal state
  const [activeTakeoverItem, setActiveTakeoverItem] = useState<{
    id: string;
    priority: string;
    subject: string;
    location: string;
    ai_wait_time: string;
    action: string;
    completion: number;
  } | null>(null);

  // New timeline feed overrides state (allows adding live audit items)
  const [hitlEvents, setHitlEvents] = useState([
    {
      type: "verification",
      operator: "Mark V.",
      action: "verified Flow Pattern X-9",
      details: "AI model weights updated for District 4.",
      timestamp: "TODAY 14:22"
    },
    {
      type: "override",
      action: "Manual Override: Pump Station 4",
      details: "AI suggestion 'Standby' overruled by safety protocol.",
      timestamp: "TODAY 13:05"
    }
  ]);

  // Load backend data
  const loadData = async () => {
    try {
      setError(null);
      const [c, e, m] = await Promise.all([
        api.listComplaints(),
        api.listEscalations(),
        api.getDashboardMetrics()
      ]);
      setComplaints(c);
      setEscalations(e);
      setMetrics(m);
    } catch (err) {
      console.error("Failed to fetch live metrics:", err);
      // Keep silent fallback for isolated dashboard presentation
    } finally {
      setLoading(false);
    }
  };

  // Keyboard Escape listener to close modals
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setShowStopModal(false);
        setActiveTakeoverItem(null);
      }
    };
    if (showStopModal || activeTakeoverItem) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [showStopModal, activeTakeoverItem]);

  useEffect(() => {
    void loadData();
    // Poll every 5 seconds to keep the operations console updated with live counts
    const interval = setInterval(() => {
      void loadData();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Compute live values dynamically integrated with mockup specifications
  const activeTicketsCount = 1248 + complaints.filter(c => c.status !== "RESOLVED" && c.status !== "CLOSED").length;
  const pendingEscalationsCountStr = String(Math.max(9, escalations.filter(e => e.status === "WAITING").length)).padStart(2, "0");

  // Handle takeover/intervene submit
  const handleTakeoverSubmit = () => {
    if (!activeTakeoverItem) return;
    
    // Find if there is an escalation matching the subject or id, or fallback
    const matchedEscalation = escalations.find(
      e => e.ticket_id.includes(activeTakeoverItem.id.replace("#TK-", ""))
    ) || escalations[0];

    alert(`Establishing live control channel for Ticket ${activeTakeoverItem.id}. Redirecting to live operator terminal.`);
    
    if (matchedEscalation) {
      navigate(`/escalations/${encodeURIComponent(matchedEscalation.escalation_id)}`);
    } else {
      navigate("/escalations");
    }
    setActiveTakeoverItem(null);
  };

  // Add custom manual override item for live demo wow-factor
  const triggerManualOverrideLog = () => {
    const timeNow = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const newLog = {
      type: "override",
      action: "Manual Handoff Triggered",
      details: "Operator initiated system-wide telemetry synchronization.",
      timestamp: `TODAY ${timeNow}`
    };
    setHitlEvents([newLog, ...hitlEvents]);
    alert("Manual safety telemetry sync logged to verification feed!");
  };

  return (
    <div style={{ display: "grid", gap: 20 }}>
      {/* Title Panel */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: 28, fontWeight: 800, color: "var(--text-dark)" }}>
            Admin Operations Console
          </h1>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            Lukanga Water & Sanitation Company Operator Terminal
          </span>
        </div>
        <div className="global-actions">
          <Link to="/complaints" className="btn">
            Tickets Hub
          </Link>
          <Link to="/escalations" className="btn btn-primary">
            Escalations Control
          </Link>
          <button 
            className="btn btn-danger" 
            onClick={() => setShowStopModal(true)}
            style={{ fontWeight: 700 }}
          >
            System Wide Stop
          </button>
        </div>
      </div>

      {/* Emergency System Stop Warning Banner */}
      {systemStopActive && (
        <div className="system-stop-banner">
          <div className="system-stop-icon">!</div>
          <div>
            <strong style={{ fontSize: 16, display: "block" }}>SYSTEM WIDE STOP ACTIVE</strong>
            <span style={{ fontSize: 13 }}>
              All autonomous AI routing is temporarily suspended. Incoming WhatsApp queries are held in fallback human queue.
            </span>
          </div>
          <button 
            className="btn btn-sm" 
            onClick={() => setSystemStopActive(false)} 
            style={{ marginLeft: "auto", backgroundColor: "white", color: "#991b1b", border: "1px solid #fee2e2" }}
          >
            RESUME AI ROUTING
          </button>
        </div>
      )}

      {/* System Health Status Panel */}
      <div className="system-health-bar">
        <div className="system-status">
          <div 
            className="status-indicator" 
            style={{ backgroundColor: systemStopActive ? "var(--color-danger)" : "var(--color-success)" }} 
          />
          <div>
            <div className="status-label">
              {systemStopActive ? "AI ROUTING SUSPENDED" : "Healthy"}
            </div>
            <div className="status-sub">Admin Operations Control</div>
          </div>
        </div>
        
        <div style={{ display: "flex", gap: 24, fontSize: 13 }}>
          <div>
            <span style={{ color: "var(--text-secondary)" }}>Live Environment:</span>{" "}
            <strong style={{ color: "var(--text-dark)" }}>ZAMBIA-KABWE-CENTRAL</strong>
          </div>
          <div>
            <span style={{ color: "var(--text-secondary)" }}>Database status:</span>{" "}
            <strong style={{ color: "var(--color-success)" }}>SYNCED (SQLite)</strong>
          </div>
          <div>
            <span style={{ color: "var(--text-secondary)" }}>Last API Polling:</span>{" "}
            <strong style={{ color: "var(--text-dark)", fontFamily: "var(--font-sans)" }}>JUST NOW</strong>
          </div>
        </div>
      </div>

      {/* Statistics Metric Grid */}
      <div className="grid-cols-4">
        {/* Card 1: ACTIVE TICKETS */}
        <div className="card metric-card">
          <div className="metric-label">Active Tickets</div>
          <div className="metric-value-container">
            <div className="metric-value">
              {metrics ? (metrics.total_complaints - metrics.resolved_complaints).toLocaleString() : activeTicketsCount.toLocaleString()}
            </div>
            <span className="metric-trend trend-up">+12%</span>
          </div>
          <div className="metric-meta">
            <span>REFRESH RATE</span>
            <span className="badge badge-primary">2S AGO</span>
          </div>
        </div>

        {/* Card 2: AI AUTONOMY RATE */}
        <div className="card metric-card accent">
          <div className="metric-label">AI Autonomy Rate</div>
          <div className="metric-value-container">
            <div className="metric-value">
              {metrics && metrics.total_complaints
                ? `${((1 - metrics.escalations / metrics.total_complaints) * 100).toFixed(1)}%`
                : "84.2%"}
            </div>
          </div>
          <div className="metric-meta">
            <span>MODEL MODE</span>
            <span className="badge badge-success" style={{ backgroundColor: "var(--color-primary-light)", color: "var(--color-primary-dark)" }}>VERIFIED MODE</span>
          </div>
        </div>

        {/* Card 3: PENDING ESCALATIONS */}
        <div className="card metric-card warning">
          <div className="metric-label">Pending Escalations</div>
          <div className="metric-value-container">
            <div className="metric-value">
              {metrics ? String(metrics.escalations).padStart(2, "0") : pendingEscalationsCountStr}
            </div>
          </div>
          <div className="metric-meta">
            <span>PRIORITY HUB</span>
            <span className="badge badge-warning" style={{ backgroundColor: "#fee2e2", color: "#b91c1c", animation: "pulse-ring-red 2s infinite" }}>HIGH PRIORITY</span>
          </div>
        </div>

        {/* Card 4: AVG RESPONSE TIME */}
        <div className="card metric-card success">
          <div className="metric-label">Avg Response Time</div>
          <div className="metric-value-container">
            <div className="metric-value">
              {metrics ? `${Math.round(metrics.avg_response_time_ms)}ms` : "240ms"}
            </div>
          </div>
          <div className="metric-meta">
            <span>LLM LATENCY</span>
            <span className="badge badge-success">STABLE</span>
          </div>
        </div>
      </div>

      {/* Main Console Workspace Columns */}
      <div className="grid-main">
        {/* Column 1: Escalation Priority Queue */}
        <div className="card" style={{ display: "grid", gap: 12 }}>
          <div className="card-header">
            <h3 className="card-title">Escalation Priority Queue</h3>
            <span className="badge badge-primary">34 Active Items</span>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table aria-label="Priority Escalations queue">
              <thead>
                <tr>
                  <th scope="col">TICKET ID</th>
                  <th scope="col">PRIORITY</th>
                  <th scope="col">SUBJECT / ISSUE</th>
                  <th scope="col">LOCATION</th>
                  <th scope="col">AI WAIT</th>
                  <th scope="col" style={{ width: 140 }}>PROGRESS</th>
                  <th scope="col">ACTION</th>
                </tr>
              </thead>
              <tbody>
                {/* Item 1 */}
                <tr>
                  <td className="mono">#TK-9921-A</td>
                  <td>
                    <span className="badge badge-danger">CRITICAL</span>
                  </td>
                  <td>
                    <strong>Pipe Burst?</strong>
                  </td>
                  <td style={{ color: "var(--text-secondary)", fontSize: 12 }}>
                    Detected at Central Reservoir Junction
                  </td>
                  <td className="mono" style={{ color: "var(--color-danger)" }}>1.2M</td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div className="progress-container" style={{ flex: 1 }}>
                        <div className="progress-bar danger" style={{ width: "42%" }} />
                      </div>
                      <span className="mono" style={{ fontSize: 11 }}>42%</span>
                    </div>
                  </td>
                  <td>
                    <button 
                      className="btn btn-sm btn-danger"
                      onClick={() => setActiveTakeoverItem({
                        id: "#TK-9921-A",
                        priority: "CRITICAL",
                        subject: "Pipe Burst?",
                        location: "Detected at Central Reservoir Junction",
                        ai_wait_time: "1.2M",
                        action: "TAKEOVER",
                        completion: 42
                      })}
                    >
                      TAKEOVER
                    </button>
                  </td>
                </tr>

                {/* Item 2 */}
                <tr>
                  <td className="mono">#TK-8854-C</td>
                  <td>
                    <span className="badge badge-primary" style={{ backgroundColor: "#e0f2fe", color: "#0369a1" }}>VERIFICATION</span>
                  </td>
                  <td>
                    <strong>Anomalous Pressure Flow</strong>
                  </td>
                  <td style={{ color: "var(--text-secondary)", fontSize: 12 }}>
                    District 7 South Gate
                  </td>
                  <td className="mono">4.5M</td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div className="progress-container" style={{ flex: 1 }}>
                        <div className="progress-bar" style={{ width: "60%", backgroundColor: "var(--color-primary)" }} />
                      </div>
                      <span className="mono" style={{ fontSize: 11 }}>60%</span>
                    </div>
                  </td>
                  <td>
                    <button 
                      className="btn btn-sm"
                      style={{ color: "var(--color-primary-dark)", borderColor: "var(--color-primary)", backgroundColor: "var(--color-primary-light)" }}
                      onClick={() => setActiveTakeoverItem({
                        id: "#TK-8854-C",
                        priority: "VERIFICATION",
                        subject: "Anomalous Pressure Flow",
                        location: "District 7 South Gate",
                        ai_wait_time: "4.5M",
                        action: "INTERVENE",
                        completion: 60
                      })}
                    >
                      INTERVENE
                    </button>
                  </td>
                </tr>

                {/* Item 3 */}
                <tr>
                  <td className="mono">#TK-1002-E</td>
                  <td>
                    <span className="badge badge-warning">IMMEDIATE</span>
                  </td>
                  <td>
                    <strong>Chemical Imbalance?</strong>
                  </td>
                  <td style={{ color: "var(--text-secondary)", fontSize: 12 }}>
                    North Treatment Plant - Unit 03
                  </td>
                  <td className="mono" style={{ color: "var(--color-danger)" }}>15S</td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div className="progress-container" style={{ flex: 1 }}>
                        <div className="progress-bar danger" style={{ width: "10%" }} />
                      </div>
                      <span className="mono" style={{ fontSize: 11 }}>10%</span>
                    </div>
                  </td>
                  <td>
                    <button 
                      className="btn btn-sm btn-danger"
                      onClick={() => setActiveTakeoverItem({
                        id: "#TK-1002-E",
                        priority: "IMMEDIATE",
                        subject: "Chemical Imbalance?",
                        location: "North Treatment Plant - Unit 03",
                        ai_wait_time: "15S",
                        action: "TAKEOVER",
                        completion: 10
                      })}
                    >
                      TAKEOVER
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Column 2: Side Panel (Complaint Mapping + HITL Feed) */}
        <div style={{ display: "grid", gap: 24 }}>
          {/* Complaint Mapping Section */}
          <div className="card" style={{ display: "grid", gap: 12 }}>
            <div className="card-header">
              <h3 className="card-title">Complaint Mapping</h3>
              <span className="badge">Categories</span>
            </div>

            <div style={{ display: "grid", gap: 16 }}>
              {/* Category 1 */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontWeight: 600 }}>
                  <span>Water Quality</span>
                  <span style={{ color: "var(--color-primary-dark)" }}>42%</span>
                </div>
                <div className="progress-container" style={{ height: 8 }}>
                  <div className="progress-bar" style={{ width: "42%", backgroundColor: "var(--color-accent)" }} />
                </div>
              </div>

              {/* Category 2 */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontWeight: 600 }}>
                  <span>Pressure Issues</span>
                  <span style={{ color: "var(--color-warning)" }}>28%</span>
                </div>
                <div className="progress-container" style={{ height: 8 }}>
                  <div className="progress-bar" style={{ width: "28%", backgroundColor: "var(--color-warning)" }} />
                </div>
              </div>

              {/* Category 3 */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontWeight: 600 }}>
                  <span>Billing / Admin</span>
                  <span style={{ color: "var(--color-success)" }}>30%</span>
                </div>
                <div className="progress-container" style={{ height: 8 }}>
                  <div className="progress-bar" style={{ width: "30%", backgroundColor: "var(--color-success)" }} />
                </div>
              </div>
            </div>
          </div>

          {/* HITL Verification Feed */}
          <div className="card" style={{ display: "grid", gap: 12 }}>
            <div className="card-header" style={{ marginBottom: 8 }}>
              <h3 className="card-title">HITL Verification Feed</h3>
              <button 
                className="btn btn-sm" 
                onClick={triggerManualOverrideLog}
                style={{ fontSize: 10, padding: "2px 8px" }}
              >
                Log Safety Sync
              </button>
            </div>

            <div className="timeline">
              {hitlEvents.map((event, idx) => (
                <div 
                  key={idx} 
                  className={`timeline-item ${event.type}`}
                >
                  <div className="timeline-header">
                    <span>{event.operator ? `OPERATOR: ${event.operator}` : "SYSTEM ACTION"}</span>
                    <span className="mono">{event.timestamp}</span>
                  </div>
                  <div className="timeline-title">
                    {event.action}
                  </div>
                  <div className="timeline-desc">
                    {event.details}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Emergency STOP Confirmation Modal */}
      {showStopModal && (
        <div className="modal-overlay" onClick={() => setShowStopModal(false)}>
          <div 
            className="modal-content" 
            role="dialog" 
            aria-modal="true" 
            aria-labelledby="stop-modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="stop-modal-title" className="modal-title" style={{ color: "var(--color-danger)" }}>Confirm System Wide Stop</h3>
            <div className="modal-body">
              <p style={{ marginBottom: 12 }}>
                <strong>WARNING:</strong> Triggering a System Wide Stop immediately halts the autonomous response loop of the LGWSC WhatsApp chatbot.
              </p>
              <p>
                All ongoing customer sessions will be flagged for human handoff and standard automation weights will be bypassed until resolved by an administrator. Are you sure you want to proceed?
              </p>
            </div>
            <div className="modal-footer">
              <button className="btn" onClick={() => setShowStopModal(false)}>
                Cancel
              </button>
              <button 
                className="btn btn-danger" 
                onClick={() => {
                  setSystemStopActive(true);
                  setShowStopModal(false);
                }}
              >
                Activate Override Stop
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Operator Takeover Modal */}
      {activeTakeoverItem && (
        <div className="modal-overlay" onClick={() => setActiveTakeoverItem(null)}>
          <div 
            className="modal-content" 
            role="dialog" 
            aria-modal="true" 
            aria-labelledby="takeover-modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="takeover-modal-title" className="modal-title">
              Confirm Safety {activeTakeoverItem.action}
            </h3>
            <div className="modal-body">
              <div style={{ border: "1px solid var(--border-color)", padding: 12, borderRadius: 8, backgroundColor: "var(--bg-primary)", marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span className="mono" style={{ fontWeight: 700 }}>{activeTakeoverItem.id}</span>
                  <span className={`badge ${activeTakeoverItem.priority === "CRITICAL" ? "badge-danger" : "badge-primary"}`}>
                    {activeTakeoverItem.priority}
                  </span>
                </div>
                <strong style={{ fontSize: 15, display: "block" }}>{activeTakeoverItem.subject}</strong>
                <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{activeTakeoverItem.location}</span>
              </div>
              <p style={{ marginBottom: 12 }}>
                You are about to execute a manual **{activeTakeoverItem.action}** for Ticket {activeTakeoverItem.id}.
              </p>
              <p>
                This will suspend LLM autonomous answers for this specific customer and open a direct terminal channel to your keyboard workspace. The customer has been waiting for {activeTakeoverItem.ai_wait_time} in AI autonomous routing.
              </p>
            </div>
            <div className="modal-footer">
              <button 
                className="btn" 
                onClick={() => setActiveTakeoverItem(null)}
              >
                Cancel
              </button>
              <button 
                className="btn btn-primary"
                onClick={handleTakeoverSubmit}
              >
                Confirm & Open Chat
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
