# Story and Content Model

## Principle

The canonical knowledge unit is the **Story Object**. Articles, race summaries, newsletter sections and tracker entries are outputs built from structured story data and evidence.

A Story is persistent. It can begin before a race, evolve during several events and remain relevant for months.

## Story Object

Conceptual schema:

```text
Story
├── id
├── slug
├── title
├── summary
├── status
├── significance
├── confidence
├── topics[]
├── teams[]
├── drivers[]
├── races[]
├── components[]
├── regulations[]
├── timeline_events[]
├── evidence[]
├── quotes[]
├── observations[]
├── interpretations[]
├── related_stories[]
├── publications[]
├── what_changed
├── why_it_matters
├── what_to_watch_next
├── created_at
├── updated_at
└── editorial_state
```

## Status

Suggested values:

- `emerging` — evidence exists but the storyline is still taking shape.
- `developing` — active story with continuing updates.
- `stable` — current interpretation is relatively mature.
- `resolved` — the main question is no longer active.
- `dormant` — currently inactive but may return.

Status is editorial metadata, not a factual claim.

## Evidence model

Every material factual assertion should be traceable to evidence.

```text
Evidence
├── id
├── source_type
├── source_name
├── source_url_or_reference
├── published_at
├── captured_at
├── author_or_speaker
├── raw_excerpt_or_reference
├── normalized_claim
├── reliability_class
├── directness
├── entities[]
├── story_ids[]
└── notes
```

Possible `source_type` values:

- FIA document
- official team statement
- official driver/team interview
- established journalism
- session/race data
- technical image/observation
- community discussion
- internal analysis

Community discussion should normally be treated as a lead or interpretation source, not as authoritative evidence for a factual claim.

## Claim separation

The system should preserve the distinction between four layers:

### Fact

Directly documented or observable information.

Example: a team submitted a revised floor edge at a specific event.

### Source claim

Something a named source says.

Example: a driver says rear instability is affecting corner entry.

### Observation

A pattern visible in data or repeated events.

Example: tyre degradation appears higher on long runs over three sessions.

### Interpretation

An editorial explanation joining facts, claims and observations.

Example: an upgrade may have shifted the car's balance toward qualifying performance at the expense of tyre life.

Interpretation must not be stored as if it were a source fact.

## Timeline Event

```text
TimelineEvent
├── id
├── occurred_at
├── event_type
├── race_id
├── session
├── title
├── summary
├── evidence_ids[]
├── affected_entities[]
└── story_ids[]
```

Typical event types:

- upgrade introduced
- technical directive issued
- quote/public statement
- setup change
- session observation
- race outcome
- regulation change
- incident
- story interpretation update

## Upgrade Entry

Upgrade tracking is a specialized content object linked to Stories and Teams.

```text
UpgradeEntry
├── id
├── team
├── season
├── race
├── component
├── change_summary
├── intended_effect
├── classification
├── first_seen_at
├── evidence_ids[]
├── related_story_ids[]
├── follow_up_observations[]
└── status
```

`classification` examples:

- permanent development
- experimental
- circuit-specific
- cooling adaptation
- reliability change
- unclear

Do not infer intended effect when the source does not establish it; use `unknown` or an explicitly labelled interpretation.

## Race Object

```text
Race
├── id
├── season
├── round
├── official_name
├── circuit
├── country
├── start_at
├── sessions[]
├── key_story_ids[]
├── upgrade_ids[]
├── publication_ids[]
└── synthesis
```

The Race Object powers the Race Hub.

## Publication Object

A publication is an editorial artifact derived from the knowledge graph.

```text
Publication
├── id
├── type
├── slug
├── headline
├── standfirst
├── body
├── story_ids[]
├── evidence_ids[]
├── race_ids[]
├── team_ids[]
├── published_at
├── updated_at
└── status
```

Types may include:

- breaking analysis
- practice analysis
- qualifying analysis
- race analysis
- what-we-learned
- technical explainer
- regulation explainer
- newsletter section

## Story clustering

Incoming evidence should be attached to an existing Story when it concerns the same underlying question or development.

Create a new Story only when:

- the underlying subject is materially different,
- combining it would make the existing Story incoherent,
- readers would reasonably want to follow it independently.

Avoid creating a new Story for every headline.

## Confidence

Confidence should describe the strength of an interpretation, not the credibility of a person.

Possible internal scale:

- `confirmed` — supported by direct documentation or unambiguous evidence.
- `strong` — multiple consistent sources/observations.
- `tentative` — plausible but incomplete evidence.
- `speculative` — useful lead but insufficient basis for publication as a conclusion.

Public UI does not need to expose these exact labels in the MVP; they are primarily editorial controls.

## Relationships

Important graph edges:

```text
Story <-> Story
Story <-> Team
Story <-> Driver
Story <-> Race
Story <-> Regulation
Story <-> UpgradeEntry
Story <-> Evidence
Story <-> Publication
TechnicalExplainer <-> Story
```

The value of the platform should increase as these relationships accumulate.

## Minimum viable model

The database does not need the full schema on day one.

MVP entities:

- Story
- Evidence
- Race
- Team
- Publication
- UpgradeEntry

Add Driver, Regulation, TechnicalConcept and richer graph relationships when actual product use requires them.
