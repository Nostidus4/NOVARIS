import type {
  ConsoleData,
  ConsoleOverview,
  ConsoleQuantum,
  ConsoleRegime,
  ConsoleReport,
  ConsoleRisk,
  ConsoleScenarios,
  ConsoleShell,
} from "./types";

const DEFAULT_API = "http://127.0.0.1:8000";

export function apiBase(): string {
  return process.env.QSHIELD_API_URL ?? DEFAULT_API;
}

/**
 * Static export (GitHub Pages) không cho route dynamic.
 * `cache: "no-store"` → Next đánh dấu dynamic → `next build` với `output: "export"` fail.
 * Khi GITHUB_PAGES=true, fetch một lần lúc build rồi bake vào HTML.
 */
function fetchInit(): RequestInit {
  if (process.env.GITHUB_PAGES === "true") {
    return { cache: "force-cache" };
  }
  return { cache: "no-store" };
}

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${apiBase()}${path}`, fetchInit());
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export const loadConsoleShell = () => getJson<ConsoleShell>("/console/shell");
export const loadConsoleOverview = () => getJson<ConsoleOverview>("/console/overview");
export const loadConsoleData = () => getJson<ConsoleData>("/console/data");
export const loadConsoleRegime = () => getJson<ConsoleRegime>("/console/regime");
export const loadConsoleScenarios = () => getJson<ConsoleScenarios>("/console/scenarios");
export const loadConsoleRisk = () => getJson<ConsoleRisk>("/console/risk");
export const loadConsoleQuantum = () => getJson<ConsoleQuantum>("/console/quantum");
export const loadConsoleReport = () => getJson<ConsoleReport>("/console/report");
