import Link from "next/link";
import type { ReactNode } from "react";

export function PageHead({
  eyebrow,
  title,
  sub,
  actions,
}: {
  eyebrow: string;
  title: string;
  sub: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-head">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1 className="page-title">{title}</h1>
        <p className="page-sub">{sub}</p>
      </div>
      {actions ? <div className="head-actions">{actions}</div> : null}
    </div>
  );
}

/** Navigation button. Mọi nút trong console phải có hành vi thật — nên đây luôn là một link. */
export function Btn({
  href,
  children,
  primary = false,
  icon,
  title,
}: {
  href: string;
  children: ReactNode;
  primary?: boolean;
  icon?: ReactNode;
  title?: string;
}) {
  return (
    <Link href={href} className={`btn${primary ? " primary" : ""}`} title={title}>
      {icon}
      {children}
    </Link>
  );
}
