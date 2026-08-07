"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Play, Square } from "lucide-react";
import { pct } from "@/lib/format";
import { fetchOptimizeJob, submitOptimizeJob, type OptimizeJob } from "@/lib/client-api";

type Props = {
  tickers: string[];
};

export function RunOptimizePanel({ tickers }: Props) {
  const router = useRouter();
  const [job, setJob] = useState<OptimizeJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [, startTransition] = useTransition();

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  function stopPolling() {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    setBusy(false);
  }

  async function poll(jobId: string) {
    try {
      const next = await fetchOptimizeJob(jobId);
      setJob(next);
      if (next.status === "done" || next.status === "failed") {
        stopPolling();
        startTransition(() => router.refresh());
        return;
      }
      timer.current = setTimeout(() => poll(jobId), 2000);
    } catch (e) {
      setError((e as Error).message);
      stopPolling();
    }
  }

  async function run() {
    setError(null);
    setJob(null);
    setBusy(true);
    try {
      const equal = tickers.length ? 1 / tickers.length : 0;
      const weights = Object.fromEntries(tickers.map((t) => [t, equal]));
      const jobId = await submitOptimizeJob(weights, 0);
      setJob({
        job_id: jobId,
        status: "queued",
        created_at: new Date().toISOString(),
        finished_at: null,
        error: null,
        result: null,
      });
      timer.current = setTimeout(() => poll(jobId), 1200);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  const status = job?.status ?? "idle";

  return (
    <article className="card card-pad">
      <div className="card-head">
        <div>
          <div className="card-label">Run optimization</div>
          <div className="card-title">Submit a solver job</div>
          <div className="card-sub">
            Gọi `POST /optimize/jobs` chạy nền, dùng handoff hiện có trên đĩa. Exact 20-bit mất
            khoảng 40 giây.
          </div>
        </div>
        <span className={`tag ${statusTone(status)}`}>{status}</span>
      </div>

      <div className="run-actions">
        <button type="button" className="btn primary" onClick={run} disabled={busy}>
          <Play size={14} />
          {busy ? "Running…" : "Run optimization"}
        </button>
        {busy ? (
          <button type="button" className="btn" onClick={stopPolling}>
            <Square size={13} />
            Stop watching
          </button>
        ) : null}
      </div>

      {error ? <div className="callout warning run-out">{error}</div> : null}

      {job?.result ? (
        <>
          <div className="grid grid-4 run-out">
            <div className="callout primary">
              <div className="card-label">Solver used</div>
              <div className="metric-value" style={{ fontSize: 21 }}>
                {job.result.actual_solver}
              </div>
            </div>
            <div className="callout">
              <div className="card-label">Runtime</div>
              <div className="metric-value" style={{ fontSize: 21 }}>
                {job.result.runtime_seconds.toFixed(1)}s
              </div>
            </div>
            <div className="callout">
              <div className="card-label">Exact energy</div>
              <div className="metric-value" style={{ fontSize: 21 }}>
                {job.result.exact_energy.toFixed(4)}
              </div>
            </div>
            <div className="callout">
              <div className="card-label">True CVaR (loss)</div>
              <div className="metric-value" style={{ fontSize: 21 }}>
                {pct(job.result.true_cvar_before)} → {pct(job.result.true_cvar_after)}
              </div>
            </div>
          </div>
          <div className="callout run-out">
            <div className="callout-title">
              Bitstring <code>{job.result.bitstring}</code>
            </div>
            <div className="callout-copy">
              Requested <strong>{job.result.requested_solver}</strong>, chạy bằng{" "}
              <strong>{job.result.actual_solver}</strong> trên {job.result.backend}. QAOA thắng
              classical: <strong>{String(job.result.qaoa_beats_classical)}</strong>.
              {job.result.fallback_reason ? ` ${job.result.fallback_reason}.` : ""}
            </div>
          </div>
        </>
      ) : null}

      {job && !job.result && !job.error ? (
        <div className="callout run-out">
          <div className="callout-title">Job {job.job_id.slice(0, 8)}</div>
          <div className="callout-copy">
            Đang chạy nền — bảng bên dưới sẽ tự cập nhật khi xong.
          </div>
        </div>
      ) : null}

      {job?.error ? <div className="callout warning run-out">{job.error}</div> : null}
    </article>
  );
}

function statusTone(status: string): string {
  if (status === "done") return "good";
  if (status === "failed") return "warn";
  return "info";
}
