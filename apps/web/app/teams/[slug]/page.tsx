import Link from "next/link";
import { notFound } from "next/navigation";

import { getTeam, type TeamMember } from "@/lib/api";

import styles from "../../catalog.module.css";

const roleLabels: Record<string, string> = {
  driver: "Driver",
  team_principal: "Team Principal",
  racing_director: "Racing Director",
  managing_director: "Managing Director",
  executive_advisor: "Executive Advisor",
};

function roleLabel(role: string) {
  return roleLabels[role] ?? role.replaceAll("_", " ");
}

function Members({ members }: { members: TeamMember[] }) {
  return (
    <ul className={styles.memberList}>
      {members.map((member) => (
        <li className={styles.member} key={`${member.id}-${member.role}`}>
          <p className={styles.memberName}>{member.display_name}</p>
          <p className={styles.memberRole}>{roleLabel(member.role)}</p>
        </li>
      ))}
    </ul>
  );
}

export default async function TeamPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const team = await getTeam(slug);
  if (!team) notFound();

  const drivers = team.members.filter((member) => member.role === "driver");
  const leadership = team.members.filter((member) => member.role !== "driver");

  return (
    <main className={styles.page}>
      <section className={`shell ${styles.hero}`}>
        <Link className={styles.backLink} href="/teams">
          ← Teams
        </Link>
        <p className="eyebrow">TEAM · {team.active_season ?? "CURRENT"}</p>
        <h1>{team.name}</h1>
        <p className={styles.heroCopy}>
          Persistent context for the team&apos;s current people and evidence-linked developments.
        </p>
      </section>

      <section className={`shell ${styles.detailGrid}`}>
        <div>
          <section className={styles.panel}>
            <p className="sectionLabel">DRIVERS</p>
            <h2>Current line-up</h2>
            {drivers.length > 0 ? <Members members={drivers} /> : <p>No current drivers recorded.</p>}
          </section>

          <section className={styles.panel}>
            <p className="sectionLabel">ACTIVE STORIES</p>
            <h2>Developments connected to {team.name}</h2>
            {team.stories.length > 0 ? (
              <ul className={styles.storyList}>
                {team.stories.map((story) => (
                  <li className={styles.story} key={story.id}>
                    <p className={styles.storyTitle}>
                      <Link href={`/stories/${story.slug}`}>{story.title}</Link>
                    </p>
                    <p className={styles.storyMeta}>
                      {story.status} · {story.evidence_count} evidence items
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No Story objects are linked to this team yet.</p>
            )}
          </section>
        </div>

        <aside>
          <section className={styles.panel}>
            <p className="sectionLabel">TEAM LEADERSHIP</p>
            <h2>Current roles</h2>
            {leadership.length > 0 ? (
              <Members members={leadership} />
            ) : (
              <p>No leadership roles recorded.</p>
            )}
          </section>
        </aside>
      </section>
    </main>
  );
}
