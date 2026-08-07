"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { RotateCw } from "lucide-react";

export function RefreshButton({ label = "Refresh" }: { label?: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <button
      type="button"
      className="btn"
      disabled={pending}
      onClick={() => startTransition(() => router.refresh())}
    >
      <RotateCw size={14} className={pending ? "spin" : undefined} />
      {pending ? "Refreshing…" : label}
    </button>
  );
}
