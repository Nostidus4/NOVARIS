"use client";

import { useMemo, useState } from "react";
import type { RegimePoint } from "@/lib/types";

const RANGES = [30, 60, 120, 0] as const;
const SERIES = [
  { key: "prob_stress", label: "Stress", cls: "line1" },
  { key: "prob_volatile", label: "Volatile", cls: "line2" },
  { key: "prob_normal", label: "Normal", cls: "line3" },
] as const;

type SeriesKey = (typeof SERIES)[number]["key"];

const W = 900;
const H = 190;
const PAD = 14;

export function RegimeChart({ timeline }: { timeline: RegimePoint[] }) {
  const [range, setRange] = useState<number>(60);
  const [hidden, setHidden] = useState<Set<SeriesKey>>(new Set(["prob_normal"]));
  const [hover, setHover] = useState<number | null>(null);

  const points = useMemo(
    () => (range === 0 ? timeline : timeline.slice(-range)),
    [timeline, range],
  );

  const xFor = (i: number) => (points.length <= 1 ? W / 2 : (i / (points.length - 1)) * W);
  const yFor = (v: number) => PAD + (1 - Math.min(Math.max(v, 0), 1)) * (H - PAD * 2);

  const active = hover !== null && points[hover] ? points[hover] : points[points.length - 1];

  function toggle(key: SeriesKey) {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function onMove(e: React.MouseEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    const idx = Math.round(ratio * (points.length - 1));
    setHover(Math.min(Math.max(idx, 0), points.length - 1));
  }

  return (
    <div>
      <div className="chart-controls">
        <div className="chip-row">
          {RANGES.map((r) => (
            <button
              key={r}
              type="button"
              className={`chip ${range === r ? "active" : ""}`}
              onClick={() => {
                setRange(r);
                setHover(null);
              }}
            >
              {r === 0 ? "All" : `${r}d`}
            </button>
          ))}
        </div>
        <div className="legend">
          {SERIES.map((s) => (
            <button
              key={s.key}
              type="button"
              className={`legend-item ${hidden.has(s.key) ? "off" : ""}`}
              onClick={() => toggle(s.key)}
            >
              <span className={`legend-dot ${s.cls}`} />
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <svg
        className="sparkline interactive"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        role="img"
        aria-label="Regime probability chart"
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      >
        {[0.25, 0.5, 0.75].map((g) => (
          <line key={g} className="gridline" x1="0" y1={yFor(g)} x2={W} y2={yFor(g)} />
        ))}
        {SERIES.filter((s) => !hidden.has(s.key)).map((s) => (
          <polyline
            key={s.key}
            className={s.cls}
            points={points.map((p, i) => `${xFor(i).toFixed(1)},${yFor(p[s.key]).toFixed(1)}`).join(" ")}
          />
        ))}
        {hover !== null && points[hover] ? (
          <>
            <line className="cursor-line" x1={xFor(hover)} y1="0" x2={xFor(hover)} y2={H} />
            {SERIES.filter((s) => !hidden.has(s.key)).map((s) => (
              <circle
                key={s.key}
                className={`cursor-dot ${s.cls}`}
                cx={xFor(hover)}
                cy={yFor(points[hover][s.key])}
                r="4"
              />
            ))}
          </>
        ) : null}
      </svg>

      {active ? (
        <div className="chart-readout">
          <span className="readout-date">{active.date}</span>
          <span className={`tag ${active.regime.toLowerCase() === "stress" ? "warn" : "info"}`}>
            {active.regime}
          </span>
          <span>Normal {(active.prob_normal * 100).toFixed(1)}%</span>
          <span>Volatile {(active.prob_volatile * 100).toFixed(1)}%</span>
          <span>Stress {(active.prob_stress * 100).toFixed(1)}%</span>
          <span className="readout-hint">
            {hover === null ? "Di chuột lên biểu đồ để đọc từng phiên" : "Phiên đang trỏ"}
          </span>
        </div>
      ) : null}
    </div>
  );
}
