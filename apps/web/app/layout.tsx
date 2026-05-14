import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "AI Infrastructure Fund",
  description: "Local read-only AI infrastructure fund control room"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
