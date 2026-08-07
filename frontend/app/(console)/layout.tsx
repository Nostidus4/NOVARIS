import { loadConsoleShell } from "@/lib/api";
import { ShellProvider } from "@/components/shell/ShellProvider";
import { Sidebar } from "@/components/shell/Sidebar";
import { Topbar } from "@/components/shell/Topbar";

export default async function ConsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const shell = await loadConsoleShell();
  const dateLabel = new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date());

  return (
    <ShellProvider>
      <div className="app">
        <Sidebar />
        <div className="workspace">
          <Topbar shell={shell} dateLabel={dateLabel} />
          <main className="main">
            {!shell?.online ? (
              <div className="offline-banner">
                Backend chưa sẵn sàng. Chạy API tại cổng 8000 hoặc đặt QSHIELD_API_URL.
              </div>
            ) : null}
            {children}
          </main>
        </div>
      </div>
    </ShellProvider>
  );
}
