import "./shared/api/client/validation-runtime";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { setNonce } from "get-nonce";
import { QueryClientProvider } from "@tanstack/react-query";
import { createApiQueryClient } from "./shared/api/query/client";
import { App } from "./app/App";
import "./styles/globals.css";

const root = document.getElementById("root");
const queryClient = createApiQueryClient();
const styleNonce = document.querySelector<HTMLMetaElement>(
  'meta[name="tripse-style-nonce"]',
)?.content;
if (styleNonce && styleNonce !== "__TRIPSE_STYLE_NONCE__") setNonce(styleNonce);
if (!root) throw new Error("Brak elementu głównego aplikacji");
createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
