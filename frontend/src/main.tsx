import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { setNonce } from "get-nonce";
import { App } from "./app/App";
import "./styles/globals.css";

const root = document.getElementById("root");
const styleNonce = document.querySelector<HTMLMetaElement>(
  'meta[name="tripse-style-nonce"]',
)?.content;
if (styleNonce && styleNonce !== "__TRIPSE_STYLE_NONCE__") setNonce(styleNonce);
if (!root) throw new Error("Brak elementu głównego aplikacji");
createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
