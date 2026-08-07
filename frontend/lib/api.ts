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

/** Bỏ cuộc sau ngần này ms — static export retry 3×60s nếu fetch treo. */
const FETCH_TIMEOUT_MS = 15_000;

function isPagesBuild(): boolean {
  return process.env.GITHUB_PAGES === "true";
}

/**
 * Chuỗi rỗng (secret CI chưa set) phải coi như chưa cấu hình — `??` không bắt được ""
 * nên `fetch("/console/overview")` thành URL tương đối và treo cả build.
 */
export function apiBase(): string {
  const configured = process.env.QSHIELD_API_URL?.trim();
  if (configured) return configured.replace(/\/+$/, "");
  // Static export không có API thật: đừng đoán localhost của runner.
  return isPagesBuild() ? "" : DEFAULT_API;
}

/**
 * Static export không cho route dynamic: `cache: "no-store"` khiến Next đánh dấu
 * page là dynamic và `output: "export"` fail. Lúc build Pages thì fetch một lần
 * rồi bake kết quả vào HTML.
 */
async function getJson<T>(path: string): Promise<T | null> {
  const base = apiBase();
  // Không có API → trả null, UI hiện banner "Backend chưa sẵn sàng" thay vì treo build.
  if (!base) return null;

  try {
    const response = await fetch(`${base}${path}`, {
      cache: isPagesBuild() ? "force-cache" : "no-store",
      signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
    });
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
