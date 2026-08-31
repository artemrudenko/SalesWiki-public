import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export function workbenchProxyTarget(value = "http://127.0.0.1:8787") {
  const parsed = new URL(value);
  if (
    !["http:", "https:"].includes(parsed.protocol)
    || parsed.username
    || parsed.password
    || parsed.pathname !== "/"
    || parsed.search
    || parsed.hash
  ) {
    throw new Error("SALESWIKI_WORKBENCH_BFF_TARGET must be an HTTP(S) origin without credentials or a path");
  }
  return parsed.origin;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget = workbenchProxyTarget(env.SALESWIKI_WORKBENCH_BFF_TARGET);
  return {
    build: {
      outDir: "dist/client",
      rollupOptions: {
        output: {
          manualChunks: {
            "graph-vendor": ["@xyflow/react"],
          },
        },
      },
    },
    optimizeDeps: {
      include: ["react", "react-dom/client"],
    },
    server: {
      host: "0.0.0.0",
      allowedHosts: ["terminal.local"],
      proxy: {
        "/api": {
          target: proxyTarget,
          changeOrigin: false,
        },
      },
      warmup: {
        clientFiles: ["./src/main.jsx"],
      },
    },
    plugins: [react()],
  };
});
