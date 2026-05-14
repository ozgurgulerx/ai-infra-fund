"use client";

import Link from "next/link";
import type { ReactNode } from "react";

type AppShellProps = {
  eyebrow: string;
  title: string;
  children: ReactNode;
  aside?: ReactNode;
};

const navigation = [
  { href: "/", label: "Control Room" },
  { href: "/portfolio", label: "Portfolio Workbench" },
  { href: "/trade-intents", label: "Manual Trade Intents" },
  { href: "/trade-journal", label: "Trade Journal" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/ticker/NVDA", label: "Ticker Workbench" },
  { href: "/evidence", label: "Evidence Library" },
  { href: "/signals", label: "Signals" },
  { href: "/runs", label: "Runs" },
  { href: "/evaluation", label: "Evaluation" },
  { href: "/ops", label: "Ops Room" },
  { href: "/incidents", label: "Incidents" }
];

export function AppShell({ eyebrow, title, children, aside }: AppShellProps) {
  return (
    <main className="app-frame">
      <aside className="side-nav" aria-label="Control room navigation">
        <div className="brand-mark">
          <span>AIIF</span>
          <small>Advisory-only</small>
        </div>
        <nav className="nav-list">
          {navigation.map((item) => (
            <Link className="nav-link" href={item.href} key={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="nav-disclaimer">
          <strong>Local journal only</strong>
          <span>No broker connection. No transaction submission surface.</span>
        </div>
      </aside>

      <div className="content-shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h1>{title}</h1>
          </div>
          {aside ?? <div className="advisory-badge">Advisory-only</div>}
        </header>
        {children}
      </div>
    </main>
  );
}
