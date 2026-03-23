import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import AdminShell from "./admin/AdminShell";
import AdminDashboard from "./admin/pages/AdminDashboard";
import AdminEscalations from "./admin/pages/AdminEscalations";
import AdminEscalationChat from "./admin/pages/AdminEscalationChat";
import AdminComplaints from "./admin/pages/AdminComplaints";
import AdminComplaintDetail from "./admin/pages/AdminComplaintDetail";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/admin" element={<AdminShell />}>
            <Route index element={<AdminDashboard />} />
            <Route path="escalations" element={<AdminEscalations />} />
            <Route path="escalations/:escalationId" element={<AdminEscalationChat />} />
            <Route path="complaints" element={<AdminComplaints />} />
            <Route path="complaints/:ticketId" element={<AdminComplaintDetail />} />
          </Route>
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
