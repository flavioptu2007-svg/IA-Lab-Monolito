import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { iniciarFingerprint } from "./fingerprint";
import "./styles/index.css";

void iniciarFingerprint();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
