import Link from "next/link";
import { notFound } from "next/navigation";

import { getStory, type StoryEvidence } from "@/lib/api";

const presentationLabels: Record<string, string> = {
  documented_change: "Documented change",
  documented_fact: "Documented fact",
  source_claim: "Source claim",
  observation: "Observation",
  analysis: "Our read",
};

function titleCase(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatTimestamp(value?: string | null) {
  if (!value) return "Time not recorded";

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

function metadataString(item: StoryEvidence, key: string) {
  const value = item.metadata[key];
  return typeof value === "string" ? value : null;
}

function EvidenceCard({ item }: { item: StoryEvidence }) {
  const label = presentationLabels[item.presentation_type] ?? titleCase(item.presentation_type);
  const event = metadataString(item, "event");
  const session = metadataString(item, "session");

  return (
    <article className={`evidenceItem evidence-${item.presentation_type}`}>
      <div className="evidenceRail" aria-hidden="true">
        <span className="evidenceMarker" />
      </div>
      <div className="evidenceContent">
        <div className="evidenceMetaRow">
          <span className="evidenceType">{label}</span>
          <time dateTime={item.published_at ?? item.captured_at}>
            {formatTimestamp(item.published_at ?? item.captured_at)} UTC
          </time>
        </div>

        {(event || session) && (
          <p className="evidenceContext">
            {[event, session].filter(Boolean).join(" · ")}
          </p>
        )}

        <h3>{item.normalized_claim ?? "Evidence item"}</h3>

        {item.author_or_speaker && (
          <p className="sourceAttribution">Attributed to {item.author_or_speaker}</p>
        )}

        <p className="evidenceSource">
          Source: {item.source_name}
          {item.source_url ? (
            <>
              {" · "}
              <a href={item.source_url} target="_blank" rel="noreferrer">
                Open source ↗
              </a>
            </>
          ) : null}
        </p>

        {item.raw_excerpt_or_reference && (
          <p className="evidenceNote">{item.raw_excerpt_or_reference}</p>
        )}
      </div>
    </article>
  );
}

export default async function StoryPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const story = await getStory(slug);

  if (!story) {
    notFound();
  }

  const isSynthetic = story.evidence.some((item) => item.metadata.is_synthetic === true);
  const timelineTitle = story.evidence.length > 1 ? "How the story changed" : "Evidence record";
  const evidenceLabel = `${story.evidence.length} evidence ${story.evidence.length === 1 ? "item" : "items"}`;

  return (
    <main className="storyPage">
      <section className="shell storyHero">
        <Link className="backLink" href="/stories">
          ← Stories
        </Link>

        {isSynthetic && (
          <div className="demoBanner" role="note">
            Demo data — this page validates the product flow and does not describe a real Formula 1 event.
          </div>
        )}

        <div className="storyStatusRow">
          <p className="eyebrow">STORY · {story.status.toUpperCase()}</p>
          <time dateTime={story.updated_at}>Updated {formatTimestamp(story.updated_at)} UTC</time>
        </div>

        <h1>{story.title}</h1>
        {story.summary && <p className="storySummary">{story.summary}</p>}

        {story.entities.length > 0 && (
          <div className="storyEntityRow" aria-label="Story context">
            {story.entities.map((entity) => (
              <span className={`storyEntityTag storyEntity-${entity.entity_type}`} key={entity.id}>
                <span>{titleCase(entity.entity_type)}</span>
                {entity.display_name}
              </span>
            ))}
          </div>
        )}
      </section>

      <section className="shell storyGrid">
        <div className="storyMain">
          <section className="storyPanel storyCurrentState">
            <p className="sectionLabel">CURRENT STATE</p>
            <h2>Best-supported current understanding</h2>
            <p>{story.summary ?? "No current summary has been published yet."}</p>
          </section>

          {story.what_changed && (
            <section className="storyPanel changePanel">
              <p className="sectionLabel">WHAT CHANGED</p>
              <p>{story.what_changed}</p>
            </section>
          )}

          <section className="timelineSection">
            <div className="sectionHeading">
              <div>
                <p className="sectionLabel">EVIDENCE TIMELINE</p>
                <h2>{timelineTitle}</h2>
              </div>
              <span>{evidenceLabel}</span>
            </div>

            <div className="evidenceTimeline">
              {story.evidence.length > 0 ? (
                story.evidence.map((item) => <EvidenceCard item={item} key={item.id} />)
              ) : (
                <div className="emptyTimeline">No evidence has been attached to this story yet.</div>
              )}
            </div>
          </section>
        </div>

        <aside className="storyAside">
          {story.why_it_matters && (
            <section className="asidePanel">
              <p className="sectionLabel">WHY IT MATTERS</p>
              <p>{story.why_it_matters}</p>
            </section>
          )}

          {story.what_to_watch_next && (
            <section className="asidePanel watchNextPanel">
              <p className="sectionLabel">WHAT TO WATCH NEXT</p>
              <p>{story.what_to_watch_next}</p>
            </section>
          )}
        </aside>
      </section>
    </main>
  );
}
