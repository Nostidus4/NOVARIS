"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ChevronDown, FileText } from "lucide-react";
import type { ConsoleShell } from "@/lib/types";

export function RunMenu({ shell }: { shell: ConsoleShell | null }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const rows: [string, string][] = [
    ["Profile", shell?.profile_id ?? "—"],
    ["Status", shell?.profile_status ?? "—"],
    ["Config", shell?.config_version ?? "—"],
    ["Candidates", String(shell?.candidate_count ?? "—")],
    ["Scenarios", shell?.scenario_count?.toLocaleString() ?? "—"],
    ["Backend", shell?.online ? "online" : "offline"],
  ];

  return (
    <div className="run-menu" ref={ref}>
      <button
        type="button"
        className={`control run-select${open ? " open" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        {shell?.profile_id || "offline"}
        <ChevronDown size={14} />
      </button>
      {open ? (
        <div className="run-popover" role="dialog" aria-label="Active run">
          <div className="run-popover-head">Active run</div>
          {rows.map(([k, v]) => (
            <div className="run-popover-row" key={k}>
              <span>{k}</span>
              <strong>{v}</strong>
            </div>
          ))}
          <Link href="/report" className="run-popover-link" onClick={() => setOpen(false)}>
            <FileText size={13} />
            Xem audit trail
          </Link>
        </div>
      ) : null}
    </div>
  );
}
