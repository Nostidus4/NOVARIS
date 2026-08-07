"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { CloudUpload } from "lucide-react";
import { syncWorkflow } from "@/lib/client-api";

export function SyncButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [, startTransition] = useTransition();

  async function onClick() {
    setBusy(true);
    setMsg(null);
    try {
      const res = await syncWorkflow();
      setMsg({
        ok: true,
        text: `Synced ${res.run_key} at ${new Date(res.synced_at).toLocaleTimeString()}`,
      });
      startTransition(() => router.refresh());
    } catch (error) {
      setMsg({ ok: false, text: (error as Error).message.slice(0, 140) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="action-with-status">
      <button type="button" className="btn primary" onClick={onClick} disabled={busy}>
        <CloudUpload size={14} className={busy ? "spin" : undefined} />
        {busy ? "Syncing…" : "Sync to Supabase"}
      </button>
      {msg ? (
        <span className={`action-status ${msg.ok ? "ok" : "bad"}`}>{msg.text}</span>
      ) : null}
    </div>
  );
}
