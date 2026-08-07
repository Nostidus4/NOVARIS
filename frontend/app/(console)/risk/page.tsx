import { Atom } from "lucide-react";
import { loadConsoleRisk } from "@/lib/api";
import { num, pct, ppDelta } from "@/lib/format";
import { Btn, PageHead } from "@/components/ui/PageHead";
import { ReadOnlyNote } from "@/components/ui/ReadOnlyNote";
import { RefreshButton } from "@/components/ui/RefreshButton";
import { CandidateTable } from "@/components/risk/CandidateTable";

export default async function RiskPage() {
  const data = await loadConsoleRisk();
  const before = data?.true_cvar_before ?? null;
  const after = data?.true_cvar_after ?? null;
  const candidates = data?.candidates ?? [];
  const top = data?.top_candidate;

  return (
    <>
      <PageHead
        eyebrow="04 / Tail-risk analysis"
        title="Risk Ranking"
        sub="Xếp hạng theo net risk score để chọn dynamic top-10 làm đầu vào cho bước tối ưu."
        actions={
          <>
            <RefreshButton />
            <Btn href="/quantum" primary icon={<Atom size={14} />}>
              Optimizer
            </Btn>
          </>
        }
      />

      <ReadOnlyNote>
        CVaR tính trên phân phối loss (loss dương = lỗ); số cao hơn nghĩa là rủi ro đuôi lớn hơn.
      </ReadOnlyNote>

      <section className="grid grid-2" style={{ marginTop: 0 }}>
        <article className="card card-pad">
          <div className="card-head">
            <div>
              <div className="card-label">Portfolio impact</div>
              <div className="card-title">Before → after (true CVaR loss)</div>
            </div>
            <span className="tag info">{data?.candidate_count ?? 0} candidates</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Before</th>
                  <th>After</th>
                  <th>Delta</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <strong>CVaR 95% (loss)</strong>
                  </td>
                  <td>{pct(before)}</td>
                  <td>{pct(after)}</td>
                  <td>
                    <span className="tag good">{ppDelta(before, after)}</span>
                  </td>
                </tr>
                <tr>
                  <td>
                    <strong>Transaction cost</strong>
                  </td>
                  <td>—</td>
                  <td>{pct(data?.transaction_cost, 3)}</td>
                  <td>
                    <span className="tag info">recorded</span>
                  </td>
                </tr>
                <tr>
                  <td>
                    <strong>Turnover</strong>
                  </td>
                  <td>—</td>
                  <td>{pct(data?.turnover, 1)}</td>
                  <td>
                    <span className="tag info">cash hedge</span>
                  </td>
                </tr>
                <tr>
                  <td>
                    <strong>Materiality</strong>
                  </td>
                  <td>—</td>
                  <td>{data?.materiality_met ? "PASS" : "FAIL/PENDING"}</td>
                  <td>
                    <span className={`tag ${data?.materiality_met ? "good" : "warn"}`}>
                      gate
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
        <article className="card card-pad">
          <div className="card-label">Selected candidate</div>
          <div className="card-title">
            {top?.ticker ?? "—"} · Rank #{top?.rank ?? "—"}
          </div>
          <div className="card-sub">{top?.reason ?? "Top-10 by net risk score"}</div>
          <div className="grid grid-2" style={{ marginTop: 16 }}>
            <div className="callout">
              <div className="card-label">Net risk score</div>
              <div className="metric-value" style={{ fontSize: 23 }}>
                {num(top?.net_risk_score, 4)}
              </div>
            </div>
            <div className="callout">
              <div className="card-label">CVaR contrib.</div>
              <div className="metric-value" style={{ fontSize: 23 }}>
                {pct(top?.baseline_cvar_contribution, 2)}
              </div>
            </div>
            <div className="callout">
              <div className="card-label">Txn. cost est.</div>
              <div className="metric-value" style={{ fontSize: 23 }}>
                {pct(top?.transaction_cost_estimate, 3)}
              </div>
            </div>
            <div className="callout">
              <div className="card-label">Weight</div>
              <div className="metric-value" style={{ fontSize: 23 }}>
                {pct(top?.current_weight, 1)}
              </div>
            </div>
          </div>
        </article>
      </section>

      <section className="card card-pad section-gap">
        <div className="card-head">
          <div>
            <div className="card-label">Candidate universe</div>
            <div className="card-title">Dynamic top-10 risk ranking</div>
            <div className="card-sub">
              Sắp xếp theo cột bất kỳ, lọc theo trạng thái. Ranking là đầu vào cho optimizer,
              không phải hành động cuối cùng.
            </div>
          </div>
          <span className="tag good">{candidates.length} rows</span>
        </div>
        <CandidateTable rows={candidates} />
      </section>
    </>
  );
}
