"use client";

import { pct } from "@/lib/format";
import type { ActionMini } from "@/lib/types";
import { DataTable, type Column, type Filter } from "@/components/ui/DataTable";

const COLUMNS: Column<ActionMini>[] = [
  {
    key: "ticker",
    label: "Ticker",
    sortValue: (r) => r.ticker,
    render: (r) => <strong>{r.ticker}</strong>,
  },
  {
    key: "current_weight",
    label: "Current weight",
    sortValue: (r) => r.current_weight ?? null,
    render: (r) => pct(r.current_weight, 2),
  },
  { key: "bits", label: "Bits", render: (r) => <code>{r.bits ?? "—"}</code> },
  {
    key: "quantum_reduction",
    label: "Quantum red.",
    sortValue: (r) => r.quantum_reduction ?? null,
    render: (r) => pct(r.quantum_reduction, 0),
  },
  {
    key: "polished_reduction",
    label: "Polished red.",
    sortValue: (r) => r.polished_reduction ?? null,
    render: (r) => <strong>{pct(r.polished_reduction, 0)}</strong>,
  },
  {
    key: "final_weight",
    label: "Final weight",
    sortValue: (r) => r.final_weight ?? null,
    render: (r) => pct(r.final_weight, 2),
  },
  {
    key: "sell_value",
    label: "Sell value",
    sortValue: (r) => r.sell_value ?? null,
    render: (r) => pct(r.sell_value, 2),
  },
];

const FILTERS: Filter<ActionMini>[] = [
  { id: "acting", label: "Có hành động", test: (r) => (r.polished_reduction ?? 0) > 0 },
  { id: "hold", label: "Giữ nguyên", test: (r) => !(r.polished_reduction ?? 0) },
  {
    id: "diverged",
    label: "Polish khác solver",
    test: (r) => (r.polished_reduction ?? 0) !== (r.quantum_reduction ?? 0),
  },
];

export function ActionTable({ rows }: { rows: ActionMini[] }) {
  return (
    <DataTable
      rows={rows}
      columns={COLUMNS}
      filters={FILTERS}
      rowKey={(r) => r.ticker}
      searchText={(r) => r.ticker}
      searchPlaceholder="Lọc theo ticker…"
      emptyMessage="Không có hành động khớp bộ lọc"
    />
  );
}
