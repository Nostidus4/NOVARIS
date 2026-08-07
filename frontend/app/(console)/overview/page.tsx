import Link from "next/link";
import { ArrowRight, ChevronRight, FileDown, TrendingDown } from "lucide-react";
import { loadConsoleOverview } from "@/lib/api";
import { pct, ppDelta, stageTone } from "@/lib/format";
import { Btn, PageHead } from "@/components/ui/PageHead";
import { ReadOnlyNote } from "@/components/ui/ReadOnlyNote";
import { RefreshButton } from "@/components/ui/RefreshButton";
import { SyncButton } from "@/components/ui/SyncButton";

const STAGE_ROUTE: Record<string, string> = {
  data: "/data",
  regime: "/regime",
  scenarios: "/scenarios",
  risk_prepare: "/risk",
  qubo_model: "/quantum",
  rerank_polish: "/report",
};

export default async function OverviewPage() {
  const data = await loadConsoleOverview();
  const before = data?.true_cvar_before ?? null;
  const after = data?.true_cvar_after ?? null;
  const actions = data?.top_actions ?? [];
  const healthy = (data?.pipeline ?? []).filter((p) =>
    ["READY", "PASS", "OK"].includes(p.status.toUpperCase()),
  ).length;

  return (
    <>
      <PageHead
        eyebrow="Portfolio intelligence"
        title="Risk posture at a glance"
        sub="Tín hiệu cần để ra quyết định. Chi tiết từng chặng nằm ở menu bên trái."
        actions={
          <>
            <RefreshButton />
            <Btn href="/report" icon={<FileDown size={14} />}>
              Decision package
            </Btn>
            <SyncButton />
          </>
        }
      />

      <ReadOnlyNote>
        Số liệu đọc từ artifact của lần chạy pipeline gần nhất. Console không tính lại CVaR;{" "}
        <strong>Sync to Supabase</strong> chỉ đẩy snapshot hiện tại lên database.
      </ReadOnlyNote>

      {!data?.online ? (
        <section className="card card-pad">
          <div className="card-title">Waiting for backend</div>
          <p className="card-sub">
            Khi API `/console/overview` sẵn sàng, overview sẽ hiển thị CVaR, pipeline và
            recommended actions từ artifact / Supabase snapshot.
          </p>
        </section>
      ) : (
        <>
          <section className="card hero">
            <div className="hero-grid">
              <div>
                <div className="hero-kicker">
                  <span className="hero-kicker-dot" />
                  {data.profile_status} · {data.actual_solver ?? "pending"}
                </div>
                <h2 className="hero-title">
                  {before !== null && after !== null && after < before
                    ? "Tail-risk is lower after the cash hedge, within cost constraints."
                    : "Evidence available for review — treat as NON_BASELINE until gates pass."}
                </h2>
                <p className="hero-text">
                  Regime và stress scenario xác định điểm chịu áp lực; QUBO/exact tìm bộ hành
                  động bị ràng buộc. Khuyến nghị cuối được chấm lại bằng true CVaR, không phải
                  bằng objective value. Đây là prototype phân tích kịch bản, không phải tư vấn
                  đầu tư.
                </p>
                <div className="hero-tags">
                  <span className="hero-tag">VN30 universe</span>
                  <span className="hero-tag">
                    {data.scenario_count
                      ? `${data.scenario_count.toLocaleString()} scenarios`
                      : "Scenarios"}
                  </span>
                  <span className="hero-tag">CVaR-aware (loss)</span>
                  <span className="hero-tag">Top-{data.candidate_count}</span>
                </div>
              </div>
              <aside className="decision-panel">
                <div className="decision-top">
                  <div className="decision-label">Recommended action</div>
                  <div className={`status-pill ${data.materiality_met ? "good" : "warn"}`}>
                    {data.materiality_met ? "MATERIALITY PASS" : "REVIEW"}
                  </div>
                </div>
                <div className="decision-title">
                  {actions.length
                    ? `Trim ${actions.map((a) => a.ticker).join(", ")} toward cash.`
                    : "No polished sell actions in current snapshot."}
                </div>
                <div className="decision-copy">
                  Solver: {data.actual_solver ?? "—"}. Constraints:{" "}
                  {data.constraints_passed ? "PASS" : "CHECK"}. Loss CVaR {pct(before)} →{" "}
                  {pct(after)}.
                </div>
                <div className="decision-row">
                  {(actions.length ? actions : [{ ticker: "—", polished_reduction: 0 }]).map(
                    (a) => (
                      <div className="decision-mini" key={a.ticker}>
                        <span>{a.ticker}</span>
                        <strong>
                          {a.polished_reduction
                            ? `-${(a.polished_reduction * 100).toFixed(0)}pp`
                            : "—"}
                        </strong>
                      </div>
                    ),
                  )}
                </div>
              </aside>
            </div>
          </section>

          <section className="grid grid-4 section-gap">
            <article className="card metric">
              <div className="metric-top">
                <div className="metric-label">CVaR 95% (loss)</div>
                <span className="metric-badge good">
                  <TrendingDown size={11} />
                  {ppDelta(before, after)}
                </span>
              </div>
              <div className="metric-value">{pct(after)}</div>
              <div className="metric-note">Was {pct(before)}</div>
            </article>
            <article className="card metric">
              <div className="metric-top">
                <div className="metric-label">Relative reduction</div>
                <span className="metric-badge good">
                  {pct(data.true_cvar_relative_reduction, 1)}
                </span>
              </div>
              <div className="metric-value">{pct(data.true_cvar_relative_reduction, 1)}</div>
              <div className="metric-note">True CVaR relative reduction</div>
            </article>
            <article className="card metric">
              <div className="metric-top">
                <div className="metric-label">Transaction cost</div>
                <span className="metric-badge good">Recorded</span>
              </div>
              <div className="metric-value">{pct(data.transaction_cost, 3)}</div>
              <div className="metric-note">Turnover {pct(data.turnover, 1)}</div>
            </article>
            <article className="card metric">
              <div className="metric-top">
                <div className="metric-label">Candidates</div>
                <span className="metric-badge warn">{data.profile_status}</span>
              </div>
              <div className="metric-value">{data.candidate_count}</div>
              <div className="metric-note">Dynamic top-10 handoff</div>
            </article>
          </section>

          <section className="grid grid-2-1 section-gap">
            <article className="card card-pad">
              <div className="card-head">
                <div>
                  <div className="card-label">Pipeline health</div>
                  <div className="card-title">From data to decision</div>
                  <div className="card-sub">
                    Bấm vào một chặng để mở trang bằng chứng tương ứng.
                  </div>
                </div>
                <span className="tag good">
                  {healthy} / {(data.pipeline ?? []).length} healthy
                </span>
              </div>
              <div className="pipeline">
                {(data.pipeline ?? []).map((p) => (
                  <Link
                    className="pipeline-row"
                    key={p.key}
                    href={STAGE_ROUTE[p.key] ?? "/overview"}
                  >
                    <div className="step">{p.step}</div>
                    <div>
                      <div className="pipeline-name">{p.name}</div>
                      <div className="pipeline-desc">{p.description}</div>
                    </div>
                    <div className={`state ${stageTone(p.status)}`}>{p.status}</div>
                    <ChevronRight size={15} className="pipeline-chevron" />
                  </Link>
                ))}
              </div>
            </article>

            <div className="grid">
              <article className="card card-pad">
                <div className="card-head">
                  <div>
                    <div className="card-label">Risk compression</div>
                    <div className="card-title">Before → after (loss)</div>
                  </div>
                  <Link href="/risk" className="btn">
                    <ArrowRight size={14} />
                    Open Risk
                  </Link>
                </div>
                <div className="risk-bars">
                  <div className="risk-row">
                    <div className="risk-label">CVaR 95%</div>
                    <div className="bar-track">
                      <div
                        className="bar-before"
                        style={{ width: `${Math.min(100, (before ?? 0) * 1000)}%` }}
                      />
                      <div
                        className="bar-after"
                        style={{ width: `${Math.min(100, (after ?? 0) * 1000)}%` }}
                      />
                    </div>
                    <div className="risk-value">{ppDelta(before, after)}</div>
                  </div>
                </div>
              </article>

              <article className="card card-pad">
                <div className="card-label">Attention</div>
                <div className="card-title">
                  {(data.warnings ?? []).length
                    ? `${data.warnings.length} warning${data.warnings.length > 1 ? "s" : ""} to review`
                    : "No extra warnings"}
                </div>
                <div className="callout warning" style={{ marginTop: 14 }}>
                  <div className="callout-title">{data.profile_status}</div>
                  <div className="callout-copy">
                    Treat this run as evidence for review — not an official baseline UAT claim
                    until gates pass.
                  </div>
                </div>
                {(data.warnings ?? []).length ? (
                  <ul className="warning-list">
                    {data.warnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                ) : null}
              </article>
            </div>
          </section>
        </>
      )}
    </>
  );
}
