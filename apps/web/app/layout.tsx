import type { ReactNode } from "react";
import {
  IBM_Plex_Sans,
  Instrument_Serif,
  JetBrains_Mono,
} from "next/font/google";
import "./globals.css";

const ibmPlex = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex",
  display: "swap",
});

const instrument = Instrument_Serif({
  subsets: ["latin"],
  weight: ["400"],
  style: ["normal", "italic"],
  variable: "--font-instrument",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata = {
  title: "AI Infrastructure Fund",
  description: "Local read-only AI infrastructure fund control room",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={`${ibmPlex.variable} ${instrument.variable} ${jetbrains.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
