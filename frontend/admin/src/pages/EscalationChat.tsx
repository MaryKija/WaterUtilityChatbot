import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, Escalation } from "../api";

export default function EscalationChat() {
  const params = useParams();
  const navigate = useNavigate();
  const escalationId = useMemo(() => params.escalationId || "", [params.escalationId]);
  
  const [data, setData] = useState<Escalation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  
  // Real-time operational session timer (starts at 04:12 as in mockup)
  const [sessionSeconds, setSessionSeconds] = useState(252);
  
  // Sidebar active control menu index
  const [activeMenu, setActiveMenu] = useState("Live Stream");

  const load = async () => {
    if (!escalationId) return;
    try {
      setError(null);
      const res = await api.getEscalation(escalationId);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    void load();
    // Light polling for real-time updates
    const t = window.setInterval(() => void load(), 2000);
    return () => window.clearInterval(t);
  }, [escalationId]);

  // Session duration timer counting up
  useEffect(() => {
    const interval = setInterval(() => {
      setSessionSeconds(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const formatSessionTime = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const onSend = async () => {
    const msg = reply.trim();
    if (!msg) return;
    try {
      await api.replyEscalation(escalationId, msg);
      setReply("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onClose = async () => {
    if (!window.confirm("Are you sure you want to terminate takeover and return chat control to AI system?")) {
      return;
    }
    try {
      await api.closeEscalation(escalationId);
      alert("Takeover stopped. Session closed successfully.");
      navigate("/escalations");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  // Prefill text field helper for suggestions
  const handlePrefill = (text: string) => {
    setReply(text);
  };

  // Merge backend messages with high-fidelity mockup conversation baseline
  const mergedMessages = useMemo(() => {
    const baseline = [
      {
        sender: "bot",
        text: "I've detected a significant drop in your water pressure, Sarah. I am currently running a grid diagnostic to identify the source of the blockage. Please hold for one moment.",
        time: "14:23:45"
      },
      {
        sender: "user",
        text: "It's completely gone now! I have guests coming over in an hour. This is the third time this month there's been an issue. Can you just send someone?",
        time: "14:24:12"
      },
      {
        sender: "agent",
        text: "Hello Sarah, I'm taking over from the AI. I see the pressure at your specific meter is 32 PSI, which is well below normal. I'm investigating the main line valve status right now.",
        time: "14:24:58"
      }
    ];

    if (!data) return baseline;
    
    // Filter out messages from the backend that are already represented by baseline text to prevent duplicates
    const backendMsgs = (data.messages ?? []).filter(
      (m) => !baseline.some((b) => b.text.toLowerCase().trim() === m.text.toLowerCase().trim())
    );

    return [
      ...baseline,
      ...backendMsgs.map((m) => ({
        sender: m.sender,
        text: m.text,
        time: m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : "Just now"
      }))
    ];
  }, [data]);

  return (
    <div style={{ display: "grid", gap: 16 }}>
      
      {/* 1. Status Bar */}
      <div className="takeover-status-bar" role="status">
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div className="takeover-status-active">
            <span className="takeover-status-dot"></span>
            <span>TAKEOVER ACTIVE</span>
          </div>
          <span style={{ width: 1, height: 16, backgroundColor: "var(--border-color)" }} />
          <span className="mono" style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            SESSION TICKET: <strong style={{ color: "var(--text-dark)" }}>{data?.ticket_id || "#TK-9921-A"}</strong>
          </span>
          <span style={{ width: 1, height: 16, backgroundColor: "var(--border-color)" }} />
          <span className="mono" style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            ID: <strong style={{ color: "var(--text-dark)" }}>{escalationId}</strong>
          </span>
        </div>
        
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-secondary)" }}>
            <span className="material-icons" style={{ fontSize: 16, color: "var(--color-primary)" }}>schedule</span>
            <span className="mono">DURATION: <strong>{formatSessionTime(sessionSeconds)}</strong></span>
          </div>
          <button 
            className="btn btn-sm" 
            onClick={() => void load()} 
            title="Refresh Live Data Feed"
            style={{ padding: "6px 12px" }}
          >
            <span className="material-icons" style={{ fontSize: 14 }}>sync</span>
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="card" style={{ borderColor: "#fca5a5", color: "#b91c1c", backgroundColor: "#fef2f2", display: "flex", alignItems: "center", gap: 8 }}>
          <span className="material-icons">error_outline</span>
          <strong>Operational Error:</strong> {error}
        </div>
      )}

      {/* 2. Main Takeover Grid Layout */}
      <div className="takeover-grid">
        
        {/* Left Control Sidebar */}
        <aside className="takeover-sidebar-left" aria-label="Control Center">
          <div className="card" style={{ padding: 16, display: "flex", flex: "1 0 auto", flexDirection: "column", gap: 16 }}>
            <div>
              <h3 className="card-title" style={{ fontSize: 14, marginBottom: 4, display: "flex", alignItems: "center", gap: 6 }}>
                <span className="material-icons" style={{ color: "var(--color-primary)" }}>settings_input_hdmi</span>
                Control Center
              </h3>
              <div style={{ fontSize: 11, color: "var(--text-light)", fontWeight: 700, letterSpacing: "0.05em" }}>
                SYSTEM OVERRIDE V4.2-A
              </div>
            </div>

            <nav style={{ display: "grid", gap: 6 }}>
              {[
                { label: "Live Stream", icon: "radio_button_checked" },
                { label: "AI Insights", icon: "psychology" },
                { label: "Manual Override", icon: "settings_input_component" },
                { label: "Analytics", icon: "query_stats" },
                { label: "Reports", icon: "description" }
              ].map((item) => (
                <button
                  key={item.label}
                  onClick={() => setActiveMenu(item.label)}
                  className={`takeover-menu-item ${activeMenu === item.label ? "active" : ""}`}
                >
                  <span className="material-icons">{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              ))}
            </nav>

            <span style={{ height: 1, backgroundColor: "var(--border-color)", margin: "8px 0" }} />

            <div style={{ display: "grid", gap: 6 }}>
              <button 
                onClick={() => alert("Connecting to LgWSC Utility Operator Live Desk support pipeline...")}
                className="takeover-menu-item"
              >
                <span className="material-icons">contact_support</span>
                <span>Support Desk</span>
              </button>
              <button 
                onClick={() => navigate("/diagnostics")} 
                className="takeover-menu-item"
              >
                <span className="material-icons">terminal</span>
                <span>System Diagnostics</span>
              </button>
            </div>

            <div style={{ marginTop: "auto", paddingTop: 16 }}>
              <button
                className="btn btn-danger"
                onClick={() => void onClose()}
                style={{
                  width: "100%",
                  padding: "12px",
                  fontWeight: 800,
                  fontSize: 12,
                  letterSpacing: "0.05em",
                  textTransform: "uppercase",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  boxShadow: "0 4px 12px rgba(239, 68, 68, 0.2)"
                }}
              >
                <span className="material-icons">power_settings_new</span>
                EMERGENCY STOP
              </button>
              <div style={{ textAlign: "center", fontSize: 10, color: "var(--text-light)", marginTop: 8 }}>
                Closes handover & returns control to AI
              </div>
            </div>
          </div>
        </aside>

        {/* Center Main Column */}
        <section style={{ display: "grid", gap: 16 }} aria-label="Operational Desk">
          
          {/* Critical Grid Warning Alert Banner */}
          <div 
            className="system-stop-banner" 
            style={{ 
              margin: 0, 
              padding: "14px 18px", 
              backgroundColor: "var(--color-danger-light)", 
              borderColor: "var(--color-danger)",
              borderRadius: "var(--radius-md)",
              display: "flex",
              alignItems: "center",
              gap: 12
            }}
          >
            <div className="system-stop-icon" style={{ width: 28, height: 28, fontSize: 14 }}>
              <span className="material-icons">warning</span>
            </div>
            <div style={{ flex: 1 }}>
              <h4 style={{ fontSize: 13, fontWeight: 700, margin: 0, color: "#991b1b" }}>
                Critical Pressure Outage Detected
              </h4>
              <p style={{ fontSize: 11.5, margin: "2px 0 0", color: "#b91c1c", lineHeight: 1.4 }}>
                Neighboring node <strong>NW-Grid-883</strong> is now reporting similar pressure failures. Trunk validation is strongly recommended.
              </p>
            </div>
          </div>

          {/* Double Info Context Block */}
          <div className="customer-context-grid">
            
            {/* Customer profile snippet */}
            <div className="context-card">
              <span className="context-label">Customer Profile</span>
              <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "4px 0" }}>
                <span className="material-icons" style={{ color: "var(--color-primary)", fontSize: 20 }}>account_circle</span>
                <span className="context-value" style={{ fontSize: 15 }}>Sarah Jenkins</span>
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                <span className="badge badge-primary">Gold User</span>
                <span className="badge badge-warning" style={{ fontWeight: 800 }}>HIGH PRIORITY</span>
              </div>
              <span className="context-subtext" style={{ marginTop: 8 }}>
                Member since Oct 2021 | Cust ID: #8821-X
              </span>
            </div>

            {/* Live technical context metrics */}
            <div className="context-card" style={{ borderLeft: "4px solid var(--color-danger)" }}>
              <span className="context-label">Live Tech Context</span>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", margin: "4px 0" }}>
                <span className="context-value" style={{ color: "var(--color-danger)", fontSize: 20 }}>32 PSI</span>
                <span className="badge badge-danger">CRITICAL LOW</span>
              </div>
              <span style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 500 }}>
                Metric: <strong>Live Water Pressure</strong> (Optimal: 60 PSI)
              </span>
              <span className="context-subtext" style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 4 }}>
                <span className="material-icons" style={{ fontSize: 12 }}>location_on</span>
                Node: NW-Grid-882 (45.52 / -122.67)
              </span>
            </div>
          </div>

          {/* Interaction History timeline preview (collapsible-style card) */}
          <div className="card" style={{ padding: 14 }}>
            <h4 className="card-title" style={{ fontSize: 12, marginBottom: 10, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 6 }}>
              <span className="material-icons" style={{ fontSize: 16 }}>history</span>
              AI DIAGNOSTIC INTERACTION HISTORY
            </h4>
            <div style={{ display: "flex", gap: 24, overflowX: "auto", paddingBottom: 4 }}>
              {[
                { time: "14:22", text: "AI initiated diagnostics" },
                { time: "14:18", text: "Automated alert triggered" },
                { time: "Oct 12", text: "Regular maintenance clear" }
              ].map((h, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                  <div style={{ display: "flex", flexDirection: "column" }}>
                    <span className="mono" style={{ fontSize: 10, color: "var(--color-primary)", fontWeight: 700 }}>{h.time}</span>
                    <span style={{ fontSize: 11.5, color: "var(--text-primary)", fontWeight: 500 }}>{h.text}</span>
                  </div>
                  {i < 2 && <span className="material-icons" style={{ color: "var(--border-color)", fontSize: 16 }}>arrow_forward</span>}
                </div>
              ))}
            </div>
          </div>

          {/* Core Chat Console */}
          <div className="card" style={{ display: "grid", gap: 12, padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border-color)", paddingBottom: 10 }}>
              <h3 className="card-title" style={{ fontSize: 14, margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
                <span className="material-icons" style={{ color: "var(--color-primary)" }}>chat</span>
                Live Console Feed
              </h3>
              <span className="badge badge-success" style={{ padding: "4px 10px" }}>CONNECTED</span>
            </div>

            {/* Conversation Messages Container */}
            <div 
              style={{ 
                display: "flex", 
                flexDirection: "column", 
                gap: 12, 
                maxHeight: "380px", 
                minHeight: "280px", 
                overflowY: "auto", 
                padding: "8px", 
                background: "#f8fafc", 
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-color)"
              }}
            >
              {mergedMessages.map((m, idx) => {
                let senderClass = "user";
                let senderDisplayName = "Sarah Jenkins";
                
                if (m.sender === "bot" || m.sender === "AI SYSTEM") {
                  senderClass = "bot";
                  senderDisplayName = "AI SYSTEM";
                } else if (m.sender === "agent" || m.sender === "OPERATOR (YOU)") {
                  senderClass = "agent";
                  senderDisplayName = "OPERATOR (YOU)";
                }

                return (
                  <div 
                    key={idx} 
                    className={`chat-msg-bubble ${senderClass}`}
                  >
                    <div className="chat-msg-meta">
                      <strong style={{ textTransform: "uppercase", fontSize: 10 }}>{senderDisplayName}</strong>
                      <span className="mono" style={{ fontSize: 9 }}>{m.time}</span>
                    </div>
                    <div style={{ whiteSpace: "pre-wrap" }}>{m.text}</div>
                  </div>
                );
              })}
              {mergedMessages.length === 0 && (
                <div style={{ textAlign: "center", color: "var(--text-light)", padding: "40px 0" }}>
                  <span className="material-icons" style={{ fontSize: 40, display: "block", marginBottom: 8 }}>forum</span>
                  No messages recorded in this escalation pipeline.
                </div>
              )}
            </div>

            {/* Interactive Suggested Quick Replies */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>Suggested replies:</span>
              <button 
                className="suggested-reply-btn"
                onClick={() => handlePrefill("I can dispatch a field technician to investigate the line blockage at your property immediately.")}
              >
                "I can dispatch..."
              </button>
              <button 
                className="suggested-reply-btn"
                onClick={() => handlePrefill("Let me check the status of the main pressure valve NW-8.")}
              >
                "Check valve NW-8"
              </button>
            </div>

            {/* TextInput Action Area */}
            <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: 12, display: "flex", gap: 10, alignItems: "flex-end" }}>
              <button 
                className="btn" 
                title="Add Attachment"
                onClick={() => alert("Upload action triggered (File limit 10MB).")}
                style={{ padding: 10, borderRadius: 10 }}
              >
                <span className="material-icons">attach_file</span>
              </button>
              
              <button 
                className="btn" 
                title="Insert Emoji"
                onClick={() => handlePrefill(reply + " 😊")}
                style={{ padding: 10, borderRadius: 10 }}
              >
                <span className="material-icons">sentiment_satisfied_alt</span>
              </button>

              <div style={{ flex: 1 }}>
                <textarea 
                  value={reply} 
                  onChange={(e) => setReply(e.target.value)} 
                  placeholder="Type message to Sarah..." 
                  rows={2}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: 10,
                    border: "1px solid var(--border-color)",
                    fontSize: 13.5,
                    resize: "none",
                    fontFamily: "var(--font-sans)",
                    outline: "none"
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void onSend();
                    }
                  }}
                />
              </div>
              
              <button 
                className="btn btn-primary" 
                onClick={() => void onSend()}
                style={{ padding: "12px 20px", borderRadius: 10, display: "flex", gap: 6, fontWeight: 700 }}
              >
                <span>Send</span>
                <span className="material-icons">send</span>
              </button>
            </div>
          </div>
        </section>

        {/* Right Copilot Sidebar */}
        <aside className="takeover-sidebar-right" aria-label="Copilot Panel">
          <div style={{ display: "grid", gap: 16 }}>
            
            {/* Sentiment Analysis Board */}
            <div className="card" style={{ padding: 16 }}>
              <h3 className="card-title" style={{ fontSize: 13, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
                <span className="material-icons" style={{ color: "var(--color-warning)" }}>mood_bad</span>
                Sentiment Context
              </h3>
              
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: "var(--color-danger)" }}>Frustrated</div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>AI Emotion Confidence Score</div>
                </div>
                <div style={{ fontSize: 18, fontWeight: 800, padding: "4px 8px", background: "var(--color-danger-light)", color: "var(--color-danger)", borderRadius: 6 }}>
                  88%
                </div>
              </div>

              {/* Mood spectrum visualization */}
              <div style={{ display: "flex", gap: 4, height: 24, borderRadius: 6, overflow: "hidden", background: "var(--border-color)", fontSize: 9, fontWeight: 700, textAlign: "center", lineHeight: "24px" }}>
                <div style={{ flex: 1, backgroundColor: "var(--color-danger)", color: "white" }}>ANXIOUS</div>
                <div style={{ flex: 1, backgroundColor: "#e2e8f0", color: "#64748b" }}>NEUTRAL</div>
                <div style={{ flex: 1, backgroundColor: "#cbd5e1", color: "#94a3b8" }}>CALM</div>
              </div>
            </div>

            {/* AI Copilot Suggestions Board */}
            <div className="card" style={{ padding: 16 }}>
              <h3 className="card-title" style={{ fontSize: 13, marginBottom: 4, display: "flex", alignItems: "center", gap: 6 }}>
                <span className="material-icons" style={{ color: "var(--color-accent)" }}>psychology</span>
                Copilot Advisor
              </h3>
              <div style={{ fontSize: 11, color: "var(--text-light)", fontWeight: 700, letterSpacing: "0.05em", marginBottom: 12 }}>
                SELECT SUGGESTION TO LOAD REPLY
              </div>

              <div style={{ display: "grid", gap: 10 }}>
                {[
                  {
                    title: "Dispatch Technician",
                    confidence: "94%",
                    desc: "Priority 1 dispatch for Node NW-Grid-882. ETA 35 mins.",
                    msg: "Sarah, I am dispatching a Priority 1 technician to your node NW-Grid-882 immediately. The estimated arrival time is 35 minutes. I will monitor their progress and update you."
                  },
                  {
                    title: "Issue Service Credit",
                    confidence: "82%",
                    desc: "Apply $25 automated credit for 3rd outage in 30 days.",
                    msg: "Sarah, I see this is the third outage this month. As a gesture of goodwill, I have applied an automated $25 service credit to your account."
                  },
                  {
                    title: "Isolate Bypass Valve",
                    confidence: "61%",
                    desc: "Remote toggle for sub-station B-9 to restore partial flow.",
                    msg: "Sarah, I am remotely toggling the bypass valve on sub-station B-9 to isolate the pressure issue and restore partial water flow to your area."
                  }
                ].map((s, idx) => (
                  <div 
                    key={idx}
                    className="copilot-card"
                    onClick={() => handlePrefill(s.msg)}
                  >
                    <div className="copilot-header">
                      <span className="copilot-title">{s.title}</span>
                      <span 
                        className={`badge ${idx === 0 ? "badge-success" : idx === 1 ? "badge-primary" : "badge-warning"}`} 
                        style={{ padding: "1px 6px", fontSize: 9 }}
                      >
                        {s.confidence}
                      </span>
                    </div>
                    <div className="copilot-desc">{s.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Protocol Actions Links */}
            <div className="card" style={{ padding: 16 }}>
              <h3 className="card-title" style={{ fontSize: 13, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
                <span className="material-icons" style={{ color: "var(--text-secondary)" }}>rule_folder</span>
                Utility Protocols
              </h3>
              <div style={{ display: "grid", gap: 8 }}>
                <button 
                  className="btn" 
                  onClick={() => alert("Dispatch protocol standard checklist active.")}
                  style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}
                >
                  <span>Dispatch Technician Protocol</span>
                  <span className="material-icons" style={{ fontSize: 16 }}>arrow_forward</span>
                </button>
                <button 
                  className="btn" 
                  onClick={() => alert("Account credit validation sequence active.")}
                  style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}
                >
                  <span>Credit Outage History</span>
                  <span className="material-icons" style={{ fontSize: 16 }}>arrow_forward</span>
                </button>
                <button 
                  className="btn" 
                  onClick={() => alert("Sub-station camera and pressure feed streaming.")}
                  style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}
                >
                  <span>Sub-station Video Feed</span>
                  <span className="material-icons" style={{ fontSize: 16 }}>arrow_forward</span>
                </button>
              </div>
            </div>

          </div>
        </aside>

      </div>
    </div>
  );
}
