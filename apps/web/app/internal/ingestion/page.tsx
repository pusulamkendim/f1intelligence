import type { Metadata } from "next";
import Link from "next/link";

import { getIngestionQueue } from "@/lib/api";

import styles from "./review.module.css";

export const metadata: Metadata = {
  title: "Ingestion review",
  robots: { index: false, follow: false },
};

const statuses = ["unmatched", "ambiguous", "attached", "filtered"] as const;

function titleCase(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value?: string | null) {
  if (!value) return "No source timestamp";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

export default async function IngestionReviewPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const params = await searchParams;
  const selected = statuses.includes(params.status as (typeof statuses)[number])
    ? params.status
    : "unmatched";
  const queue = await getIngestionQueue(selected);

  return (
    <main className={styles.page}>
      <section className={`shell ${styles.hero}`}>
        <p className="eyebrow">INTERNAL · SOURCE OPERATIONS</p>
        <h1>Ingestion review</h1>
        <p>
          Inspect deterministic matching results before expanding Story rules. This surface is
          intentionally not linked from the public navigation.
        </p>
      </section>

      <section className={`shell ${styles.content}`}>
        {!queue ? (
          <div className={styles.emptyState}>
            Internal ingestion data is unavailable. Run the API in a non-production environment.
          </div>
        ) : (
          <>
            <div className={styles.metrics}>
              {statuses.map((status) => (
                <Link
                  className={`${styles.metric} ${selected === status ? styles.metricActive : ""}`}
                  href={`/internal/ingestion?status=${status}`}
                  key={status}
                >
                  <span>{titleCase(status)}</span>
                  <strong>{queue.counts[status]}</strong>
                </Link>
              ))}
            </div>

            <div className={styles.queueHeader}>
              <div>
                <p className="sectionLabel">REVIEW QUEUE</p>
                <h2>{titleCase(selected ?? "unmatched")}</h2>
              </div>
              <span>{queue.items.length} shown</span>
            </div>

            <div className={styles.items}>
              {queue.items.length === 0 ? (
                <div className={styles.emptyState}>No ingestion items in this state.</div>
              ) : (
                queue.items.map((item) => (
                  <article className={styles.item} key={item.id}>
                    <div className={styles.itemTopline}>
                      <span className={styles.status}>{titleCase(item.status)}</span>
                      <time dateTime={item.published_at ?? item.ingested_at}>
                        {formatDate(item.published_at ?? item.ingested_at)} UTC
                      </time>
                    </div>
                    <h3>{item.title}</h3>
                    <p className={styles.sourceLine}>
                      {item.source_name} · match score {item.match_score ?? "—"}
                      {item.matched_story_slug ? (
                        <>
                          {" · "}
                          <Link href={`/stories/${item.matched_story_slug}`}>
                            {item.matched_story_title ?? item.matched_story_slug}
                          </Link>
                        </>
                      ) : null}
                    </p>

                    {item.entities.length > 0 && (
                      <div className={styles.entities}>
                        {item.entities.map((entity) => (
                          <span className={styles.entity} key={entity.id}>
                            {titleCase(entity.entity_type)} · {entity.display_name}
                          </span>
                        ))}
                      </div>
                    )}

                    {item.source_url && (
                      <a
                        className={styles.sourceLink}
                        href={item.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open original source ↗
                      </a>
                    )}
                  </article>
                ))
              )}
            </div>
          </>
        )}
      </section>
    </main>
  );
}
