import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, UsersRound, FileText, ArrowLeft } from "lucide-react";

function NavItem({ to, label, icon }: { to: string; label: string; icon: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        [
          "inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition",
          isActive
            ? "border-sky-200 bg-sky-50 text-sky-900"
            : "border-slate-200 bg-white text-slate-800 hover:bg-slate-50",
        ].join(" ")
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}

export default function AdminShell() {
  return (
    <div className="min-h-screen bg-slate-50">
      <div className="border-b bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
          <NavLink
            to="/"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
          >
            <ArrowLeft className="h-4 w-4" />
            Customer
          </NavLink>

          <div className="font-extrabold text-slate-900">Admin Panel</div>

          <div className="ml-auto flex items-center gap-2">
            <NavItem to="/admin" label="Dashboard" icon={<LayoutDashboard className="h-4 w-4" />} />
            <NavItem to="/admin/escalations" label="Escalations" icon={<UsersRound className="h-4 w-4" />} />
            <NavItem to="/admin/complaints" label="Complaints" icon={<FileText className="h-4 w-4" />} />
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-5xl px-4 py-4">
        <Outlet />
      </div>
    </div>
  );
}

