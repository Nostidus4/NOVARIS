"use client";

import { useMemo, useState } from "react";
import { Check, Copy, Search } from "lucide-react";

const LEVELS = ["ERROR", "WARN", "INFO"] as const;

export function LogPanel({ lines }: { lines: string[] }) {
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return lines.filter((line) => {
      if (level && !line.toUpperCase().includes(level)) return false;
      if (q && !line.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [lines, query, level]);

  async function copy() {
    await navigator.clipboard.writeText(shown.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div>
      <div className="datatable-bar">
        <label className="search-field">
          <Search size={14} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Tìm trong log…"
            spellCheck={false}
          />
        </label>
        <div className="chip-row">
          {LEVELS.map((lv) => (
            <button
              key={lv}
              type="button"
              className={`chip ${level === lv ? "active" : ""}`}
              onClick={() => setLevel(level === lv ? null : lv)}
            >
              {lv} ({lines.filter((l) => l.toUpperCase().includes(lv)).length})
            </button>
          ))}
          <button type="button" className="chip" onClick={copy} disabled={!shown.length}>
            {copied ? <Check size={12} /> : <Copy size={12} />}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
      <pre className="log-pre">
        {shown.length ? shown.join("\n") : "Không có dòng log khớp bộ lọc."}
      </pre>
    </div>
  );
}
