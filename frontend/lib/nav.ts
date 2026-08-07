import type { NavItem } from "./types";

export const NAV_ITEMS: NavItem[] = [
  {
    href: "/overview",
    icon: "gauge",
    title: "Overview",
    desc: "Executive snapshot",
    section: "workspace",
  },
  {
    href: "/data",
    icon: "database",
    title: "Data Gate",
    desc: "Input quality & coverage",
    section: "workspace",
  },
  {
    href: "/regime",
    icon: "activity",
    title: "Regime",
    desc: "Market state inference",
    section: "workspace",
  },
  {
    href: "/scenarios",
    icon: "waves",
    title: "Scenarios",
    desc: "Stress simulation",
    section: "workspace",
  },
  {
    href: "/risk",
    icon: "shield",
    title: "Risk",
    desc: "Ranking & tail exposure",
    section: "decision",
  },
  {
    href: "/quantum",
    icon: "atom",
    title: "Quantum",
    desc: "QUBO / QAOA optimizer",
    section: "decision",
  },
  {
    href: "/report",
    icon: "file",
    title: "Report",
    desc: "Decision package",
    section: "decision",
  },
];

export const CRUMB: Record<string, string> = {
  "/overview": "Overview",
  "/data": "Data Gate",
  "/regime": "Regime",
  "/scenarios": "Scenarios",
  "/risk": "Risk",
  "/quantum": "Quantum",
  "/report": "Report",
};
