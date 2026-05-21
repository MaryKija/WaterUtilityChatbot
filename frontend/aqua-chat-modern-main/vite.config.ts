import { defineConfig, UserConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

<<<<<<< HEAD
=======
// Backend URL for the dev proxy — override with VITE_BACKEND_URL if needed
const BACKEND = process.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

>>>>>>> 9a7f394 (Initial clean commit for capstone project)
// https://vitejs.dev/config/
export default defineConfig(({ mode }): UserConfig => ({
  server: {
    host: "0.0.0.0",
    port: 5173,
    hmr: {
      overlay: false,
    },
<<<<<<< HEAD
    proxy: {
      // Proxy API requests to the FastAPI backend so the browser never hits CORS.
      // Frontend calls /api/* and Vite rewrites to backend /*.
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
=======
    // Proxy all API calls to the FastAPI backend in dev mode.
    // This eliminates CORS issues during development and makes it trivial
    // to embed the widget on any company website later.
    proxy: {
      "/chat": { target: BACKEND, changeOrigin: true },
      "/auth": { target: BACKEND, changeOrigin: true },
      "/admin": { target: BACKEND, changeOrigin: true },
      "/feedback": { target: BACKEND, changeOrigin: true },
      "/health": { target: BACKEND, changeOrigin: true },
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
