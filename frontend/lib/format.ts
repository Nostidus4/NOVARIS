export function pct(value: number | undefined | null, digits = 2): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function num(value: number | undefined | null, digits = 4): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

export function ppDelta(before: number | undefined | null, after: number | undefined | null): string {
  if (before === undefined || before === null || after === undefined || after === null) {
    return "—";
  }
  const delta = (before - after) * 100;
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(2)}pp`;
}

export function stageTone(status: string | undefined): "pass" | "warn" | "ready" {
  const s = (status ?? "").toUpperCase();
  if (["PASS", "READY", "OK"].includes(s)) return "pass";
  if (["WARN", "WARNING", "PENDING", "MISSING", "FAIL"].includes(s)) return "warn";
  return "ready";
}
