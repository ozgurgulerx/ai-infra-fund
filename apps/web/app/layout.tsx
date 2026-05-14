import type { ReactNode } from "react";

export const metadata = {
  title: "AI Infrastructure Fund",
  description: "Phase 0 scaffold"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
