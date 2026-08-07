"use client";

import { num, pct } from "@/lib/format";
import type { CandidateRow } from "@/lib/types";
import { DataTable, type Column, type Filter } from "@/components/ui/DataTable";

const COLUMNS: Column<CandidateRow>[] = [
  {
    key: "rank",
    label: "Rank",
    sortValue: (r) => r.rank ?? Number.MAX_SAFE_INTEGER,
    render: (r) => <strong>#{r.rank ?? "—"}</strong>,
  },
  {
    key: "ticker",
    label: "Ticker",
    sortValue: (r) => r.ticker ?? "",
    render: (r) => <strong>{r.ticker ?? "—"}</strong>,
  },
  {
    key: "eligible",
    label: "Eligible",
    sortValue: (r) => (r.eligible_status ? 1 : 0),
    render: (r) => (
      <span className={`tag ${r.eligible_status ? "good" : "warn"}`}>
        {r.eligible_status ? "ELIGIBLE" : "NO"}
      </span>
    ),
  },
  {
    key: "selected",
    label: "Top-10",
    sortValue: (r) => (r.selected_top10 ? 1 : 0),
    render: (r) =>
      r.selected_top10 ? <span className="tag good">SELECTED</span> : <span className="muted">—</span>,
  },
  {
    key: "net_risk",
    label: "Net risk",
    sortValue: (r) => r.net_risk_score ?? null,
    render: (r) => <strong>{num(r.net_risk_score, 4)}</strong>,
  },
  {
    key: "cvar",
    label: "CVaR contrib",
    sortValue: (r) => r.baseline_cvar_contribution ?? null,
    render: (r) => pct(r.baseline_cvar_contribution, 2),
  },
  {
    key: "cost",
    label: "Cost est.",
    sortValue: (r) => r.transaction_cost_estimate ?? null,
    render: (r) => pct(r.transaction_cost_estimate, 3),
  },
  {
    key: "liq",
    label: "Liq. penalty",
    sortValue: (r) => r.liquidity_penalty ?? null,
    render: (r) => num(r.liquidity_penalty, 6),
  },
  { key: "reason", label: "Reason", render: (r) => r.reason ?? "—" },
];

const FILTERS: Filter<CandidateRow>[] = [
  { id: "top10", label: "Top-10", test: (r) => r.selected_top10 },
  { id: "eligible", label: "Eligible", test: (r) => r.eligible_status },
  { id: "excluded", label: "Excluded", test: (r) => !r.eligible_status },
];

export function CandidateTable({ rows }: { rows: CandidateRow[] }) {
  return (
    <DataTable
      rows={rows}
      columns={COLUMNS}
      filters={FILTERS}
      rowKey={(r, i) => `${r.ticker ?? "row"}-${r.rank ?? i}`}
      searchText={(r) => `${r.ticker ?? ""} ${r.reason ?? ""}`}
      searchPlaceholder="Lọc theo ticker hoặc lý do…"
      emptyMessage="Không có candidate khớp bộ lọc"
    />
  );
}
