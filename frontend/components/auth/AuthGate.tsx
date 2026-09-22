"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { LoaderCircle, ShieldCheck } from "lucide-react";
import { clearStoredSession, getStoredSession, verifySession } from "@/lib/auth";

export function AuthGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    const session = getStoredSession();
    if (!session) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }

    verifySession(session)
      .then(() => {
        if (active) setReady(true);
      })
      .catch(() => {
        clearStoredSession();
        if (active) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      });

    return () => {
      active = false;
    };
  }, [pathname, router]);

  if (!ready) {
    return (
      <div className="auth-check" role="status" aria-live="polite">
        <span className="auth-check-mark">
          <ShieldCheck size={28} />
        </span>
        <LoaderCircle className="auth-spin" size={20} />
        <span>Đang xác thực phiên truy cập…</span>
      </div>
    );
  }

  return children;
}
