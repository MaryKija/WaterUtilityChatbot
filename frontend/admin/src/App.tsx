import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Escalations from "./pages/Escalations";
import EscalationChat from "./pages/EscalationChat";
import Complaints from "./pages/Complaints";
import ComplaintDetail from "./pages/ComplaintDetail";
import "./App.css";

const linkStyle = {
  color: "inherit",
  textDecoration: "none",
};

export default function App() {
  return (
    <div>
      <div className="navbar">
        <div className="container navbar-content">
          <div className="navbar-title">Water Utility Admin</div>
          <div className="navbar-spacer" />
          <nav className="navbar-nav">
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

