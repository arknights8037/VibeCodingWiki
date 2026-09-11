import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/skills": "http://localhost:8000",
      "/healthz": "http://localhost:8000",
      "/mcp": "http://localhost:8000",
    },
  },
});
