import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Escalations from "./pages/Escalations";
import EscalationChat from "./pages/EscalationChat";
import Complaints from "./pages/Complaints";
import ComplaintDetail from "./pages/ComplaintDetail";

const linkStyle = ({ isActive }: { isActive: boolean }) => ({
  padding: "8px 10px",
  borderRadius: 10,
  textDecoration: "none",
  border: "1px solid #e2e8f0",
  background: isActive ? "#e0f2fe" : "#fff",
});

export default function App() {
  return (
    <div>
      <div style={{ borderBottom: "1px solid #e2e8f0", background: "white" }}>
        <div className="container" style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontWeight: 800 }}>Water Utility Admin</div>
          <div style={{ flex: 1 }} />
          <nav style={{ display: "flex", gap: 10 }}>
            <NavLink to="/" style={linkStyle} end>
              Dashboard
            </NavLink>
            <NavLink to="/escalations" style={linkStyle}>
              Escalations
            </NavLink>
            <NavLink to="/complaints" style={linkStyle}>
              Complaints
            </NavLink>
          </nav>
        </div>
      </div>

      <div className="container">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/escalations" element={<Escalations />} />
          <Route path="/escalations/:escalationId" element={<EscalationChat />} />
          <Route path="/complaints" element={<Complaints />} />
          <Route path="/complaints/:ticketId" element={<ComplaintDetail />} />
        </Routes>
      </div>
    </div>
  );
}

