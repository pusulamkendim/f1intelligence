import Link from "next/link";

import { getTeams } from "@/lib/api";

import styles from "../catalog.module.css";

export default async function TeamsPage() {
  const teams = await getTeams();

  return (
    <main className={styles.page}>
      <section className={`shell ${styles.hero}`}>
        <p className="eyebrow">TEAMS</p>
        <h1>The grid as a living intelligence layer.</h1>
        <p className={styles.heroCopy}>
          Team pages connect the current roster and leadership to the persistent stories that matter across the season.
        </p>
      </section>

      <section className={`shell ${styles.grid}`} aria-label="Formula 1 teams">
        {teams.length > 0 ? (
          teams.map((team) => (
            <article className={styles.card} key={team.id}>
              <div className={styles.cardMeta}>
                <span>{team.active_season ?? "Current"} season</span>
                <span>{team.driver_count} drivers</span>
              </div>
              <h2>
                <Link href={`/teams/${team.slug}`}>{team.name}</Link>
              </h2>
              <p>Follow the team&apos;s people, evidence-linked developments and active Story objects.</p>
              <div className={styles.cardFooter}>
                <span>{team.story_count} linked stories</span>
                <Link href={`/teams/${team.slug}`}>Open team →</Link>
              </div>
            </article>
          ))
        ) : (
          <div className={styles.empty}>
            No team registry is available yet. Run the ingestion setup to seed the current grid.
          </div>
        )}
      </section>
    </main>
  );
}
