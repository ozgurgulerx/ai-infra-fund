import type { ReactNode } from "react";
import Link from "next/link";

type EmptyStateRowProps = {
  children: ReactNode;
};

export function EmptyStateRow({ children }: EmptyStateRowProps) {
  return (
    <div className="data-empty-state" role="status">
      {children}
    </div>
  );
}

type EmptyStateProps = {
  reason: string;
  ctaLabel?: string;
  ctaHref?: string;
};

export function EmptyState({ reason, ctaLabel, ctaHref }: EmptyStateProps) {
  return (
    <div className="empty-state" role="status" aria-live="polite">
      <p className="empty-state-reason">{reason}</p>
      {ctaLabel && ctaHref ? (
        <Link className="empty-state-cta" href={ctaHref}>
          {ctaLabel} →
        </Link>
      ) : null}
    </div>
  );
}
