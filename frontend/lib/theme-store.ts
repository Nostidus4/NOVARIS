export type Theme = "light" | "dark";

export const THEME_KEY = "novaris-theme-v2";

/**
 * Theme sống ngoài React (localStorage + `document.body.dataset`) nên đọc qua
 * `useSyncExternalStore`; server luôn trả "light" để hydration không lệch.
 */
let current: Theme =
  typeof document !== "undefined" && document.body.dataset.theme === "dark" ? "dark" : "light";

const listeners = new Set<() => void>();

export function subscribeTheme(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getTheme(): Theme {
  return current;
}

export function getServerTheme(): Theme {
  return "light";
}

export function setTheme(next: Theme): void {
  current = next;
  document.body.dataset.theme = next;
  window.localStorage.setItem(THEME_KEY, next);
  listeners.forEach((listener) => listener());
}

/** Chạy trước khi React hydrate để tránh nháy sáng/tối. */
export const THEME_BOOT_SCRIPT = `try{var t=localStorage.getItem(${JSON.stringify(
  THEME_KEY,
)});document.body.dataset.theme=t==="dark"?"dark":"light"}catch(e){}`;
