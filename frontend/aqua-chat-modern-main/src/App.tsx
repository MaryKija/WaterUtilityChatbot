import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
<<<<<<< HEAD
import { BrowserRouter, Routes, Route } from "react-router-dom";
=======
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation } from "react-router-dom";
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import AdminShell from "./admin/AdminShell";
import AdminDashboard from "./admin/pages/AdminDashboard";
import AdminEscalations from "./admin/pages/AdminEscalations";
import AdminEscalationChat from "./admin/pages/AdminEscalationChat";
import AdminComplaints from "./admin/pages/AdminComplaints";
import AdminComplaintDetail from "./admin/pages/AdminComplaintDetail";
<<<<<<< HEAD
=======
import AdminLogin from "./admin/pages/AdminLogin";

function AdminAuthGuard() {
  const token = typeof window !== "undefined" ? window.localStorage.getItem("admin_token") : null;
  const location = useLocation();

  if (!token) {
    // Always redirect to the React login page, never to the static admin.html
    return <Navigate to="/admin/login" state={{ from: location.pathname }} replace />;
  }

  return <Outlet />;
}
>>>>>>> 9a7f394 (Initial clean commit for capstone project)

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
<<<<<<< HEAD
          <Route path="/admin" element={<AdminShell />}>
            <Route index element={<AdminDashboard />} />
            <Route path="escalations" element={<AdminEscalations />} />
            <Route path="escalations/:escalationId" element={<AdminEscalationChat />} />
            <Route path="complaints" element={<AdminComplaints />} />
            <Route path="complaints/:ticketId" element={<AdminComplaintDetail />} />
=======
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/admin" element={<AdminAuthGuard />}>
            <Route element={<AdminShell />}>
              <Route index element={<AdminDashboard />} />
              <Route path="escalations" element={<AdminEscalations />} />
              <Route path="escalations/:escalationId" element={<AdminEscalationChat />} />
              <Route path="complaints" element={<AdminComplaints />} />
              <Route path="complaints/:ticketId" element={<AdminComplaintDetail />} />
            </Route>
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
          </Route>
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
