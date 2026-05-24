import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, UsersRound, FileText, ArrowLeft, LogOut, Droplets } from "lucide-react";
import { adminLogout } from "./api";

function NavItem({ to, label, icon }: { to: string; label: string; icon: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        [
          "inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition",
          isActive
            ? "border-primary/25 bg-primary/10 text-primary"
            : "border-slate-200 bg-white text-slate-700 hover:border-primary/20 hover:bg-primary/5 hover:text-slate-900",
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
    <div className="min-h-screen bg-background">
      <div className="border-b border-border bg-white/95 shadow-sm">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3">
          <NavLink
            to="/"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-primary/20 hover:bg-primary/5 hover:text-slate-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Customer portal
          </NavLink>

          <div className="flex min-w-0 items-center gap-2">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <Droplets className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <div className="truncate text-sm font-extrabold text-slate-900 sm:text-base">LgWSC Admin</div>
              <div className="hidden text-xs font-medium text-slate-500 sm:block">Lukanga Water operations</div>
            </div>
          </div>

          <div className="ml-auto flex flex-wrap items-center gap-2">
            <NavItem to="/admin" label="Dashboard" icon={<LayoutDashboard className="h-4 w-4" />} />
            <NavItem to="/admin/escalations" label="Escalations" icon={<UsersRound className="h-4 w-4" />} />
            <NavItem to="/admin/complaints" label="Complaints" icon={<FileText className="h-4 w-4" />} />
            <button
              type="button"
              onClick={adminLogout}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-primary/20 hover:bg-primary/5 hover:text-slate-900"
            >
              <LogOut className="h-4 w-4" />
              Log out
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-4 py-5">
        <Outlet />
      </div>
    </div>
  );
}

