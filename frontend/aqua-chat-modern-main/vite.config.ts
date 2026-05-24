import { defineConfig, UserConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// Backend URL for the dev proxy; override with VITE_BACKEND_URL if needed.
const BACKEND = process.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

// https://vitejs.dev/config/
export default defineConfig(({ mode }): UserConfig => ({
  server: {
    host: "0.0.0.0",
    port: 5173,
    hmr: {
      overlay: false,
    },
    // Proxy API calls to the FastAPI backend in dev mode.
    proxy: {
      "/chat": { target: BACKEND, changeOrigin: true },
      "/auth": { target: BACKEND, changeOrigin: true },
      "/admin": { target: BACKEND, changeOrigin: true },
      "/feedback": { target: BACKEND, changeOrigin: true },
      "/health": { target: BACKEND, changeOrigin: true },
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
