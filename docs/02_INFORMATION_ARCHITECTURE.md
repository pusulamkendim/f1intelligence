# Information Architecture and MVP Screens

## Core navigation

Initial top-level navigation:

- Home
- Races
- Teams
- Stories
- Technical
- Regulations
- Newsletter

Drivers can initially be represented as entity pages reachable from stories, races and teams. A dedicated top-level Drivers section can be added when enough content exists.

## URL model

Suggested route structure:

```text
/
/races/
/races/2026/
/races/2026/azerbaijan-grand-prix/
/teams/
/teams/red-bull/
/teams/red-bull/2026-upgrades/
/drivers/max-verstappen/
/stories/
/stories/red-bull-rear-stability/
/technical/
/technical/how-f1-floors-generate-downforce/
/regulations/
/regulations/2026-f1-regulations-explained/
/articles/{slug}/
/newsletter/
```

Canonical long-running subjects should have stable URLs. Articles can be time-bound outputs associated with those subjects.

## MVP page types

### 1. Home

Purpose: show what matters now and provide entry points into persistent context.

Primary modules:

1. **Lead story** — one high-signal developing story.
2. **Current / next race weekend** — shortcut to race hub.
3. **What changed today** — concise intelligence cards, not a generic news firehose.
4. **Developing stories** — persistent stories with recent updates.
5. **Team development** — latest upgrade or performance-trend entries.
6. **Technical explainer** — evergreen discovery module.
7. **Newsletter CTA**.

The homepage should answer: “What matters in F1 right now, and why?”

### 2. Race Hub

Example:

`/races/2026/azerbaijan-grand-prix/`

Purpose: become the canonical destination for an event across the entire weekend.

Sections:

- event header and status,
- pre-weekend context,
- key storylines,
- session index,
- practice analysis,
- qualifying analysis,
- race analysis,
- technical updates introduced at the event,
- strategy notes,
- important quotes,
- “What we learned” synthesis,
- related season-long stories.

The page evolves rather than being replaced after every session.

### 3. Story Page

Example:

`/stories/red-bull-rear-stability/`

Purpose: follow a developing issue across time.

Sections:

- current state / latest conclusion,
- why it matters,
- evidence timeline,
- related quotes,
- technical changes,
- race-by-race progression,
- competing interpretations where relevant,
- latest related articles,
- what to watch next.

A Story Page is a view of a canonical Story Object, not a manually duplicated article archive.

### 4. Team Page

Example:

`/teams/red-bull/`

Sections:

- current team context,
- latest analysis,
- development trend,
- active stories,
- recent race performance summaries,
- drivers,
- links to upgrade tracker and historical season pages.

### 5. Upgrade Tracker

Example:

`/teams/red-bull/2026-upgrades/`

Purpose: create a durable, continuously updated reference page.

Each entry should capture:

- event,
- date,
- component,
- change summary,
- intended effect if documented,
- source/evidence,
- whether permanent, experimental or circuit-specific,
- observed follow-up where known.

Preferred UI: chronological timeline with filters by component and event.

### 6. Technical Explainer

Example:

`/technical/how-f1-floors-generate-downforce/`

Purpose: durable educational/search content that can be linked from current stories.

Structure:

- concise answer,
- concept explanation,
- diagrams or original illustrations,
- current-era relevance,
- examples from recent stories,
- glossary links,
- related explainers.

### 7. Regulation Explainer

Example:

`/regulations/2026-f1-regulations-explained/`

Structure:

- summary,
- exact change,
- effective date,
- practical effect,
- source document references,
- team/driver implications only when supported,
- revision history when the regulation changes.

### 8. Article Page

Articles are editorial outputs for a specific moment.

Sections:

- headline,
- standfirst,
- timestamp and update status,
- analysis body,
- source transparency where appropriate,
- embedded links to Story, Team, Race and Technical entities,
- “continue following this story” module.

Article pages should feed users into persistent pages rather than become dead ends.

## MVP screen priority

### P0 — required before public launch

- Home
- Race Hub
- Article Page
- Story Page
- Team Page
- basic search / internal navigation

### P1 — immediately after launch

- Upgrade Tracker
- Technical Explainer template
- Regulation Explainer template
- Newsletter landing/signup flow

### P2 — after content volume justifies it

- Driver pages
- component-level upgrade comparison
- story-following/personalization
- advanced filters and timelines
- data visualizations

## Internal linking rules

Every current article should link to at least one persistent entity where relevant:

```text
Article -> Race Hub
Article -> Story Page
Article -> Team Page
Article -> Technical/Regulation Explainer
```

Persistent pages should link back to the strongest supporting current outputs.

This creates a graph rather than a chronological pile of posts.

## Homepage editorial hierarchy

Do not order content purely by publication timestamp.

Recommended ranking dimensions:

- significance,
- recency,
- evidence strength,
- ongoing reader interest,
- relationship to the current race weekend,
- amount of meaningful new information.

A minor new press release should not automatically displace an important developing story.

## Mobile-first consideration

Most race-weekend consumption is likely to happen on mobile. The MVP should therefore prioritize:

- fast loading,
- clear headline hierarchy,
- compact timeline cards,
- sticky race/story context,
- short summaries before deeper analysis,
- low-friction movement between related pages.

Dense desktop dashboards should not define the first version of the public site.
