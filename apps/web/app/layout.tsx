import type { Metadata } from "next";

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
            <a className="brand" href="/" aria-label="F1 Intelligence home">
              F1 Intelligence
            </a>
            <nav className="nav" aria-label="Primary navigation">
              <a href="/races">Races</a>
              <a href="/teams">Teams</a>
              <a href="/stories">Stories</a>
              <a href="/technical">Technical</a>
            </nav>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
