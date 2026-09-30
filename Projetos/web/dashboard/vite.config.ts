import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Base path dinâmico: local dev = /, GitHub Pages = /IA-Lab-Monolito/
const basePath = process.env.VITE_BASE_PATH || "/";

export default defineConfig({
  plugins: [react()],
  base: basePath,
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
