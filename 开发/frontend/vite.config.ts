import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";

const apiTarget = process.env.VCW_API_TARGET || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  // The editor is a local tarball whose contents can change without a
  // package-version change. Always rebuild its dependency prebundle on a
  // fresh dev-server start so stale named exports cannot be served.
  optimizeDeps: { force: true },
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    proxy: {
      "/api": apiTarget,
      "^/skills/[^/]+/[^/]+/": apiTarget,
      "/healthz": apiTarget,
      "/mcp": apiTarget,
      "/media": apiTarget,
    },
  },
});
