import { ShieldHalf } from "lucide-react";
import { loadConsoleScenarios } from "@/lib/api";
import { Btn, PageHead } from "@/components/ui/PageHead";
import { ReadOnlyNote } from "@/components/ui/ReadOnlyNote";
import { RefreshButton } from "@/components/ui/RefreshButton";
import { ValidationTable } from "@/components/scenarios/ValidationTable";

export default async function ScenariosPage() {
  const data = await loadConsoleScenarios();
  const validation = data?.validation ?? [];

  return (
    <>
      <PageHead
        eyebrow="03 / Stress engine"
        title="Stress Scenarios"
        sub="Moving-block bootstrap có điều kiện regime, giữ nguyên vector tương quan chéo giữa các mã."
        actions={
          <>
            <RefreshButton />
            <Btn href="/risk" icon={<ShieldHalf size={14} />}>
              Risk ranking
            </Btn>
          </>
        }
      />

      <ReadOnlyNote>
        Tensor kịch bản nằm ở `stress_scenarios.npz`; màn này chỉ đọc manifest và bảng validation.
      </ReadOnlyNote>

      <section className="grid grid-4">
        <article className="card metric">
          <div className="metric-label">Generated paths</div>
          <div className="metric-value">{data?.num_scenarios?.toLocaleString() ?? "—"}</div>
          <div className="metric-note">Stress universe</div>
        </article>
        <article className="card metric">
          <div className="metric-label">Horizon</div>
          <div className="metric-value">{data?.horizon_days ?? "—"}</div>
          <div className="metric-note">Trading days</div>
        </article>
        <article className="card metric">
          <div className="metric-label">Assets</div>
          <div className="metric-value">{data?.n_assets ?? "—"}</div>
          <div className="metric-note">Ticker dimension</div>
        </article>
        <article className="card metric">
          <div className="metric-label">Block length</div>
          <div className="metric-value">{data?.block_length ?? "—"}</div>
          <div className="metric-note">Moving-block bootstrap</div>
        </article>
      </section>

      <section className="grid grid-2 section-gap">
        <article className="card card-pad">
          <div className="card-head">
            <div>
              <div className="card-label">Scenario library</div>
              <div className="card-title">Manifest metadata</div>
            </div>
            <span className="tag info">{data?.gate_status ?? "—"}</span>
          </div>
          <div className="list">
            <div className="list-row">
              <div>
                <div className="list-title">Seed</div>
                <div className="list-sub">scenario_manifest.seed</div>
              </div>
              <div className="list-value">{String(data?.seed ?? "—")}</div>
            </div>
            <div className="list-row">
              <div>
                <div className="list-title">Return type</div>
                <div className="list-sub">No forward-fill on returns</div>
              </div>
              <div className="list-value">{data?.return_type ?? "—"}</div>
            </div>
            <div className="list-row">
              <div>
                <div className="list-title">Anchor window</div>
                <div className="list-sub">Bootstrap source days</div>
              </div>
              <div className="list-value">
                {data?.anchor_first ?? "—"} → {data?.anchor_last ?? "—"}
              </div>
            </div>
            <div className="list-row">
              <div>
                <div className="list-title">Reuse rate</div>
                <div className="list-sub">Block reuse diagnostic</div>
              </div>
              <div className="list-value">
                {data?.reuse_rate !== null && data?.reuse_rate !== undefined
                  ? data.reuse_rate.toFixed(4)
                  : "—"}
              </div>
            </div>
            <div className="list-row">
              <div>
                <div className="list-title">Target regime</div>
                <div className="list-sub">Conditioning</div>
              </div>
              <div className="list-value">{data?.target_regime ?? "—"}</div>
            </div>
          </div>
        </article>
        <article className="card card-pad">
          <div className="card-head">
            <div>
              <div className="card-label">Universe order</div>
              <div className="card-title">Ticker tensor axis</div>
            </div>
            <span className="tag warn">n_fail={data?.n_fail ?? 0}</span>
          </div>
          <div className="hero-tags" style={{ marginTop: 0 }}>
            {(data?.ticker_order?.length ? data.ticker_order : ["—"]).slice(0, 30).map((t) => (
              <span
                className="hero-tag"
                key={t}
                style={{
                  color: "var(--text)",
                  borderColor: "var(--line)",
                  background: "var(--surface-2)",
                }}
              >
                {t}
              </span>
            ))}
          </div>
        </article>
      </section>

      <section className="card card-pad section-gap">
        <div className="card-head">
          <div>
            <div className="card-label">Validation gate</div>
            <div className="card-title">scenario_validation.csv</div>
          </div>
          <span className={`tag ${(data?.n_fail ?? 0) === 0 ? "good" : "warn"}`}>
            {(data?.n_fail ?? 0) === 0 ? "All pass" : `${data?.n_fail} fail`}
          </span>
        </div>
        <ValidationTable rows={validation} />
      </section>
    </>
  );
}
