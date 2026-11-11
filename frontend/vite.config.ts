import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // so the frontend can call /api/... without CORS issues in dev
      "/api": "http://localhost:8000",
    },
  },
});
