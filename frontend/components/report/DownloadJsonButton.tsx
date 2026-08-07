"use client";

import { useState } from "react";
import { Check, FileDown } from "lucide-react";

type Props = {
  payload: unknown;
  filename: string;
  label?: string;
  primary?: boolean;
};

export function DownloadJsonButton({ payload, filename, label = "Download JSON", primary }: Props) {
  const [done, setDone] = useState(false);

  function download() {
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    setDone(true);
    setTimeout(() => setDone(false), 2000);
  }

  return (
    <button type="button" className={`btn${primary ? " primary" : ""}`} onClick={download}>
      {done ? <Check size={14} /> : <FileDown size={14} />}
      {done ? "Saved" : label}
    </button>
  );
}
