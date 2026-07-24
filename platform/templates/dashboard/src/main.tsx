import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ThemeProvider } from "@quant-research/ui";
import "@quant-research/ui/styles.css";
import "@quant-research/shell/styles.css";
import "@quant-research/charts/styles.css";
import "./styles.css";
import { App } from "./app";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Missing #root element.");
}

createRoot(root).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>,
);
