"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

type AppShellProps = {
  eyebrow: string;
  title: string;
  children: ReactNode;
  aside?: ReactNode;
};

const navigationSections = [
  {
    title: "Workspace",
    items: [
      { href: "/", label: "Control Room" },
      { href: "/portfolio", label: "Portfolio Workbench" },
      { href: "/trade-intents", label: "Manual Trade Intents" },
      { href: "/trade-journal", label: "Trade Journal" }
    ]
  },
  {
    title: "Research",
    items: [
      { href: "/watchlist", label: "Watchlist" },
      { href: "/ticker/NVDA", label: "Ticker Workbench" },
      { href: "/evidence", label: "Evidence Library" },
      { href: "/signals", label: "Signals" }
    ]
  },
  {
    title: "Governance",
    items: [
      { href: "/runs", label: "Runs" },
      { href: "/evaluation", label: "Evaluation" },
      { href: "/ops", label: "Ops Room" },
      { href: "/incidents", label: "Incidents" }
    ]
  }
];

export function AppShell({ eyebrow, title, children, aside }: AppShellProps) {
  const pathname = usePathname();

  return (
    <main className="app-frame">
      <aside className="side-nav" aria-label="Control room navigation">
        <div className="brand-mark">
          <span className="brand-lockup">AIIF</span>
          <small>AI Infrastructure Fund</small>
        </div>
        <nav className="nav-list">
          {navigationSections.map((section) => (
            <div className="nav-section" key={section.title}>
              <span className="nav-section-title">{section.title}</span>
              {section.items.map((item) => {
                const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href.replace("/NVDA", ""));

                return (
                  <Link
                    aria-current={isActive ? "page" : undefined}
                    className={isActive ? "nav-link nav-link-active" : "nav-link"}
                    href={item.href}
                    key={item.href}
                  >
                    <span className="nav-link-indicator" aria-hidden="true" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
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
          <div className="topbar-rail">
            <span className="topbar-chip">Read-only</span>
            <span className="topbar-chip">Evidence traced</span>
            <span className="topbar-chip">Local journal</span>
            <div className="workspace-signal">
              {aside ?? <div className="advisory-badge">Advisory-only</div>}
            </div>
          </div>
        </header>
        {children}
      </div>
    </main>
  );
}
