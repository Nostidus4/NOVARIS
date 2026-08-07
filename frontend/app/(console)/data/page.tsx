import { CheckCircle2, FileClock } from "lucide-react";
import { loadConsoleData } from "@/lib/api";
import { Btn, PageHead } from "@/components/ui/PageHead";
import { ReadOnlyNote } from "@/components/ui/ReadOnlyNote";
import { RefreshButton } from "@/components/ui/RefreshButton";
import { QualityTable } from "@/components/data/QualityTable";

export default async function DataGatePage() {
  const data = await loadConsoleData();
  const checks = data?.data_quality ?? [];

  return (
    <>
      <PageHead
        eyebrow="01 / Input assurance"
        title="Data Gate"
        sub="Cổng kiểm tra dữ liệu đầu vào trước khi regime, scenario và quantum được phép chạy."
        actions={
          <>
            <RefreshButton />
            <Btn href="/report" icon={<FileClock size={14} />}>
              Audit log
            </Btn>
          </>
        }
      />

      <ReadOnlyNote>
        Kết quả đọc từ `data_quality_report.csv` — chạy lại check bằng `qshield-data` ở CLI.
      </ReadOnlyNote>

      <section className="grid grid-4">
        <article className="card metric">
          <div className="metric-top">
            <div className="metric-label">Quality checks</div>
            <span className="metric-badge good">
              <CheckCircle2 size={11} />
              {data?.checks_passed ?? 0}/{data?.checks_total ?? 0}
            </span>
          </div>
          <div className="metric-value">{data?.checks_total ?? "—"}</div>
          <div className="metric-note">From data_quality_report</div>
        </article>
        <article className="card metric">
          <div className="metric-top">
            <div className="metric-label">Universe</div>
            <span className="metric-badge good">VN30</span>
          </div>
          <div className="metric-value">{data?.universe_count ?? "—"}</div>
          <div className="metric-note">Tickers in snapshot</div>
        </article>
        <article className="card metric">
          <div className="metric-top">
            <div className="metric-label">Adj.close evidence</div>
            <span className="metric-badge warn">Review</span>
          </div>
          <div className="metric-value">{data?.evidence_count ?? "—"}</div>
          <div className="metric-note">Evidence rows</div>
        </article>
        <article className="card metric">
          <div className="metric-top">
            <div className="metric-label">Gate status</div>
            <span className="metric-badge good">{data?.stage_status ?? "—"}</span>
          </div>
          <div className="metric-value">{data?.stage_status ?? "—"}</div>
          <div className="metric-note">{data?.config_version ?? ""}</div>
        </article>
      </section>

      <section className="grid grid-3-2 section-gap">
        <article className="card card-pad">
          <div className="card-head">
            <div>
              <div className="card-label">Source validation</div>
              <div className="card-title">Feed-level checks</div>
            </div>
            <span className="tag good">{data?.checks_passed ?? 0} pass</span>
          </div>
          <QualityTable rows={checks} />
        </article>
        <article className="card card-pad">
          <div className="card-label">Data contract</div>
          <div className="card-title">Gate logic</div>
          <div className="list" style={{ marginTop: 13 }}>
            <div className="list-row">
              <div>
                <div className="list-title">Manifest</div>
                <div className="list-sub">data_manifest present</div>
              </div>
              <div className="list-value">{data?.manifest_present ? "YES" : "NO"}</div>
            </div>
            <div className="list-row">
              <div>
                <div className="list-title">Universe rows</div>
                <div className="list-sub">30-name snapshot</div>
              </div>
              <div className="list-value">{data?.universe_count ?? 0}</div>
            </div>
            <div className="list-row">
              <div>
                <div className="list-title">No return ffill</div>
                <div className="list-sub">CLAUDE.md rule 3</div>
              </div>
              <div className="list-value">Enforced</div>
            </div>
            <div className="list-row">
              <div>
                <div className="list-title">Gate result</div>
                <div className="list-sub">Model execution permission</div>
              </div>
              <div className="list-value">{data?.stage_status ?? "—"}</div>
            </div>
          </div>
        </article>
      </section>
    </>
  );
}
