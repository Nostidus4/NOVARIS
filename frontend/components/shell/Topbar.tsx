"use client";

import { usePathname } from "next/navigation";
import { CalendarDays, Menu, Moon, Sun } from "lucide-react";
import { CRUMB } from "@/lib/nav";
import type { ConsoleShell } from "@/lib/types";
import { RunMenu } from "./RunMenu";
import { useShell } from "./ShellProvider";

type Props = {
  shell: ConsoleShell | null;
  dateLabel: string;
};

export function Topbar({ shell, dateLabel }: Props) {
  const pathname = usePathname();
  const { openSidebar, toggleTheme, theme } = useShell();
  const crumb = CRUMB[pathname] ?? "Overview";

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          className="control menu-btn"
          onClick={openSidebar}
          aria-label="Open navigation"
        >
          <Menu size={16} />
        </button>
        <div className="breadcrumb">
          Q‑SHIELD <span className="crumb-sep">/</span> <strong>{crumb}</strong>
        </div>
      </div>
      <div className="topbar-right">
        <span className="control date-control" aria-label="Evaluation date">
          <CalendarDays size={14} />
          {dateLabel}
        </span>
        <RunMenu shell={shell} />
        <button
          className="control icon-only"
          type="button"
          onClick={toggleTheme}
          aria-label="Toggle theme"
          title={theme === "dark" ? "Switch to light" : "Switch to dark"}
        >
          {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </header>
  );
}
