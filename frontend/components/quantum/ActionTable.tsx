"use client";

import { useMemo } from "react";
import { pct } from "@/lib/format";
import type { ActionMini } from "@/lib/types";
import { DataTable, type Column, type Filter } from "@/components/ui/DataTable";

function solverBadgeTone(solver: string | null | undefined): string {
  return solver === "qaoa" ? "good" : "warn";
}

const BASE_COLUMNS: Column<ActionMini>[] = [
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
    label: "Solver reduction",
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

type Props = {
  rows: ActionMini[];
  /** `actual_solver` của run này — cột "Source solver" nhắc lại trên từng dòng để không ai đọc
   * nhầm "Solver reduction" là kết quả QAOA khi run thực chạy exact/classical. */
  sourceSolver?: string | null;
};

export function ActionTable({ rows, sourceSolver = null }: Props) {
  const columns = useMemo<Column<ActionMini>[]>(
    () => [
      ...BASE_COLUMNS,
      {
        key: "source_solver",
        label: "Source solver",
        render: () => (
          <span className={`tag ${solverBadgeTone(sourceSolver)}`}>{sourceSolver ?? "n/a"}</span>
        ),
      },
    ],
    [sourceSolver],
  );

  return (
    <DataTable
      rows={rows}
      columns={columns}
      filters={FILTERS}
      rowKey={(r) => r.ticker}
      searchText={(r) => r.ticker}
      searchPlaceholder="Lọc theo ticker…"
      emptyMessage="Không có hành động khớp bộ lọc"
    />
  );
}
