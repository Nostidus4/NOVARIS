"use client";

import type { ScenarioValidationRow } from "@/lib/types";
import { DataTable, type Column, type Filter } from "@/components/ui/DataTable";

const COLUMNS: Column<ScenarioValidationRow>[] = [
  {
    key: "regime",
    label: "Regime",
    sortValue: (r) => r.target_regime,
    render: (r) => <strong>{r.target_regime}</strong>,
  },
  { key: "metric", label: "Metric", sortValue: (r) => r.metric, render: (r) => r.metric },
  {
    key: "scenario",
    label: "Scenario",
    sortValue: (r) => r.scenario_value,
    render: (r) => r.scenario_value.toFixed(4),
  },
  {
    key: "reference",
    label: "Reference",
    sortValue: (r) => r.reference_value,
    render: (r) => r.reference_value.toFixed(4),
  },
  {
    key: "statistic",
    label: "Statistic",
    sortValue: (r) => r.statistic,
    render: (r) => r.statistic.toFixed(4),
  },
  {
    key: "verdict",
    label: "Verdict",
    sortValue: (r) => (r.verdict === "PASS" ? 1 : 0),
    render: (r) => (
      <span className={`tag ${r.verdict === "PASS" ? "good" : "warn"}`}>{r.verdict}</span>
    ),
  },
];

const FILTERS: Filter<ScenarioValidationRow>[] = [
  { id: "fail", label: "Fail", test: (r) => r.verdict !== "PASS" },
  { id: "pass", label: "Pass", test: (r) => r.verdict === "PASS" },
];

export function ValidationTable({ rows }: { rows: ScenarioValidationRow[] }) {
  return (
    <DataTable
      rows={rows}
      columns={COLUMNS}
      filters={FILTERS}
      rowKey={(r, i) => `${r.target_regime}-${r.metric}-${i}`}
      searchText={(r) => `${r.target_regime} ${r.metric}`}
      searchPlaceholder="Tìm theo regime hoặc metric…"
      emptyMessage="Không có dòng validation khớp bộ lọc"
    />
  );
}
