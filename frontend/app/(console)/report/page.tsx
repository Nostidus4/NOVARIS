import { FileText, LayoutDashboard, ScrollText } from "lucide-react";
import { loadConsoleReport } from "@/lib/api";
import { pct, ppDelta } from "@/lib/format";
import { Btn, PageHead } from "@/components/ui/PageHead";
import { ReadOnlyNote } from "@/components/ui/ReadOnlyNote";
import { RefreshButton } from "@/components/ui/RefreshButton";
import { DownloadJsonButton } from "@/components/report/DownloadJsonButton";
import { LogPanel } from "@/components/report/LogPanel";

export default async function ReportPage() {
  const data = await loadConsoleReport();
  const before = data?.true_cvar_before ?? null;
  const after = data?.true_cvar_after ?? null;
  const runTag = data?.run_id ?? data?.profile_id ?? "run";

  return (
    <>
      <PageHead
        eyebrow="06 / Decision package"
        title="Report & Audit Trail"
        sub="Tóm tắt điều hành, metadata lần chạy và dấu vết log để trình bày hoặc soát lại."
        actions={
          <>
            <RefreshButton />
            <Btn href="/overview" icon={<LayoutDashboard size={14} />}>
              Overview
            </Btn>
            {data ? (
              <DownloadJsonButton
                payload={data}
                filename={`qshield-decision-${runTag}.json`}
                label="Download package"
                primary
              />
            ) : null}
          </>
        }
      />

      <ReadOnlyNote>
        Mọi kết luận giới hạn trong phạm vi artifact hỗ trợ. File tải về là chính JSON mà console
        đang hiển thị, không phải bản dựng lại.
      </ReadOnlyNote>

      <section className="grid grid-2">
        <article className="card report-card">
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div className="report-icon">
              <FileText size={20} />
            </div>
            <div>
              <div className="card-title" style={{ marginTop: 0 }}>
                Executive decision report
              </div>
              <div className="card-sub">
                Thay đổi rủi ro chính, hành động được chọn và lý do.
              </div>
            </div>
          </div>
          {data ? (
            <DownloadJsonButton
              payload={{
                profile_id: data.profile_id,
                profile_status: data.profile_status,
                config_version: data.config_version,
                true_cvar_before: data.true_cvar_before,
                true_cvar_after: data.true_cvar_after,
                transaction_cost: data.transaction_cost,
                turnover: data.turnover,
                materiality_met: data.materiality_met,
                top_actions: data.top_actions,
                warnings: data.warnings,
              }}
              filename={`qshield-executive-${runTag}.json`}
              label="Export"
            />
          ) : (
            <span className="tag warn">Offline</span>
          )}
        </article>
        <article className="card report-card">
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div className="report-icon">
              <ScrollText size={20} />
            </div>
            <div>
              <div className="card-title" style={{ marginTop: 0 }}>
                Run audit log
              </div>
              <div className="card-sub">
                Data gate, regime, seed kịch bản và cấu hình optimizer.
              </div>
            </div>
          </div>
          {data ? (
            <DownloadJsonButton
              payload={{
                run_id: data.run_id,
                stage_status: data.stage_status,
                metrics: data.metrics,
                logs_tail: data.logs_tail,
              }}
              filename={`qshield-audit-${runTag}.json`}
              label="Export"
            />
          ) : (
            <span className="tag warn">Offline</span>
          )}
        </article>
      </section>

      <section className="grid grid-3-2 section-gap">
        <article className="card card-pad">
          <div className="card-head">
            <div>
              <div className="card-label">Executive summary</div>
              <div className="card-title">Baseline decision narrative</div>
            </div>
          </div>
          <div className="callout primary">
            <div className="callout-title">Decision</div>
            <div className="callout-copy">
              Solver {data?.actual_solver ?? "—"} sinh ra bộ hành động chuyển sang tiền mặt.
              True CVaR (loss) đi từ {pct(before)} xuống {pct(after)} ({ppDelta(before, after)}
              ). Đây là prototype phân tích kịch bản, không phải khuyến nghị mua bán.
            </div>
          </div>
          <div className="list" style={{ marginTop: 10 }}>
            <div className="list-row">
              <div>
                <div className="list-title">Primary objective</div>
                <div className="list-sub">Tail-risk compression (loss CVaR)</div>
              </div>
              <div className="list-value">
                {before !== null && after !== null && after < before ? "Improved" : "Review"}
              </div>
            </div>
            <div className="list-row">
              <div>
                <div className="list-title">Execution cost</div>
                <div className="list-sub">Recorded transaction cost</div>
              </div>
              <div className="list-value">{pct(data?.transaction_cost, 3)}</div>
            </div>
            <div className="list-row">
              <div>
                <div className="list-title">Residual warning</div>
                <div className="list-sub">{data?.warnings?.[0] ?? "None listed"}</div>
              </div>
              <div className="list-value" style={{ color: "var(--warning)" }}>
                Review
              </div>
            </div>
          </div>
        </article>
        <article className="card card-pad">
          <div className="card-label">Run metadata</div>
          <div className="card-title">{data?.profile_id ?? "offline"}</div>
          <div className="list" style={{ marginTop: 12 }}>
            <div className="list-row">
              <div className="list-title">Config</div>
              <div className="list-value">{data?.config_version ?? "—"}</div>
            </div>
            <div className="list-row">
              <div className="list-title">Universe</div>
              <div className="list-value">{data?.universe_count ?? "—"} tickers</div>
            </div>
            <div className="list-row">
              <div className="list-title">Scenarios</div>
              <div className="list-value">{data?.scenario_count?.toLocaleString() ?? "—"}</div>
            </div>
            <div className="list-row">
              <div className="list-title">Optimizer</div>
              <div className="list-value">{data?.actual_solver ?? "—"}</div>
            </div>
            <div className="list-row">
              <div className="list-title">Run id</div>
              <div className="list-value">{data?.run_id ?? "—"}</div>
            </div>
          </div>
        </article>
      </section>

      <section className="card card-pad section-gap">
        <div className="card-head">
          <div>
            <div className="card-label">Audit trail</div>
            <div className="card-title">logs.txt tail</div>
          </div>
          <span className="tag info">{(data?.logs_tail ?? []).length} lines</span>
        </div>
        <LogPanel lines={data?.logs_tail ?? []} />
      </section>
    </>
  );
}
