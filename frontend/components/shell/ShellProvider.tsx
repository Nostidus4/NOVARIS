"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import {
  getServerTheme,
  getTheme,
  setTheme,
  subscribeTheme,
  type Theme,
} from "@/lib/theme-store";

type ShellContextValue = {
  theme: Theme;
  toggleTheme: () => void;
  sidebarOpen: boolean;
  openSidebar: () => void;
  closeSidebar: () => void;
};

const ShellContext = createContext<ShellContextValue | null>(null);

export function ShellProvider({ children }: { children: ReactNode }) {
  const theme = useSyncExternalStore(subscribeTheme, getTheme, getServerTheme);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleTheme = useCallback(() => {
    setTheme(getTheme() === "dark" ? "light" : "dark");
  }, []);

  const value = useMemo(
    () => ({
      theme,
      toggleTheme,
      sidebarOpen,
      openSidebar: () => setSidebarOpen(true),
      closeSidebar: () => setSidebarOpen(false),
    }),
    [theme, toggleTheme, sidebarOpen],
  );

  return <ShellContext.Provider value={value}>{children}</ShellContext.Provider>;
}

export function useShell() {
  const ctx = useContext(ShellContext);
  if (!ctx) throw new Error("useShell must be used within ShellProvider");
  return ctx;
}
