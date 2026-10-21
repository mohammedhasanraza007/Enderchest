import "@fontsource-variable/dm-sans";
import "@fontsource-variable/jetbrains-mono";
import "@fontsource-variable/newsreader/opsz.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/base.css";
import "./primitives/primitives.css";
import "./patterns/patterns.css";
import "./screens/screens.css";
import { App } from "./App";

const root = document.getElementById("root");
if (root === null) throw new Error("index.html has no #root element");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
