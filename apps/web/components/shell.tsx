"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/review", label: "Review" },
  { href: "/graph", label: "Graph" }
] as const;

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="shell-root">
      <header className="hero">
        <p className="eyebrow">LetterOps Phase 5</p>
        <h1>Operational Reading Console</h1>
        <p className="lede">
          Structured retrieval and human review with evidence-first navigation.
        </p>
      </header>
      <nav className="nav-row" aria-label="Primary">
        {links.map((link) => {
          const active = pathname === link.href;
          return (
            <Link key={link.href} className={active ? "nav-chip active" : "nav-chip"} href={link.href}>
              {link.label}
            </Link>
          );
        })}
      </nav>
      <main>{children}</main>
    </div>
  );
}
