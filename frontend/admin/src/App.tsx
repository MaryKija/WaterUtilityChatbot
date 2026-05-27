import { NavLink, Route, Routes } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "./api";
import Dashboard from "./pages/Dashboard";
import Escalations from "./pages/Escalations";
import EscalationChat from "./pages/EscalationChat";
import Complaints from "./pages/Complaints";
import ComplaintDetail from "./pages/ComplaintDetail";

// -------------------------------------------------------------
// Interactive Mock Subpages for full Navigation Fidelity
// -------------------------------------------------------------

function ModelLab() {
  return (
    <div style={{ display: "grid", gap: 24 }}>
      <div className="system-health-bar">
        <div>
          <h2 style={{ margin: 0, fontFamily: "var(--font-display)" }}>Model Lab</h2>
          <div className="status-sub">AI Hyperparameter Control & Vector Staging</div>
        </div>
        <span className="badge badge-primary">ACTIVE MODEL: DEEPSEEK R1 / GROQ LLAMA 3.3</span>
      </div>

      <div className="grid-main" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Prompt & Agent Staging</h3>
          </div>
          <div style={{ display: "grid", gap: 16 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 6 }}>SYSTEM INSTRUCTIONS PROMPT</label>
              <textarea 
                rows={6} 
                defaultValue="You are a helpful customer support agent for LgWSC (Lukanga Water and Sanitation Company) in Kabwe, Zambia. You assist customers with billing queries, reporting water bursts, pressure outages, and human operator handoffs..."
                style={{ fontSize: 13, fontFamily: "var(--font-sans)" }}
              />
            </div>
            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 6 }}>TEMPERATURE</label>
                <input type="range" min="0" max="1" step="0.05" defaultValue="0.2" />
                <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>0.2 (Focused & Accurate)</span>
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 6 }}>MAX TOKENS</label>
                <input type="number" defaultValue="512" style={{ padding: 6 }} />
              </div>
            </div>
            <button className="btn btn-primary" onClick={() => alert("Model settings staged successfully! Pending deployment review.")}>
              Stage Candidate Changes
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Model Staging & Evaluation</h3>
          </div>
          <div style={{ display: "grid", gap: 14 }}>
            <div style={{ border: "1px solid var(--border-color)", padding: 12, borderRadius: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <strong style={{ fontSize: 14 }}>CAND-9943 (Billing Assistant)</strong>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>F1 Score: 92.4% | Staging Environment</div>
              </div>
              <button className="btn btn-sm btn-primary" onClick={() => alert("Candidate active. Standard 2-human approval required for production release.")}>Test Run</button>
            </div>
            <div style={{ border: "1px solid var(--border-color)", padding: 12, borderRadius: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <strong style={{ fontSize: 14 }}>CAND-8112 (Burst Reporter)</strong>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>F1 Score: 88.7% | Verified Candidate</div>
              </div>
              <span className="badge badge-success">STAGED</span>
            </div>

            <div style={{ marginTop: 12 }}>
              <h4 style={{ fontSize: 13, marginBottom: 8 }}>Model Evaluation Metrics (Autonomy Rate)</h4>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--text-secondary)" }}>
                <span>Target Accuracy</span>
                <span>85.0%</span>
              </div>
              <div className="progress-container">
                <div className="progress-bar success" style={{ width: "85%" }}></div>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--text-secondary)", marginTop: 12 }}>
                <span>Actual Autonomy Rate</span>
                <span>84.2%</span>
              </div>
              <div className="progress-container">
                <div className="progress-bar" style={{ width: "84.2%", backgroundColor: "var(--color-accent)" }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Diagnostics() {
  return (
    <div style={{ display: "grid", gap: 24 }}>
      <div className="system-health-bar">
        <div>
          <h2 style={{ margin: 0, fontFamily: "var(--font-display)" }}>Diagnostics Suite</h2>
          <div className="status-sub">Live Microservice Status & Latency Monitors</div>
        </div>
        <button className="btn" onClick={() => window.location.reload()}>Run Full Diagnosis</button>
      </div>

      <div className="grid-cols-4">
        <div className="card metric-card success">
          <div className="metric-label">FastAPI Gatekeeper</div>
          <div className="metric-value" style={{ fontSize: 24 }}>ONLINE</div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 6 }}>Latency: 12ms | Port 8000</div>
        </div>
        <div className="card metric-card success">
          <div className="metric-label">Groq LLM Provider</div>
          <div className="metric-value" style={{ fontSize: 24 }}>STABLE</div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 6 }}>Token Latency: 240ms | API Ready</div>
        </div>
        <div className="card metric-card success">
          <div className="metric-label">Twilio Sandbox</div>
          <div className="metric-value" style={{ fontSize: 24 }}>SYNCED</div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 6 }}>Webhooks: Activated</div>
        </div>
        <div className="card metric-card accent">
          <div className="metric-label">SQLite Local Storage</div>
          <div className="metric-value" style={{ fontSize: 24 }}>HEALTHY</div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 6 }}>Size: 712KB | 0 Connections Stalled</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Live System Diagnostic Logs</h3>
        </div>
        <div className="mono" style={{ backgroundColor: "#0f172a", color: "#38bdf8", padding: 20, borderRadius: 8, fontSize: 12, overflowX: "auto", maxHeight: 300, lineHeight: 1.6 }}>
          <div>[2026-05-26 12:44:11] INFO - Starting Lukanga Water Utility Chatbot Core Orchestrator...</div>
          <div>[2026-05-26 12:44:12] INFO - Groq LLM configured and validated with model: Llama3-8b-8192</div>
          <div>[2026-05-26 12:44:12] INFO - Mounted Vite assets index.html matching MIME rules.</div>
          <div>[2026-05-26 12:44:13] INFO - SQLite DB connection pool established. water_utility.db active.</div>
          <div>[2026-05-26 12:44:15] DEBUG - Intent classifier result: BurstReport confidence: 0.98</div>
          <div>[2026-05-26 12:44:15] DEBUG - Dispatching context updates to Kabwe Central reservoir flow-meters.</div>
          <div style={{ color: "#10b981" }}>[2026-05-26 12:45:01] SUCCESS - System health probe returned STATUS:200 OK.</div>
        </div>
      </div>
    </div>
  );
}

function Settings() {
  return (
    <div style={{ display: "grid", gap: 24 }}>
      <div className="system-health-bar">
        <div>
          <h2 style={{ margin: 0, fontFamily: "var(--font-display)" }}>Settings</h2>
          <div className="status-sub">Global Escalation Safeguards & Threshold Boundaries</div>
        </div>
        <button className="btn btn-primary" onClick={() => alert("Settings saved.")}>Save Settings</button>
      </div>

      <div className="card" style={{ maxWidth: 800 }}>
        <div className="card-header">
          <h3 className="card-title">Escalation Safeguard Metrics</h3>
        </div>
        <div style={{ display: "grid", gap: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <strong>Confidence Threshold</strong>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Auto-escalates to human agent if AI intent classification is below this score.</div>
            </div>
            <input type="number" defaultValue="0.75" step="0.05" style={{ width: 100 }} />
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <strong>Max Loops Allowed</strong>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Flags escalations if a customer repeats queries within a 2-minute slot.</div>
            </div>
            <input type="number" defaultValue="3" style={{ width: 100 }} />
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <strong>Emergency Override Mode</strong>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>When enabled, bypasses validation approvals for rapid prompt hotfixes.</div>
            </div>
            <input type="checkbox" defaultChecked={false} style={{ width: 24, height: 24 }} />
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <strong>Audit Log Level</strong>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Detail level logged to water_utility.db during conversation runs.</div>
            </div>
            <select style={{ width: 150 }}>
              <option>VERBOSE</option>
              <option selected>INFO</option>
              <option>WARNING ONLY</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}

// -------------------------------------------------------------
// App Component
// -------------------------------------------------------------

export default function App() {
  const [authenticated, setAuthenticated] = useState<boolean>(!!localStorage.getItem("admin_user"));
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.login(username, password);
      if (res.success) {
        // Clear plain text token from localStorage for XSS protection
        localStorage.removeItem("admin_token");
        localStorage.setItem("admin_user", JSON.stringify({ user_id: res.user_id, role: res.role }));
        setAuthenticated(true);
      } else {
        setError(res.message || "Invalid credentials");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch (err) {
      // Ignore API logout failures (e.g. if already expired or unreachable)
    }
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_user");
    setAuthenticated(false);
  };

  if (!authenticated) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        fontFamily: "var(--font-sans)",
        padding: 20
      }}>
        <div style={{
          background: "rgba(30, 41, 59, 0.7)",
          backdropFilter: "blur(16px)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          borderRadius: 24,
          padding: "40px 32px",
          width: "100%",
          maxWidth: 440,
          boxShadow: "0 20px 40px rgba(0, 0, 0, 0.3), 0 0 50px rgba(14, 165, 233, 0.15)",
          textAlign: "center",
          animation: "slide-up 0.4s cubic-bezier(0.16, 1, 0.3, 1)"
        }}>
          {/* Brand Icon */}
          <div style={{
            background: "linear-gradient(135deg, #38bdf8, #0ea5e9)",
            width: 60,
            height: 60,
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 28,
            fontWeight: 800,
            color: "white",
            margin: "0 auto 20px",
            boxShadow: "0 0 20px rgba(56, 189, 248, 0.6)",
            fontFamily: "var(--font-display)"
          }}>
            W
          </div>
          
          <h2 style={{
            fontFamily: "var(--font-display)",
            fontSize: 26,
            fontWeight: 800,
            color: "#ffffff",
            marginBottom: 8,
            letterSpacing: "-0.02em"
          }}>
            LgWSC Console
          </h2>
          <p style={{
            color: "var(--text-light)",
            fontSize: 14,
            marginBottom: 32
          }}>
            Operator Terminal & Safety Override Hub
          </p>

          <form onSubmit={handleLogin} style={{ display: "grid", gap: 20, textAlign: "left" }}>
            <div>
              <label style={{
                fontSize: 11,
                fontWeight: 700,
                color: "rgba(255, 255, 255, 0.6)",
                display: "block",
                marginBottom: 6,
                textTransform: "uppercase",
                letterSpacing: "0.05em"
              }}>
                Username
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{
                  width: "100%",
                  padding: "12px 16px",
                  borderRadius: 10,
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  background: "rgba(15, 23, 42, 0.6)",
                  color: "#ffffff",
                  fontSize: 14,
                  outline: "none",
                  transition: "var(--transition-fast)"
                }}
                placeholder="admin"
              />
            </div>

            <div>
              <label style={{
                fontSize: 11,
                fontWeight: 700,
                color: "rgba(255, 255, 255, 0.6)",
                display: "block",
                marginBottom: 6,
                textTransform: "uppercase",
                letterSpacing: "0.05em"
              }}>
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  width: "100%",
                  padding: "12px 16px",
                  borderRadius: 10,
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  background: "rgba(15, 23, 42, 0.6)",
                  color: "#ffffff",
                  fontSize: 14,
                  outline: "none",
                  transition: "var(--transition-fast)"
                }}
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div style={{
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid var(--color-danger)",
                color: "#fca5a5",
                padding: "10px 14px",
                borderRadius: 8,
                fontSize: 13,
                textAlign: "center"
              }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
              style={{
                width: "100%",
                padding: "12px",
                borderRadius: 10,
                fontSize: 14,
                fontWeight: 700,
                marginTop: 8,
                border: "none",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                gap: 8,
                boxShadow: "0 4px 12px rgba(14, 165, 233, 0.3)"
              }}
            >
              {loading ? (
                <span>Signing in...</span>
              ) : (
                <>
                  <span>Sign In</span>
                  <svg style={{ width: 16, height: 16 }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div>
      <a href="#main-content" className="sr-only focus:not-sr-only btn-skip">Skip to main content</a>
      <div className="navbar" role="banner">
        <div className="navbar-content">
          <div className="navbar-branding">
            <div className="navbar-logo-icon">W</div>
            <div className="navbar-title">LGWSC CHATBOT</div>
          </div>
          
          <nav className="navbar-nav" aria-label="Admin Navigation">
            <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`} end>
              Dashboard
            </NavLink>
            <NavLink to="/complaints" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
              Tickets
            </NavLink>
            <NavLink to="/escalations" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
              Takeover
            </NavLink>
            <NavLink to="/model-lab" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
              Model Lab
            </NavLink>
            <span style={{ width: 1, height: 20, backgroundColor: "#334155", margin: "0 8px" }} />
            <NavLink to="/diagnostics" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
              Diagnostics
            </NavLink>
            <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
              Settings
            </NavLink>
            <span style={{ width: 1, height: 20, backgroundColor: "#334155", margin: "0 8px" }} />
            <button
              onClick={handleLogout}
              className="nav-item"
              style={{
                background: "rgba(239, 68, 68, 0.1)",
                border: "none",
                cursor: "pointer",
                color: "#f87171",
                fontWeight: 600,
                fontSize: 13,
                padding: "8px 14px",
                borderRadius: "var(--radius-sm)",
                transition: "var(--transition-fast)"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "rgba(239, 68, 68, 0.25)";
                e.currentTarget.style.color = "#ffffff";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "rgba(239, 68, 68, 0.1)";
                e.currentTarget.style.color = "#f87171";
              }}
            >
              Logout
            </button>
          </nav>
        </div>
      </div>

      <main id="main-content" className="container" role="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/complaints" element={<Complaints />} />
          <Route path="/complaints/:ticketId" element={<ComplaintDetail />} />
          <Route path="/escalations" element={<Escalations />} />
          <Route path="/escalations/:escalationId" element={<EscalationChat />} />
          <Route path="/model-lab" element={<ModelLab />} />
          <Route path="/diagnostics" element={<Diagnostics />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
