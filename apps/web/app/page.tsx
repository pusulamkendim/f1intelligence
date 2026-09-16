import { getApiHealth } from "@/lib/api";

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
  const health = await getApiHealth();

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
        <p className="eyebrow">NEXT VERTICAL SLICE</p>
        <h2>Story Page → real API data → evidence timeline.</h2>
        <p>
          The repository is intentionally starting with the canonical Story model before expanding into a generic news feed.
        </p>
      </section>
    </main>
  );
}
