"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, Menu, X } from "lucide-react";
import { assetPath } from "@/lib/paths";

const LINKS = [
  { href: "#pipeline", label: "Quy trình" },
  { href: "#principles", label: "Minh bạch" },
  { href: "#scope", label: "Giới hạn" },
  { href: "#contact", label: "Liên hệ" },
];

export function LandingNav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="lp-nav">
      <div className="lp-nav-row">
        <Link href="/landing" className="lp-brand" onClick={() => setOpen(false)}>
          <Image
            src={assetPath("/novaris-mark.png")}
            alt="NOVARIS"
            width={30}
            height={30}
            priority
          />
          <span>
            NOVARIS <em>Q-SHIELD</em>
          </span>
        </Link>

        <nav className="lp-nav-links">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href}>
              {l.label}
            </a>
          ))}
        </nav>

        <div className="lp-nav-actions">
          <Link href="/overview" className="lp-btn lp-btn-primary">
            Vào Console
            <ArrowRight size={14} />
          </Link>
          <button
            type="button"
            className="lp-nav-toggle"
            aria-label={open ? "Đóng menu" : "Mở menu"}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {open ? (
        <nav className="lp-nav-mobile">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} onClick={() => setOpen(false)}>
              {l.label}
            </a>
          ))}
          <Link href="/overview" className="lp-btn lp-btn-primary" onClick={() => setOpen(false)}>
            Vào Console
            <ArrowRight size={14} />
          </Link>
        </nav>
      ) : null}
    </header>
  );
}
