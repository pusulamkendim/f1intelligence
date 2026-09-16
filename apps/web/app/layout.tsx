import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "F1 Intelligence",
    template: "%s | F1 Intelligence",
  },
  description: "Follow the story, not just the news.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="siteHeader">
          <div className="shell headerInner">
            <Link className="brand" href="/" aria-label="F1 Intelligence home">
              F1 Intelligence
            </Link>
            <nav className="nav" aria-label="Primary navigation">
              <Link href="/races">Races</Link>
              <Link href="/teams">Teams</Link>
              <Link href="/stories">Stories</Link>
              <Link href="/technical">Technical</Link>
            </nav>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
