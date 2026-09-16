# MVP UI Specification

## Purpose

This document turns the P0 page types defined in `02_INFORMATION_ARCHITECTURE.md` into an implementation-ready public UI specification.

The MVP is a mobile-first editorial intelligence product, not a dense analytics dashboard. Every screen should help the reader answer one of three questions quickly:

1. What changed?
2. Why does it matter?
3. What should I follow next?

The public UI should expose strong context and source transparency without exposing internal editorial machinery such as raw confidence scores, ingestion state or debugging metadata.

---

## 1. Shared application shell

### Header

Desktop:

- brand mark / site name,
- primary navigation: `Races`, `Teams`, `Stories`, `Technical`, `Regulations`,
- search control,
- newsletter CTA.

Mobile:

- brand mark,
- search icon,
- menu trigger,
- no permanently expanded navigation.

The header should remain visually quiet. Current content should dominate the page.

### Global context strip

When a race weekend is active or imminent, show a compact contextual strip below the header:

```text
Azerbaijan GP · Round 17
FP1 Friday 12:30 UTC · Race Sunday 11:00 UTC
[Open race hub]
```

This strip should disappear when there is no useful current-event context.

### Footer

Required items:

- About / editorial approach,
- source and corrections policy,
- contact,
- newsletter,
- privacy / cookie controls,
- legal / unofficial-site disclaimer,
- copyright.

### Shared card grammar

Cards should use a small number of reusable visual patterns instead of unique layouts for every module.

Core card types:

- `LeadStoryCard`
- `StoryCard`
- `ArticleCard`
- `RaceCard`
- `TeamCard`
- `UpdateCard`
- `ExplainerCard`

Each card should make its object type visually clear and avoid presenting all objects as generic news posts.

### Shared metadata

Where relevant, content may expose:

- updated/published time,
- associated race,
- associated team(s),
- object type,
- developing/resolved status for Story objects,
- source count where useful,
- reading time for long publications.

Do not expose internal `confidence` values directly in the MVP.

### Search

P0 search should support at minimum:

- stories,
- teams,
- races,
- articles/publications.

The search result should identify object type and route the reader to the canonical object, not merely return article matches.

---

# 2. Home screen

Route: `/`

## User goal

Understand the most important current F1 developments in under 30 seconds, then move into deeper context.

## Desktop structure

```text
[Header]
[Current race strip]

[Lead Story -----------------------------------]
[Why it matters]                   [Next Race]

[What Changed Today ---------------------------]
[Update] [Update] [Update]

[Developing Stories ---------------------------]
[Story]  [Story]  [Story]

[Current Race / Weekend -----------------------]
[Race context + latest session analysis]

[Team Development -----------------------------]
[Team/update cards]

[Technical / Regulation Explainers ------------]
[Explainer] [Explainer]

[Newsletter CTA]
[Footer]
```

## Mobile order

1. Current race strip
2. Lead story
3. What changed today
4. Current race hub shortcut
5. Developing stories
6. Team development
7. Explainers
8. Newsletter

No two-column editorial layout should be required on mobile.

## Components

### `LeadStoryCard`

Data:

- story id,
- title,
- summary,
- `why_it_matters`,
- last meaningful update,
- primary entities,
- hero visual when available.

Actions:

- open Story Page,
- open latest associated analysis.

Rules:

- exactly one lead story,
- selected by editorial ranking rather than latest timestamp,
- must contain meaningful new information.

### `WhatChangedToday`

A compact list of 3-6 meaningful changes.

Each item contains:

- timestamp or session context,
- one-sentence factual change,
- associated team/story/race,
- route to source context or canonical story.

This is not a generic headline feed.

### `DevelopingStories`

Show 3-6 Story objects with:

- title,
- latest change,
- `why_it_matters` excerpt,
- status,
- entity chips,
- last updated.

### `CurrentRaceModule`

Show:

- event name,
- round/circuit,
- current weekend state,
- latest completed session,
- next session,
- 2-3 key storylines,
- Race Hub CTA.

### `TeamDevelopmentModule`

Show recent meaningful technical or performance-development changes by team.

Avoid league-table style ranking unless it is based on explicit measurable data.

## Empty / quiet-day state

If there are few new developments, the homepage should become more evergreen rather than manufacture urgency. Increase prominence of:

- active season-long stories,
- current team development pages,
- technical explainers,
- next race preview.

## Success events

Track:

- `home_lead_opened`,
- `home_story_opened`,
- `home_race_hub_opened`,
- `home_explainer_opened`,
- `newsletter_cta_clicked`.

---

# 3. Race Hub

Route example: `/races/2026/azerbaijan-grand-prix/`

## User goal

Use one canonical page before, during and after the race weekend instead of navigating a pile of disconnected articles.

## Page states

The Race Hub evolves through four states:

1. `upcoming`
2. `live_weekend`
3. `post_race`
4. `archived`

The URL does not change between states.

## Structure

```text
[Race Header]
[Weekend Status / Session Navigation]
[Weekend Summary]
[Key Storylines]
[Latest Analysis]
[Session Timeline]
[Technical Updates]
[Strategy Notes]
[Important Quotes]
[What We Learned]
[Related Season Stories]
```

## `RaceHeader`

Display:

- official event name,
- season and round,
- circuit / country,
- weekend dates,
- event status,
- next session or final result state.

Avoid unnecessary decorative telemetry in MVP.

## `SessionNavigation`

Tabs or anchors:

- Preview
- Practice
- Qualifying
- Race
- What We Learned

Only enabled sections should be selectable.

On mobile, use a horizontally scrollable sticky control below the race header.

## `WeekendSummary`

A short editorial synthesis, updated as the weekend evolves.

Data source:

- `Race.synthesis`
- key associated Story objects.

Maximum initial visible length should be approximately 3 short paragraphs before expansion.

## `KeyStorylines`

3-5 Story objects most relevant to this event.

Each card shows:

- story title,
- pre-event question or latest conclusion,
- latest race-specific update,
- team/driver associations.

## `SessionTimeline`

Chronological event stream built from `TimelineEvent` and associated publications.

Each item may include:

- session,
- time,
- event title,
- concise summary,
- evidence/source indication,
- link to deeper analysis.

The stream should prioritize meaningful events over lap-by-lap logging.

## `TechnicalUpdates`

Show `UpgradeEntry` objects first seen at this event.

Fields:

- team,
- component,
- change summary,
- documented intended effect if available,
- classification,
- link to team Upgrade Tracker.

Unknown intended effect must stay explicitly unknown.

## `StrategyNotes`

Editorial module for:

- tyre choices,
- undercut/overcut relevance,
- safety-car sensitivity,
- weather implications,
- race-specific tactical observations.

Clearly separate documented facts from analysis.

## `ImportantQuotes`

Only use quotes that add explanatory value. Each quote should retain:

- speaker,
- role/team,
- context/session,
- source attribution.

## `WhatWeLearned`

Post-race synthesis. This can link to a full Publication but the Race Hub should still contain a compact persistent summary.

## Mobile behavior

Mobile must prioritize:

1. race state,
2. next/latest session,
3. weekend summary,
4. key storylines,
5. latest analysis.

Technical detail and quote modules can appear lower.

## Success events

- `race_session_tab_changed`,
- `race_story_opened`,
- `race_analysis_opened`,
- `race_upgrade_opened`,
- `race_related_story_opened`.

---

# 4. Story Page

Route example: `/stories/red-bull-rear-stability/`

## User goal

Understand how one important F1 storyline developed over time, what is known now and what remains unresolved.

This is the product's main differentiating screen.

## Structure

```text
[Story Header]
[Current State]
[Why It Matters]
[What Changed]
[Evidence Timeline]
[Technical / Performance Context]
[Quotes]
[Interpretations]
[Related Publications]
[Related Stories]
[What To Watch Next]
```

## `StoryHeader`

Display:

- title,
- concise summary,
- status (`emerging`, `developing`, etc.) in reader-friendly language,
- associated teams/drivers/races,
- last meaningful update.

Internal significance/confidence metadata should not be displayed directly.

## `CurrentState`

The first substantive block should answer:

> What is the best-supported current understanding?

Data:

- Story summary,
- latest stable interpretation,
- supporting evidence references.

This block should be updated rather than accumulating obsolete summaries.

## `WhyItMatters`

Use `Story.why_it_matters`.

Keep it short: typically 2-4 sentences.

## `WhatChanged`

Use `Story.what_changed` to show the delta from the previous meaningful state.

Example UI:

```text
WHAT CHANGED · 3 hours ago
Red Bull introduced a revised floor edge and Verstappen reported improved entry stability after FP2.
```

## `EvidenceTimeline`

Chronological grouped timeline of material events.

Timeline item types should visually distinguish:

- documented technical change,
- quote/source claim,
- session observation,
- race outcome,
- editorial interpretation update.

Every material factual item should be traceable to evidence.

### Timeline filters

MVP desktop:

- All
- Technical
- Quotes
- Sessions
- Analysis

Mobile may initially ship without filters if timeline length is manageable.

## `InterpretationBlock`

Interpretation must be visually distinguishable from fact/source claim.

Suggested labels:

- `Analysis`
- `Our read`

Avoid visual language that implies certainty beyond evidence.

## `WhatToWatchNext`

Prominent closing module using `Story.what_to_watch_next`.

Example:

- whether the package remains on the car at the next high-downforce circuit,
- long-run tyre degradation,
- driver feedback after qualifying.

This gives the user a reason to return to the same Story URL.

## Related content

Prioritize:

1. latest direct publication,
2. related Race Hub,
3. Team Page,
4. technical explainer,
5. adjacent Story objects.

## Mobile behavior

Use a compact sticky story context header after the user scrolls beyond the hero:

```text
Red Bull rear stability · Developing
```

Do not use a permanently visible large sidebar.

## Success events

- `story_timeline_expanded`,
- `story_evidence_opened`,
- `story_publication_opened`,
- `story_related_story_opened`,
- `story_team_opened`.

---

# 5. Team Page

Route example: `/teams/red-bull/`

## User goal

Understand a team's current competitive and development picture without reconstructing it from dozens of articles.

## Structure

```text
[Team Header]
[Current Context]
[Latest Meaningful Change]
[Active Stories]
[Development Timeline]
[Recent Race Context]
[Latest Analysis]
[Drivers]
[Upgrade Tracker CTA]
```

## `TeamHeader`

Display:

- team name,
- current season,
- drivers,
- latest race context,
- link to season upgrade tracker.

Avoid unauthorized use of protected team/F1 graphical assets where licensing is unclear.

## `CurrentContext`

Editorial summary of the team's present situation.

Should answer:

- what is working,
- what problems are active,
- what changed recently,
- which story should the reader follow.

Do not turn this into an unsupported subjective power ranking.

## `LatestMeaningfulChange`

One prominent recent development selected from:

- UpgradeEntry,
- Story update,
- significant race observation,
- documented personnel/regulatory development.

## `ActiveStories`

List 3-6 active Story objects associated with the team.

Sort by editorial significance and meaningful recency.

## `DevelopmentTimeline`

Condensed season timeline combining important UpgradeEntries and major Story changes.

Each row:

- race/event,
- component/topic,
- change,
- observed follow-up if known.

The dedicated Upgrade Tracker remains the deeper technical reference.

## `RecentRaceContext`

Show the latest 3-5 events with concise summaries rather than only finishing position.

Possible fields:

- result,
- qualifying context,
- key limitation/strength,
- linked story,
- major technical change.

## `Drivers`

MVP driver cards provide:

- name,
- current team relationship,
- latest associated stories,
- route to driver page only if/when that page exists.

## Mobile behavior

Order:

1. team header,
2. current context,
3. latest meaningful change,
4. active stories,
5. recent race context,
6. development timeline,
7. latest analysis.

## Success events

- `team_story_opened`,
- `team_upgrade_tracker_opened`,
- `team_race_opened`,
- `team_article_opened`.

---

# 6. Article Page

Route: `/articles/{slug}/`

## User goal

Read one time-bound piece of analysis, understand its evidence and then continue into the persistent context behind it.

## Structure

```text
[Article Header]
[Standfirst]
[Context Links]
[Body]
[Source / Evidence Notes]
[Continue Following This Story]
[Related Race / Team / Explainer]
[Newsletter CTA]
```

## `ArticleHeader`

Display:

- publication type,
- headline,
- standfirst,
- published time,
- updated time when materially changed,
- byline/editorial attribution when applicable,
- reading time.

## `ContextLinks`

Immediately below the header, show canonical context links when available:

```text
Following: Red Bull rear stability
Race: Azerbaijan GP
Team: Red Bull
```

This reinforces that articles are snapshots and Story/Team/Race pages are persistent objects.

## Body

Requirements:

- strong heading hierarchy,
- short paragraphs suitable for mobile,
- original diagrams/charts where valuable,
- in-text links to entity pages,
- clear attribution for external claims,
- clear distinction between source claims and editorial interpretation.

Avoid aggressive inline ad density in the MVP.

## `EvidenceNotes`

For analysis-heavy articles, expose a compact source section containing the most material references.

The UI does not need to dump every internal Evidence object, but a reader should be able to understand the basis for significant claims.

## `ContinueFollowing`

This is the key article exit module.

Priority destination:

1. canonical Story Page,
2. Race Hub,
3. Team Page,
4. related explainer.

Example:

```text
CONTINUE FOLLOWING
Red Bull's rear-stability story
12 updates · latest 2h ago
[Open story]
```

## Mobile behavior

- headline must fit without oversized typography,
- context links become compact chips or stacked rows,
- reading column uses full available width with comfortable margins,
- sticky share controls are optional and not P0,
- no desktop-style right rail is required.

## Success events

- `article_context_story_opened`,
- `article_context_race_opened`,
- `article_context_team_opened`,
- `article_source_opened`,
- `article_related_content_opened`.

---

# 7. Cross-screen interaction rules

## Canonical-object routing

When the same subject is shown in multiple places, links should prefer persistent objects where appropriate.

Examples:

```text
Headline about evolving technical problem -> Story Page
Event/session context -> Race Hub
Team context -> Team Page
One-time editorial analysis -> Article Page
```

## Back-navigation and context

Readers frequently enter from search/social directly into deep pages. Every page must therefore explain its own context and provide meaningful onward navigation without relying on the homepage.

## Entity chips

Entity chips should be navigational, not decorative.

Examples:

- `Red Bull`
- `Azerbaijan GP`
- `Floor`

Only render a chip if the destination exists or the taxonomy has a real user-facing purpose.

## Time language

Use both human-friendly recency and durable timestamps where needed.

Example:

```text
Updated 2h ago · 16 Sep 2026, 14:20 UTC
```

Archived pages should favor absolute dates.

## Loading and skeletons

Skeletons should resemble the final module shape and not block the entire screen for one slow secondary request.

Critical content order:

1. page identity/header,
2. primary summary,
3. primary Story/Race content,
4. secondary modules.

## Error states

If a secondary module fails, keep the core page usable.

Examples:

- failed quote module should not fail the Race Hub,
- missing upgrade data should show no module rather than a fake empty timeline,
- unavailable source link should not erase the normalized evidence summary.

---

# 8. Responsive behavior

Suggested breakpoints are implementation details, but behavior should follow these principles.

## Mobile

- single primary column,
- 16-20px content gutters,
- horizontal scroll only for compact navigation/tabs,
- no interaction dependent on hover,
- tap targets at least approximately 44px,
- contextual sticky bars may be used sparingly.

## Tablet

- primarily one column with selective two-column card groups,
- do not introduce desktop sidebars solely because width permits them.

## Desktop

- editorial content width remains constrained,
- secondary context can use a right rail on Home/Race/Team screens,
- Article and Story reading columns should remain comfortable rather than spanning the viewport.

---

# 9. Accessibility requirements

P0 requirements:

- semantic heading order,
- keyboard-navigable menus and tabs,
- visible focus states,
- sufficient text/background contrast,
- text alternatives for meaningful images and diagrams,
- do not encode status only through color,
- accessible labels for icon-only controls,
- reduced-motion support for non-essential animation.

Tables/timelines must remain understandable with screen readers.

---

# 10. Performance requirements

The product is likely to receive race-weekend mobile traffic. Performance is a product requirement.

Initial targets:

- server-render or statically render public editorial pages where practical,
- minimize client-side JavaScript for reading flows,
- lazy-load below-the-fold media,
- use responsive images,
- reserve image dimensions to avoid layout shifts,
- avoid third-party scripts unless they have measurable value,
- ads must not cause major content layout movement.

Core Web Vitals should be monitored per template, not only site-wide.

---

# 11. Visual direction

The brand should feel closer to a serious motorsport publication / technical notebook than a betting dashboard or generic news aggregator.

Desired qualities:

- editorial,
- technical,
- restrained,
- data-aware,
- fast,
- legible.

Avoid:

- excessive gradients/glow,
- fake telemetry decoration,
- dense dashboards on reader-facing pages,
- card overload,
- visually treating every update as breaking news.

A future design-system document should define typography, spacing, color tokens, component states and chart conventions after the first low-fidelity prototypes are validated.

---

# 12. P0 component inventory

Shared:

```text
AppHeader
MobileMenu
CurrentRaceStrip
SearchTrigger
SearchResults
EntityChip
Timestamp
SectionHeader
NewsletterCTA
Footer
```

Home:

```text
LeadStoryCard
WhatChangedToday
UpdateCard
DevelopingStories
StoryCard
CurrentRaceModule
TeamDevelopmentModule
ExplainerCard
```

Race Hub:

```text
RaceHeader
SessionNavigation
WeekendSummary
KeyStorylines
SessionTimeline
TechnicalUpdates
StrategyNotes
ImportantQuotes
WhatWeLearned
```

Story:

```text
StoryHeader
CurrentState
WhyItMatters
WhatChanged
EvidenceTimeline
InterpretationBlock
RelatedPublications
WhatToWatchNext
```

Team:

```text
TeamHeader
CurrentContext
LatestMeaningfulChange
ActiveStories
DevelopmentTimeline
RecentRaceContext
DriverCards
UpgradeTrackerCTA
```

Article:

```text
ArticleHeader
ContextLinks
ArticleBody
EvidenceNotes
ContinueFollowing
RelatedContent
```

---

# 13. MVP acceptance criteria

The public UI is ready for the first content beta when all of the following are true:

1. A user can enter through any Article and reach its relevant Story, Race or Team context.
2. A Story Page can communicate current understanding, timeline and next question without requiring the reader to open every underlying article.
3. A Race Hub can evolve through a weekend without changing URL or duplicating session pages as separate canonical hubs.
4. Team Pages expose active stories and development context rather than functioning as article tag archives.
5. Home editorial ranking is independent from pure publication chronology.
6. All five P0 screens work cleanly on mobile.
7. Core factual/analytical distinctions survive the UI layer.
8. No screen requires unsupported data fields outside the MVP content model without an explicit fallback.
9. The page can remain useful when optional modules have no data.
10. Internal linking creates a coherent graph between Article, Story, Race and Team objects.

---

# 14. Next design step

Before visual design, produce low-fidelity wireframes for these flows:

1. Home -> Story -> related Race Hub
2. Search/social -> Article -> Continue Following -> Story
3. Home -> Race Hub -> session analysis -> Story
4. Team -> active Story -> technical evidence timeline
5. Mobile Race Hub during a live weekend

The wireframes should validate hierarchy and navigation before typography, branding or decorative styling is finalized.
