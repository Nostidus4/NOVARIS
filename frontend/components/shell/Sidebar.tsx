"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Atom,
  Database,
  FileText,
  Gauge,
  ShieldHalf,
  Waves,
  type LucideIcon,
} from "lucide-react";
import { NAV_ITEMS } from "@/lib/nav";
import { assetPath } from "@/lib/paths";
import type { NavIconName } from "@/lib/types";
import { useShell } from "./ShellProvider";

const ICONS: Record<NavIconName, LucideIcon> = {
  gauge: Gauge,
  database: Database,
  activity: Activity,
  waves: Waves,
  shield: ShieldHalf,
  atom: Atom,
  file: FileText,
};

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, closeSidebar } = useShell();

  return (
    <>
      <div
        className={`mobile-overlay${sidebarOpen ? " show" : ""}`}
        onClick={closeSidebar}
        aria-hidden={!sidebarOpen}
      />
      <aside className={`sidebar${sidebarOpen ? " open" : ""}`}>
        <Link href="/overview" className="brand" onClick={closeSidebar}>
          <Image
            className="brand-mark"
            src={assetPath("/novaris-mark.png")}
            alt="NOVARIS"
            width={44}
            height={44}
            priority
          />
          <div>
            <div className="brand-name">NOVARIS</div>
            <div className="brand-sub">Q‑SHIELD CONSOLE</div>
          </div>
        </Link>

        <nav className="nav-scroll">
          <NavSection
            label="Workspace"
            items={NAV_ITEMS.filter((i) => i.section === "workspace")}
            pathname={pathname}
            onNavigate={closeSidebar}
          />
          <NavSection
            label="Decision Engine"
            items={NAV_ITEMS.filter((i) => i.section === "decision")}
            pathname={pathname}
            onNavigate={closeSidebar}
          />
        </nav>
      </aside>
    </>
  );
}

function NavSection({
  label,
  items,
  pathname,
  onNavigate,
}: {
  label: string;
  items: typeof NAV_ITEMS;
  pathname: string;
  onNavigate: () => void;
}) {
  return (
    <div className="nav-section">
      <div className="nav-label">{label}</div>
      <div className="nav-list">
        {items.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = ICONS[item.icon];
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-item${active ? " active" : ""}`}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
            >
              <span className="nav-icon">
                <Icon size={15} strokeWidth={2} />
              </span>
              <span className="nav-copy">
                <span className="nav-title">{item.title}</span>
                <span className="nav-desc">{item.desc}</span>
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
