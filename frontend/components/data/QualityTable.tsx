"use client";

import type { DataQualityRow } from "@/lib/types";
import { DataTable, type Column, type Filter } from "@/components/ui/DataTable";

const isPass = (row: DataQualityRow) => (row.status ?? "").toUpperCase() === "PASS";

const COLUMNS: Column<DataQualityRow>[] = [
  {
    key: "check",
    label: "Check",
    sortValue: (r) => r.check_name ?? r.check_id ?? "",
    render: (r) => <strong>{r.check_name ?? r.check_id ?? "—"}</strong>,
  },
  { key: "type", label: "Type", sortValue: (r) => r.type ?? "", render: (r) => r.type ?? "—" },
  {
    key: "count",
    label: "Count",
    sortValue: (r) => r.count ?? null,
    render: (r) => r.count ?? "—",
  },
  { key: "trace", label: "Trace", render: (r) => r.trace ?? "—" },
  {
    key: "status",
    label: "Status",
    sortValue: (r) => (isPass(r) ? 1 : 0),
    render: (r) => (
      <span className={`tag ${isPass(r) ? "good" : "warn"}`}>{r.status ?? "—"}</span>
    ),
  },
];

const FILTERS: Filter<DataQualityRow>[] = [
  { id: "pass", label: "Pass", test: isPass },
  { id: "attention", label: "Cần xem", test: (r) => !isPass(r) },
];

export function QualityTable({ rows }: { rows: DataQualityRow[] }) {
  return (
    <DataTable
      rows={rows}
      columns={COLUMNS}
      filters={FILTERS}
      rowKey={(r, i) => `${r.check_id ?? "check"}-${i}`}
      searchText={(r) => `${r.check_name ?? ""} ${r.check_id ?? ""} ${r.trace ?? ""}`}
      searchPlaceholder="Tìm check hoặc trace…"
      emptyMessage="Không có check khớp bộ lọc"
    />
  );
}
