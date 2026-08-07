"use client";

import { useMemo, useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ChevronsUpDown, Search } from "lucide-react";

export type Column<T> = {
  key: string;
  label: string;
  render: (row: T) => ReactNode;
  sortValue?: (row: T) => number | string | null | undefined;
};

export type Filter<T> = {
  id: string;
  label: string;
  test: (row: T) => boolean;
};

type Props<T> = {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T, index: number) => string;
  searchText?: (row: T) => string;
  searchPlaceholder?: string;
  filters?: Filter<T>[];
  pageSize?: number;
  emptyMessage?: string;
};

export function DataTable<T>({
  rows,
  columns,
  rowKey,
  searchText,
  searchPlaceholder = "Search…",
  filters = [],
  pageSize = 12,
  emptyMessage = "No rows",
}: Props<T>) {
  const [query, setQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [sort, setSort] = useState<{ key: string; dir: "asc" | "desc" } | null>(null);
  const [expanded, setExpanded] = useState(false);

  const view = useMemo(() => {
    let out = rows;

    const filter = filters.find((f) => f.id === activeFilter);
    if (filter) out = out.filter(filter.test);

    const q = query.trim().toLowerCase();
    if (q && searchText) out = out.filter((row) => searchText(row).toLowerCase().includes(q));

    if (sort) {
      const col = columns.find((c) => c.key === sort.key);
      if (col?.sortValue) {
        const sign = sort.dir === "asc" ? 1 : -1;
        out = [...out].sort((a, b) => {
          const av = col.sortValue!(a);
          const bv = col.sortValue!(b);
          if (av === bv) return 0;
          if (av === null || av === undefined) return 1;
          if (bv === null || bv === undefined) return -1;
          return av > bv ? sign : -sign;
        });
      }
    }
    return out;
  }, [rows, filters, activeFilter, query, searchText, sort, columns]);

  const visible = expanded ? view : view.slice(0, pageSize);
  const hidden = view.length - visible.length;

  function toggleSort(key: string) {
    setSort((prev) => {
      if (!prev || prev.key !== key) return { key, dir: "desc" };
      if (prev.dir === "desc") return { key, dir: "asc" };
      return null;
    });
  }

  return (
    <div className="datatable">
      {(searchText || filters.length > 0) && (
        <div className="datatable-bar">
          {searchText ? (
            <label className="search-field">
              <Search size={14} />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={searchPlaceholder}
                spellCheck={false}
              />
            </label>
          ) : null}
          {filters.length > 0 ? (
            <div className="chip-row">
              <button
                type="button"
                className={`chip ${activeFilter === null ? "active" : ""}`}
                onClick={() => setActiveFilter(null)}
              >
                All ({rows.length})
              </button>
              {filters.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  className={`chip ${activeFilter === f.id ? "active" : ""}`}
                  onClick={() => setActiveFilter(activeFilter === f.id ? null : f.id)}
                >
                  {f.label} ({rows.filter(f.test).length})
                </button>
              ))}
            </div>
          ) : null}
        </div>
      )}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {columns.map((col) => {
                const sortable = Boolean(col.sortValue);
                const active = sort?.key === col.key;
                return (
                  <th key={col.key} className={sortable ? "sortable" : undefined}>
                    {sortable ? (
                      <button type="button" onClick={() => toggleSort(col.key)}>
                        {col.label}
                        {active ? (
                          sort!.dir === "asc" ? (
                            <ArrowUp size={12} />
                          ) : (
                            <ArrowDown size={12} />
                          )
                        ) : (
                          <ChevronsUpDown size={12} className="sort-idle" />
                        )}
                      </button>
                    ) : (
                      col.label
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="table-empty">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              visible.map((row, i) => (
                <tr key={rowKey(row, i)}>
                  {columns.map((col) => (
                    <td key={col.key}>{col.render(row)}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {hidden > 0 || expanded ? (
        <button type="button" className="table-more" onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Show less" : `Show ${hidden} more`}
        </button>
      ) : null}
    </div>
  );
}
