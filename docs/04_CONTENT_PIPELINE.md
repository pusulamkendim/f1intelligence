# Content Pipeline

## Goal

The pipeline should convert many fragmented inputs into structured, evidence-linked intelligence that can support several editorial outputs.

The pipeline exists to improve research quality, continuity and speed. It should not exist merely to automate article volume.

## High-level flow

```text
Sources
  -> Ingestion
  -> Normalization
  -> Entity extraction
  -> Story matching / clustering
  -> Evidence store
  -> Significance scoring
  -> Analysis brief
  -> Editorial review
  -> Publication
  -> Feedback / story update
```

## 1. Source ingestion

Potential source classes:

- FIA documents and notices
- official F1/team/driver communications
- established motorsport journalism
- press-conference/interview transcripts
- session and race data where legally usable
- technical observations and imagery with appropriate rights
- Reddit and other communities for discussion signals

Each ingested item should preserve provenance, original timestamp and source class.

## 2. Normalization

Convert different source types into a common internal structure.

Minimum normalized fields:

```text
source_id
source_type
source_name
published_at
captured_at
title
body_or_reference
url_or_reference
speaker_or_author
language
```

Raw material should remain recoverable even after downstream extraction.

## 3. Entity extraction

Identify relevant entities:

- team
- driver
- race
- circuit
- car/component
- regulation
- technical concept
- named incident

Entity extraction enables clustering, linking and later retrieval.

## 4. Claim and evidence extraction

The model may propose structured claims, but the system should preserve whether each claim is:

- direct fact from source,
- attributed statement,
- extracted observation,
- model/editor interpretation.

Do not collapse these categories.

## 5. Story matching

For each new evidence item, attempt to match it to an existing Story Object.

Example:

```text
New item:
"Driver reports instability on corner entry after FP2"

Possible existing story:
"Red Bull rear stability problem"
```

Matching can consider:

- entity overlap,
- semantic similarity,
- temporal proximity,
- race/event context,
- technical component overlap,
- existing story keywords and embeddings.

A model may recommend a match, but uncertain cases should remain reviewable.

## 6. Significance scoring

Scoring is internal prioritization, not a public truth metric.

Potential dimensions:

- competitive impact,
- championship relevance,
- technical novelty,
- regulatory significance,
- number/quality of supporting sources,
- amount of genuinely new information,
- current race-weekend relevance,
- reader interest.

Use the score to rank analyst attention, not to auto-publish conclusions.

## 7. Story update

When new evidence materially changes a Story, update:

- `what_changed`
- current summary
- timeline
- confidence
- `why_it_matters`
- `what_to_watch_next`

The change itself should be recorded so the system can later explain how the story evolved.

## 8. Analysis Brief

The primary machine-assisted editorial output should be an **Analysis Brief**, not a finished article.

Suggested structure:

```text
Story: Red Bull rear stability

What changed
- ...

Confirmed evidence
- ...

Relevant quotes
- ...

Historical context
- ...

Possible interpretations
- ...

Contradictory / missing evidence
- ...

Why it matters
- ...

What to watch next
- ...

Recommended related pages
- ...
```

This gives an editor or author a high-signal research package.

## 9. Editorial decision

Editor selects the appropriate output:

- no publication; update Story only
- homepage intelligence card
- race-hub update
- breaking analysis
- technical explainer update
- upgrade tracker entry
- post-session analysis
- newsletter item

Not every source event deserves a standalone article.

## 10. Publication

Published content should preserve structured relationships to:

- Story IDs
- Evidence IDs
- Race
- Teams/drivers
- technical concepts
- upgrade entries

This allows a publication to automatically appear in the correct Race Hub, Story Page and Team Page.

## 11. Feedback loop

After publication, collect:

- search impressions/clicks
- page engagement
- internal-navigation behavior
- newsletter conversions
- updates or corrections
- later evidence that confirms or contradicts an interpretation

The purpose is to improve both editorial prioritization and product navigation.

## Race-weekend operating cycle

### Before the weekend

- identify active season-long stories
- create/update Race Hub
- collect circuit-specific technical context
- ingest team previews and regulatory notices
- prepare questions to watch

### Practice

- ingest session evidence and comments
- update active stories
- publish only meaningful changes

### Qualifying

- link result to prior practice expectations
- distinguish one-lap performance from broader race conclusions
- create qualifying analysis

### Race

- update strategy, incidents and performance evidence
- preserve chronology
- produce race analysis

### Post-race

- produce "What we learned"
- update team/upgrade trackers
- promote durable insights into Story Pages
- identify which storylines carry into the next event

## Automation boundaries

Good automation targets:

- source collection
- deduplication
- transcript parsing
- entity extraction
- source classification
- semantic story matching
- timeline construction
- related-content suggestions
- evidence retrieval
- first-pass briefs

Human/editorial control should remain strongest for:

- deciding what is significant
- resolving contradictory evidence
- separating fact from interpretation
- final headlines and framing
- legal/IP-sensitive material
- corrections
- deciding whether evidence is sufficient to publish

## Quality gates before public publication

A publication should normally pass:

1. provenance available for important factual claims,
2. no unsupported interpretation written as fact,
3. meaningful added value beyond source rewriting,
4. correct entity/story links,
5. duplication check against existing pages,
6. rights check for images/data/media,
7. clear update timestamp when a live story changes.

## Initial implementation approach

Start with a semi-automated workflow. Do not overbuild an autonomous publishing system before we know which editorial steps are repeated often enough to justify automation.

MVP target:

```text
Automated ingestion + structured Story/Evidence storage
                    ↓
Machine-generated Analysis Brief
                    ↓
Human/editor approval
                    ↓
CMS publication + automatic graph linking
```
