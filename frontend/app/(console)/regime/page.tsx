import { Waves } from "lucide-react";
import { loadConsoleRegime } from "@/lib/api";
import { num } from "@/lib/format";
import { Btn, PageHead } from "@/components/ui/PageHead";
import { ReadOnlyNote } from "@/components/ui/ReadOnlyNote";
import { RefreshButton } from "@/components/ui/RefreshButton";
import { RegimeChart } from "@/components/regime/RegimeChart";

export default async function RegimePage() {
  const data = await loadConsoleRegime();
  const champion = data?.champion ?? {};
  const coverage = data?.coverage ?? {};
  const labels = Object.entries(data?.label_map ?? {}).slice(0, 4);
  const timeline = data?.timeline ?? [];

  return (
    <>
      <PageHead
        eyebrow="02 / AI inference"
        title="Market Regime"
        sub="HMM xác định trạng thái thị trường, để scenario và risk scoring không dùng chung một giả định cho mọi điều kiện."
        actions={
          <>
            <RefreshButton />
            <Btn href="/scenarios" icon={<Waves size={14} />}>
              Scenarios
            </Btn>
          </>
        }
      />

      <ReadOnlyNote>
        Nhãn regime gán theo thống kê qua `label_map`, không suy từ state id của HMM.
      </ReadOnlyNote>

      <section className="grid grid-3">
        <article className="card card-pad">
          <div className="card-label">Current state</div>
          <div className="card-title" style={{ fontSize: 28 }}>
            {data?.latest?.regime ?? `seed ${String(champion.seed ?? "—")}`}
          </div>
          <p className="card-sub">
            n_states={String(champion.n_states ?? "—")} · cov=
            {String(champion.covariance_type ?? "—")} · converged=
            {String(champion.converged ?? "—")}
          </p>
          <div className="callout primary" style={{ marginTop: 16 }}>
            <div className="callout-title">
              Gate {data?.gate_status ?? "—"} · AIC {num(champion.aic as number | undefined, 1)}
            </div>
            <div className="callout-copy">
              BIC {num(champion.bic as number | undefined, 1)} · run mode{" "}
              {data?.run_mode ?? "—"}.
            </div>
          </div>
        </article>
        <article className="card card-pad">
          <div className="card-label">Coverage</div>
          <div className="card-title">Train / val / test</div>
          <div className="list" style={{ marginTop: 12 }}>
            <div className="list-row">
              <div className="list-title">Range</div>
              <div className="list-value">
                {String(coverage.start ?? "—")} → {String(coverage.end ?? "—")}
              </div>
            </div>
            <div className="list-row">
              <div className="list-title">Rows</div>
              <div className="list-value">{String(coverage.n_rows ?? "—")}</div>
            </div>
            <div className="list-row">
              <div className="list-title">Latest probs</div>
              <div className="list-value">
                N {num(data?.latest?.prob_normal, 2)} / V{" "}
                {num(data?.latest?.prob_volatile, 2)} / S {num(data?.latest?.prob_stress, 2)}
              </div>
            </div>
          </div>
        </article>
        <article className="card card-pad">
          <div className="card-label">Label map</div>
          <div className="card-title">State → regime name</div>
          <div className="list" style={{ marginTop: 12 }}>
            {labels.length ? (
              labels.map(([k, v]) => (
                <div className="list-row" key={k}>
                  <div>
                    <div className="list-title">state {k}</div>
                    <div className="list-sub">HMM raw id</div>
                  </div>
                  <div className="tag info">{v}</div>
                </div>
              ))
            ) : (
              <div className="list-row">
                <div>
                  <div className="list-title">Scenario weighting</div>
                  <div className="list-sub">Conditioned on inferred regime</div>
                </div>
                <div className="tag info">↑</div>
              </div>
            )}
          </div>
        </article>
      </section>

      <section className="card card-pad section-gap">
        <div className="card-head">
          <div>
            <div className="card-label">Regime probability</div>
            <div className="card-title">Recent inference trend</div>
            <div className="card-sub">
              {timeline.length} phiên trong artifact — chọn khoảng thời gian, bật/tắt từng
              đường, di chuột để đọc xác suất của một phiên.
            </div>
          </div>
          <span className="tag warn">{data?.latest?.regime ?? "—"}</span>
        </div>
        <RegimeChart timeline={timeline} />
      </section>
    </>
  );
}
