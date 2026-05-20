"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { AdvisoryStamp } from "./transparency";
import { PageHeader, StatusChip } from "./workstation";

const SESSION_DATE_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

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
      { href: "/", label: "Daily Trading Cockpit" },
      { href: "/radar", label: "Market / Sentiment Radar" },
      { href: "/portfolio", label: "Portfolio Workbench" },
      { href: "/trade-plans", label: "Trade Plan Workbench" },
      { href: "/trade-intents", label: "Manual Plan Review Queue" },
      { href: "/trade-journal", label: "Trade Journal" },
    ],
  },
  {
    title: "Research",
    items: [
      { href: "/segments", label: "AI Infrastructure Segment Map" },
      { href: "/themes", label: "Value-Chain Atlas" },
      { href: "/watchlist", label: "Watchlist" },
      { href: "/ticker/NVDA", label: "Ticker Workbench" },
      { href: "/evidence", label: "Evidence Library" },
      { href: "/signals", label: "Signals" },
    ],
  },
  {
    title: "Governance",
    items: [
      { href: "/runs", label: "Runs" },
      { href: "/evaluation", label: "Evaluation" },
      { href: "/ops", label: "Ops Room" },
      { href: "/incidents", label: "Incidents" },
    ],
  },
];

export function AppShell({ eyebrow, title, children, aside }: AppShellProps) {
  const pathname = usePathname();
  const sessionDate = SESSION_DATE_FORMATTER.format(new Date()).toUpperCase();

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
                const isActive =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href.replace("/NVDA", ""));

                return (
                  <Link
                    aria-current={isActive ? "page" : undefined}
                    className={
                      isActive ? "nav-link nav-link-active" : "nav-link"
                    }
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
          <strong>Manual journal only</strong>
          <span>
            External account connections disabled. Manual journal only.
          </span>
        </div>
      </aside>

      <div className="content-shell">
        <PageHeader
          eyebrow={eyebrow}
          title={title}
          subtitle="Evidence-backed advisory workstation. Backend read models stay authoritative."
        >
          <div className="topbar-rail topbar-chip-group">
            <span className="readonly-label">{sessionDate} · LOCAL</span>
            <StatusChip label="Read-only" tone="neutral" />
            <StatusChip label="Evidence traced" tone="fresh" />
            <StatusChip label="Journal local" tone="review" />
            <div className="workspace-signal">{aside ?? <AdvisoryStamp />}</div>
          </div>
        </PageHeader>
        {children}
      </div>
    </main>
  );
}
