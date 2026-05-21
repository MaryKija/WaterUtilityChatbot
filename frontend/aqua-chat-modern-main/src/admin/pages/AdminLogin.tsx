import { useState, type FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Droplets, ShieldCheck } from "lucide-react";

const API_URL = import.meta.env.PROD
  ? (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "")
  : "";

export default function AdminLogin() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as { from?: string } | null)?.from || "/admin";

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    const u = username.trim();
    const p = password.trim();
    if (!u || !p) {
      setError("Please enter both username and password.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: u, password: p }),
      });

      const data = await res.json() as {
        success: boolean;
        token?: string;
        role?: string;
        message?: string;
      };

      if (!data.success || !data.token) {
        setError(data.message || "Invalid username or password.");
        return;
      }

      // Store the session token - admin/api.ts reads this as the Bearer token.
      window.localStorage.setItem("admin_token", data.token);
      window.localStorage.setItem("admin_role", data.role ?? "admin");
      navigate(from, { replace: true });
    } catch {
      setError("Could not reach the server. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-8">
      <div className="w-full max-w-md rounded-2xl border border-border bg-white p-8 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <Droplets className="h-6 w-6" />
          </span>
          <div>
            <p className="m-0 text-xs font-semibold uppercase tracking-normal text-primary">LgWSC operations</p>
            <h1 className="m-0 text-2xl font-bold text-slate-900">Admin sign in</h1>
          </div>
        </div>
        <p className="mt-4 text-sm leading-6 text-slate-600">
          Access Lukanga Water case handling, escalations, and service feedback.
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="admin-username">
              Username
            </label>
            <input
              id="admin-username"
              type="text"
              value={username}
              onChange={(e) => { setUsername(e.target.value); setError(null); }}
              className="w-full rounded-xl border border-input bg-chat-input-bg px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
              placeholder="admin"
              autoComplete="username"
              autoFocus
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="admin-password">
              Password
            </label>
            <input
              id="admin-password"
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError(null); }}
              className="w-full rounded-xl border border-input bg-chat-input-bg px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
              placeholder="password"
              autoComplete="current-password"
            />
          </div>

          {error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground transition hover:brightness-95 disabled:opacity-60"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="mt-6 flex gap-3 rounded-xl border border-primary/10 bg-primary/5 px-4 py-4 text-sm text-slate-600">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <span>Your session token is stored locally and cleared on logout.</span>
        </div>
      </div>
    </div>
  );
}
