import {
  Binary,
  FileText,
  ListOrdered,
  Scale,
  Sparkles,
  SlidersHorizontal,
  TriangleAlert,
} from "lucide-react";
import { loadConsoleQuantum } from "@/lib/api";
import { Btn, PageHead } from "@/components/ui/PageHead";
import { ReadOnlyNote } from "@/components/ui/ReadOnlyNote";
import { RefreshButton } from "@/components/ui/RefreshButton";
import { ActionTable } from "@/components/quantum/ActionTable";
import { RunOptimizePanel } from "@/components/quantum/RunOptimizePanel";

const FLOW = [
  { no: "01", title: "Top-10 input", sub: "Risk-ranked assets", Icon: ListOrdered },
  { no: "02", title: "QUBO build", sub: "Objective + penalties", Icon: SlidersHorizontal },
  { no: "03", title: "Solve", sub: "Exact / QAOA", Icon: Sparkles },
  { no: "04", title: "Decode", sub: "Action levels", Icon: Binary },
  { no: "05", title: "Polish", sub: "Hard constraints", Icon: Scale },
  { no: "06", title: "Decision", sub: "True CVaR score", Icon: FileText },
];

export default async function QuantumPage() {
  const data = await loadConsoleQuantum();
  const actions = data?.actions ?? [];

  return (
    <>
      <PageHead
        eyebrow="05 / Optimization engine"
        title="Quantum Optimizer"
        sub="QUBO → exact hoặc QAOA → decode → polish → chấm lại bằng true CVaR."
        actions={
          <>
            <RefreshButton />
            <Btn href="/report" icon={<FileText size={14} />}>
              Decision package
            </Btn>
          </>
        }
      />

      <ReadOnlyNote>
        Exact solver là thước đo chuẩn, QAOA là bên thách thức — kết quả ở đây không chứng minh
        quantum advantage.
      </ReadOnlyNote>

      {data && data.online && data.actual_solver !== "qaoa" ? (
        <div className="solver-warning-banner">
          <TriangleAlert size={18} />
          <div>
            <div className="solver-warning-banner-title">
              Không có kết quả QAOA trong lần chạy này
            </div>
            <div className="solver-warning-banner-copy">
              Solver thực tế đã sinh ra các con số dưới đây là{" "}
              <strong>{data.actual_solver ?? "unknown"}</strong>, không phải QAOA.{" "}
              {data.fallback_reason
                ? `Lý do: ${data.fallback_reason}.`
                : "Không có fallback_reason nào được artifact ghi lại."}{" "}
              Mọi nhãn &quot;solver reduction&quot; bên dưới mô tả nghiệm của solver này (thường
              là brute-force exact), không phải QAOA.
            </div>
          </div>
        </div>
      ) : null}

      <section className="card card-pad">
        <div className="card-head">
          <div>
            <div className="card-label">Optimization flow</div>
            <div className="card-title">
              Risk candidates → QUBO → solve → constraint polish → decision
            </div>
          </div>
          <span className="tag info">{data?.actual_solver ?? "pending"}</span>
        </div>
        <div className="process-line">
          {FLOW.map(({ no, title, sub, Icon }) => (
            <div className="process-node" key={no}>
              <div className="process-icon">
                <Icon size={14} />
              </div>
              <div className="process-no">{no}</div>
              <div className="process-title">{title}</div>
              <div className="process-sub">{sub}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid grid-2 section-gap">
        <article className="card card-pad">
          <div className="card-head">
            <div>
              <div className="card-label">Run result</div>
              <div className="card-title">{data?.actual_solver ?? "—"}</div>
              <div className="card-sub">
                {data?.caveat ?? "Exact is ground truth; QAOA is challenger."}
              </div>
            </div>
            <span className="tag info">{data?.winning_bitstring ?? "bits"}</span>
          </div>
          <div className="grid grid-2">
            <div className="callout primary">
              <div className="card-label">Actual solver</div>
              <div className="metric-value" style={{ fontSize: 23 }}>
                {data?.actual_solver ?? "—"}
              </div>
            </div>
            <div className="callout">
              <div className="card-label">Constraints</div>
              <div
                className="metric-value"
                style={{
                  color: !data?.constraints_evaluated
                    ? "var(--muted)"
                    : data?.constraints_passed
                      ? "var(--success)"
                      : "var(--warning)",
                  fontSize: 23,
                }}
              >
                {!data?.constraints_evaluated
                  ? "NOT_EVALUATED"
                  : data?.constraints_passed
                    ? "PASS"
                    : "FAIL"}
              </div>
              {!data?.constraints_evaluated ? (
                <div className="card-sub">Không có quantum_constraints/risk_policy nào được encode.</div>
              ) : null}
            </div>
            <div className="callout">
              <div className="card-label">Exact energy</div>
              <div className="metric-value" style={{ fontSize: 23 }}>
                {data?.exact_best_energy !== null && data?.exact_best_energy !== undefined
                  ? data.exact_best_energy.toFixed(4)
                  : "—"}
              </div>
            </div>
            <div className="callout">
              <div className="card-label">Feasible rate</div>
              <div className="metric-value" style={{ fontSize: 23 }}>
                {!data?.constraints_evaluated ||
                data?.mean_feasibility_rate === null ||
                data?.mean_feasibility_rate === undefined
                  ? "n/a"
                  : data.mean_feasibility_rate.toFixed(2)}
              </div>
              {!data?.constraints_evaluated ? (
                <div className="card-sub">n/a — no constraints encoded</div>
              ) : null}
            </div>
          </div>
        </article>
        <article className="card card-pad">
          <div className="card-head">
            <div>
              <div className="card-label">Bit mapping</div>
              <div className="card-title">Four-level action decode</div>
            </div>
            <span className="tag info">2 bits / ticker</span>
          </div>
          <div className="quantum-grid">
            {[
              ["00", "0%"],
              ["10", "10%"],
              ["01", "20%"],
              ["11", "30%"],
            ].map(([code, value]) => (
              <div className="bit" key={code}>
                <div className="bit-code">{code}</div>
                <div className="bit-value">{value}</div>
              </div>
            ))}
          </div>
          <div className="callout" style={{ marginTop: 14 }}>
            <div className="callout-title">Benchmark honesty</div>
            <div className="callout-copy">
              QAOA thắng classical:{" "}
              <strong>{String(data?.qaoa_beats_classical ?? "n/a")}</strong> · optimality gap{" "}
              {data?.optimality_gap !== null && data?.optimality_gap !== undefined
                ? data.optimality_gap.toFixed(4)
                : "—"}
              . Hành động thô từ solver chỉ là đề xuất; bản cuối phải qua polish và ràng buộc
              danh mục.
            </div>
          </div>
        </article>
      </section>

      <section className="card card-pad section-gap">
        <div className="card-head">
          <div>
            <div className="card-label">Polishing dependency</div>
            <div className="card-title">Solver vs. classical local polish contribution</div>
            <div className="card-sub">
              Tỷ lệ phần cải thiện CVaR đến từ bước polish cổ điển (±5pp, zero-lock) thay vì từ
              solver (exact/QAOA). Càng cao nghĩa là phần cải thiện càng đến từ polish, không phải
              từ solver.
            </div>
          </div>
        </div>
        <div className="callout primary">
          <div className="card-label">polishing_dependency</div>
          <div className="metric-value" style={{ fontSize: 28 }}>
            {data?.polishing_dependency !== null && data?.polishing_dependency !== undefined
              ? `${(data.polishing_dependency * 100).toFixed(1)}%`
              : "—"}
          </div>
        </div>
      </section>

      <section className="card card-pad section-gap">
        <div className="card-head">
          <div>
            <div className="card-label">Action reconciliation</div>
            <div className="card-title">Solver output vs. polished final action</div>
            <div className="card-sub">
              Lọc nhanh những mã mà polish lệch khỏi nghiệm solver để soát lại ràng buộc.
            </div>
          </div>
          <span className="tag good">{actions.length} rows</span>
        </div>
        <ActionTable rows={actions} sourceSolver={data?.actual_solver ?? null} />
      </section>

      <section className="section-gap">
        <RunOptimizePanel tickers={actions.map((a) => a.ticker)} />
      </section>
    </>
  );
}
