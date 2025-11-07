import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Align with frontend src/api.ts which reads VITE_API_BASE
const apiTarget = process.env.VITE_API_BASE || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/auth": {
        target: apiTarget,
        changeOrigin: true
      },
      "/labs": {
        target: apiTarget,
        changeOrigin: true
      },
      "/quizzes": {
        target: apiTarget,
        changeOrigin: true
      },
      "/exams": {
        target: apiTarget,
        changeOrigin: true
      },
      "/dashboard": {
        target: apiTarget,
        changeOrigin: true
      },
      "/notes": {
        target: apiTarget,
        changeOrigin: true
      },
      "/admin": {
        target: apiTarget,
        changeOrigin: true
      },
      "/health": {
        target: apiTarget,
        changeOrigin: true
      }
    }
  }
});
