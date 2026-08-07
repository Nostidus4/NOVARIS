"use client";

const DEFAULT_API = "http://127.0.0.1:8000";

export function clientApiBase(): string {
  // Chuỗi rỗng (secret CI chưa set) không phải URL hợp lệ — fallback về default.
  const configured = process.env.NEXT_PUBLIC_QSHIELD_API_URL?.trim();
  return configured ? configured.replace(/\/+$/, "") : DEFAULT_API;
}

export type SyncResponse = {
  run_key: string;
  profile_id: string;
  profile_status: string;
  synced_at: string;
  candidate_count: number;
  message: string;
};

export async function syncWorkflow(): Promise<SyncResponse> {
  const res = await fetch(`${clientApiBase()}/workflow/sync`, { method: "POST" });
  const body = await res.json();
  if (!res.ok) throw new Error(body?.detail ?? `Sync failed (${res.status})`);
  return body as SyncResponse;
}

export type OptimizeJob = {
  job_id: string;
  status: string;
  created_at: string;
  finished_at: string | null;
  error: string | null;
  result: {
    bitstring: string;
    requested_solver: string;
    actual_solver: string;
    exact_energy: number;
    optimality_gap: number | null;
    qaoa_beats_classical: boolean;
    runtime_seconds: number;
    backend: string;
    true_cvar_before: number | null;
    true_cvar_after: number | null;
    fallback_reason: string | null;
    source_artifact: string;
  } | null;
};

export async function submitOptimizeJob(
  weights: Record<string, number>,
  cashWeight: number,
): Promise<string> {
  const res = await fetch(`${clientApiBase()}/optimize/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ weights, cash_weight: cashWeight }),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body?.detail ?? `Submit failed (${res.status})`);
  return body.job_id as string;
}

export async function fetchOptimizeJob(jobId: string): Promise<OptimizeJob> {
  const res = await fetch(`${clientApiBase()}/optimize/jobs/${jobId}`, {
    cache: "no-store",
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body?.detail ?? `Poll failed (${res.status})`);
  return body as OptimizeJob;
}
