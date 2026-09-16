import Link from "next/link";

import { getApiHealth, getStories } from "@/lib/api";

const pillars = [
  {
    eyebrow: "STORIES",
    title: "Follow developments over time",
    body: "One persistent page connects evidence, technical changes, quotes and analysis instead of fragmenting the story across headlines.",
  },
  {
    eyebrow: "RACE HUBS",
    title: "One page for the whole weekend",
    body: "Preview, sessions, technical updates and post-race synthesis evolve on one canonical race URL.",
  },
  {
    eyebrow: "EVIDENCE",
    title: "Know what supports the analysis",
    body: "Documented facts, source claims, observations and editorial interpretation remain visibly distinct.",
  },
];

export default async function Home() {
  const [health, stories] = await Promise.all([getApiHealth(), getStories()]);
  const latestStory = stories[0];

  return (
    <main>
      <section className="hero shell">
        <p className="eyebrow">F1 INTELLIGENCE · MVP</p>
        <h1>Follow the story, not just the news.</h1>
        <p className="heroCopy">
          Race-weekend intelligence, technical development and persistent evidence timelines for Formula 1.
        </p>
        <div className="systemState" aria-label="Development system status">
          <span className={health ? "statusDot statusOk" : "statusDot"} />
          API {health ? "connected" : "not connected"}
          {health?.database === "ok" ? " · database connected" : ""}
        </div>
      </section>

      <section className="shell grid" aria-label="Product pillars">
        {pillars.map((pillar) => (
          <article className="card" key={pillar.eyebrow}>
            <p className="eyebrow">{pillar.eyebrow}</p>
            <h2>{pillar.title}</h2>
            <p>{pillar.body}</p>
          </article>
        ))}
      </section>

      <section className="shell nextStep">
        <p className="eyebrow">CURRENT STORY</p>
        {latestStory ? (
          <>
            <h2>{latestStory.title}</h2>
            <p>{latestStory.summary ?? "Follow the evidence and updates attached to this story."}</p>
            <Link className="storyCta" href={`/stories/${latestStory.slug}`}>
              Follow current story →
            </Link>
          </>
        ) : (
          <>
            <h2>Story Page → API data → evidence timeline.</h2>
            <p>
              Start the API and ingestion pipeline to populate the site with persistent F1 stories backed by source evidence.
            </p>
            <Link className="storyCta" href="/stories">
              Browse stories →
            </Link>
          </>
        )}
      </section>
    </main>
  );
}
