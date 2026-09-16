import Link from "next/link";

import { getRaces } from "@/lib/api";

import styles from "../catalog.module.css";

function formatDate(value?: string | null) {
  if (!value) return "Date pending";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value));
}

export default async function RacesPage() {
  const races = await getRaces();

  return (
    <main className={styles.page}>
      <section className={`shell ${styles.hero}`}>
        <p className="eyebrow">RACES</p>
        <h1>One evolving context layer for every weekend.</h1>
        <p className={styles.heroCopy}>
          Race pages are the canonical home for event context, linked Story objects and the evidence that accumulates through a weekend.
        </p>
      </section>

      <section className={`shell ${styles.grid}`} aria-label="Formula 1 race calendar">
        {races.length > 0 ? (
          races.map((race) => (
            <article className={styles.card} key={race.id}>
              <div className={styles.cardMeta}>
                <span>Round {race.round ?? "—"}</span>
                <span>{race.season}</span>
                <span>{race.status}</span>
              </div>
              <h2>
                <Link href={`/races/${race.slug}`}>{race.official_name}</Link>
              </h2>
              <p>
                {[race.circuit, race.country].filter(Boolean).join(" · ") || "Venue pending"}
              </p>
              <div className={styles.cardFooter}>
                <span>
                  {formatDate(race.weekend_start_date)} – {formatDate(race.weekend_end_date)}
                </span>
                <Link href={`/races/${race.slug}`}>{race.story_count} stories →</Link>
              </div>
            </article>
          ))
        ) : (
          <div className={styles.empty}>
            No race calendar is available yet. Run the ingestion setup to seed the current season.
          </div>
        )}
      </section>
    </main>
  );
}
