import Link from "next/link";

import { getStories } from "@/lib/api";

function titleCase(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(value));
}

export default async function StoriesPage() {
  const stories = await getStories();

  return (
    <main className="storiesIndex">
      <section className="shell storiesHero">
        <p className="eyebrow">STORIES</p>
        <h1>Developments worth following over time.</h1>
        <p>
          Persistent story pages connect official evidence, technical context and editorial analysis as the picture changes.
        </p>
      </section>

      <section className="shell storyList" aria-label="Current stories">
        {stories.length > 0 ? (
          stories.map((story) => (
            <article className="storyListItem" key={story.id}>
              <div className="storyListMeta">
                <span>{titleCase(story.status)}</span>
                <span>{story.evidence_count} evidence</span>
                <span>Updated {formatDate(story.updated_at)}</span>
              </div>
              <h2>
                <Link href={`/stories/${story.slug}`}>{story.title}</Link>
              </h2>
              {story.summary && <p>{story.summary}</p>}
              <Link className="storyListLink" href={`/stories/${story.slug}`}>
                Follow story →
              </Link>
            </article>
          ))
        ) : (
          <div className="storyListEmpty">
            <h2>No stories are available yet.</h2>
            <p>Start the API and ingestion pipeline to populate this page with persistent F1 stories.</p>
          </div>
        )}
      </section>
    </main>
  );
}
