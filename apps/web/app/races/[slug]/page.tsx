import Link from "next/link";
import { notFound } from "next/navigation";

import { getRace } from "@/lib/api";

import styles from "../../catalog.module.css";

function formatDate(value?: string | null) {
  if (!value) return "Pending";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(value));
}

function titleCase(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default async function RacePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const race = await getRace(slug);
  if (!race) notFound();

  const recentDocuments = race.documents.slice(0, 16);

  return (
    <main className={styles.page}>
      <section className={`shell ${styles.hero}`}>
        <Link className={styles.backLink} href="/races">
          ← Races
        </Link>
        <span className={styles.status}>{titleCase(race.status)}</span>
        <p className="eyebrow">
          {race.season} · ROUND {race.round ?? "—"}
        </p>
        <h1>{race.official_name}</h1>
        <p className={styles.heroCopy}>
          {[race.circuit, race.country].filter(Boolean).join(" · ")}
        </p>
      </section>

      <section className={`shell ${styles.detailGrid}`}>
        <div>
          {race.synthesis && (
            <section className={styles.panel}>
              <p className="sectionLabel">WEEKEND SYNTHESIS</p>
              <h2>Current read</h2>
              <p>{race.synthesis}</p>
            </section>
          )}

          <section className={styles.panel}>
            <p className="sectionLabel">RACE STORIES</p>
            <h2>Developments connected to this weekend</h2>
            {race.stories.length > 0 ? (
              <ul className={styles.storyList}>
                {race.stories.map((story) => (
                  <li className={styles.story} key={story.id}>
                    <p className={styles.storyTitle}>
                      <Link href={`/stories/${story.slug}`}>{story.title}</Link>
                    </p>
                    <p className={styles.storyMeta}>
                      {titleCase(story.status)} · {story.evidence_count} evidence items
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No Story objects are linked to this race yet.</p>
            )}
          </section>

          <section className={styles.panel}>
            <p className="sectionLabel">OFFICIAL DOCUMENTS</p>
            <h2>Latest FIA event documents</h2>
            {recentDocuments.length > 0 ? (
              <ul className={styles.storyList}>
                {recentDocuments.map((document) => (
                  <li className={styles.story} key={document.id}>
                    <p className={styles.storyTitle}>
                      <a href={document.document_url} target="_blank" rel="noreferrer">
                        {document.document_number ? `Doc ${document.document_number} · ` : ""}
                        {document.title} ↗
                      </a>
                    </p>
                    <p className={styles.storyMeta}>
                      {titleCase(document.document_type)}
                      {document.published_at ? ` · ${formatDate(document.published_at)}` : ""}
                      {document.recalled ? " · Recalled" : ""}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No FIA event documents have been ingested for this race yet.</p>
            )}
          </section>
        </div>

        <aside>
          <section className={styles.panel}>
            <p className="sectionLabel">WEEKEND</p>
            <h2>Event facts</h2>
            <dl className={styles.factList}>
              <div className={styles.fact}>
                <dt className={styles.factLabel}>Round</dt>
                <dd className={styles.factValue}>{race.round ?? "—"}</dd>
              </div>
              <div className={styles.fact}>
                <dt className={styles.factLabel}>Start</dt>
                <dd className={styles.factValue}>{formatDate(race.weekend_start_date)}</dd>
              </div>
              <div className={styles.fact}>
                <dt className={styles.factLabel}>End</dt>
                <dd className={styles.factValue}>{formatDate(race.weekend_end_date)}</dd>
              </div>
              <div className={styles.fact}>
                <dt className={styles.factLabel}>Circuit</dt>
                <dd className={styles.factValue}>{race.circuit ?? "Pending"}</dd>
              </div>
              <div className={styles.fact}>
                <dt className={styles.factLabel}>Country</dt>
                <dd className={styles.factValue}>{race.country ?? "Pending"}</dd>
              </div>
            </dl>
          </section>
        </aside>
      </section>
    </main>
  );
}
