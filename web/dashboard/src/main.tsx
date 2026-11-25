import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { FingerprintRoot } from "./fingerprint";
import "./styles/index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <FingerprintRoot>
      <App />
    </FingerprintRoot>
  </StrictMode>,
);
