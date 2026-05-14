import type { ReactNode } from "react";

type SectionPanelProps = {
  eyebrow: string;
  title: string;
  children: ReactNode;
  aside?: ReactNode;
};

export function SectionPanel({ eyebrow, title, children, aside }: SectionPanelProps) {
  return (
    <section className="section-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        {aside ? <div className="section-aside">{aside}</div> : null}
      </div>
      {children}
    </section>
  );
}
