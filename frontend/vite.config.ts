import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import type { IncomingMessage, ServerResponse } from "node:http";

// Vite requires the trailing slash at its base. Normalize only the app entry in
// local dev/preview; production FastAPI routing is deliberately FRONT-001B.
function redirectAppEntry(
  request: IncomingMessage,
  response: ServerResponse,
  next: () => void,
) {
  if (request.url && /^\/app(?:\?|$)/.test(request.url)) {
    response.writeHead(307, { Location: `/app/${request.url.slice(4)}` });
    response.end();
    return;
  }
  next();
}

export default defineConfig({
  base: "/app/",
  plugins: [
    react(),
    tailwindcss(),
    {
      name: "tripse-local-app-entry",
      configureServer(server) {
        server.middlewares.use(redirectAppEntry);
      },
      configurePreviewServer(server) {
        server.middlewares.use(redirectAppEntry);
      },
    },
  ],
  server: { host: "127.0.0.1", port: 5173, strictPort: true },
  preview: { host: "127.0.0.1", port: 4173, strictPort: true },
  test: {
    env: { BASE_URL: "/app/" },
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
    restoreMocks: true,
  },
});
