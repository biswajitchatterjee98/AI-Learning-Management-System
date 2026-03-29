import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI-LMS",
  description: "Adaptive AI LMS Generator (Phase 4 roadmap)"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

