# Low-Fidelity Wireframes and Key User Flows

## Purpose

This document converts the MVP information architecture and UI specification into low-fidelity interaction flows before visual design begins.

These wireframes deliberately avoid brand color, typography, illustration style and decorative decisions. The goal is to validate hierarchy, navigation, information density and movement between canonical objects.

The product rule remains:

> Articles are snapshots. Stories, Race Hubs and Team Pages are persistent context.

---

# 1. Flow A — Home → Story → Race Hub

## Goal

A reader arriving on the homepage should understand the most important current development, open its persistent Story Page, and then move naturally into the current race context.

## Flow

```text
HOME
  ↓ lead story
STORY PAGE
  ↓ related/current race
RACE HUB
```

## Home — desktop wireframe

```text
┌──────────────────────────────────────────────────────────────────────┐
│ F1 INTELLIGENCE      Races Teams Stories Technical Regulations  🔍  │
├──────────────────────────────────────────────────────────────────────┤
│ AZERBAIJAN GP · LIVE WEEKEND                      [Open Race Hub]    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  LEAD STORY                                      NEXT SESSION        │
│  Red Bull's rear stability problem              Qualifying          │
│  has changed again                                                   │
│                                                                      │
│  Latest: revised floor + stronger FP2 balance    Sat · 14:00         │
│  Why it matters: qualifying pace may no longer   [Race Hub]          │
│  be the main limitation.                                              │
│                                                                      │
│  [Follow story →]                                                      │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│ WHAT CHANGED TODAY                                                    │
│                                                                      │
│  13:42  Red Bull revised floor edge                  [Story →]       │
│  12:20  Ferrari changed rear-wing configuration      [Story →]       │
│  10:05  FIA issued updated technical note            [Context →]     │
├──────────────────────────────────────────────────────────────────────┤
│ DEVELOPING STORIES                                                   │
│                                                                      │
│ [Story Card]        [Story Card]        [Story Card]                 │
├──────────────────────────────────────────────────────────────────────┤
│ CURRENT RACE                                                         │
│ Azerbaijan GP · FP2 complete · 3 key storylines      [Open hub →]   │
├──────────────────────────────────────────────────────────────────────┤
│ TEAM DEVELOPMENT                                                     │
│ [Update] [Update] [Update]                                           │
├──────────────────────────────────────────────────────────────────────┤
│ TECHNICAL EXPLAINERS                                                 │
│ [Explainer] [Explainer]                                              │
├──────────────────────────────────────────────────────────────────────┤
│ NEWSLETTER CTA                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

## Story Page — desktop wireframe

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Header                                                               │
├──────────────────────────────────────────────────────────────────────┤
│ STORY · DEVELOPING                                                   │
│                                                                      │
│ Red Bull's rear stability problem                                    │
│ Updated 38 min ago                                                   │
│                                                                      │
│ [Red Bull] [Verstappen] [Azerbaijan GP]                              │
├──────────────────────────────────────────────────────────────────────┤
│ CURRENT STATE                                                        │
│ Best-supported current understanding in 2–4 short paragraphs.       │
├──────────────────────────────────────────────────────────────────────┤
│ WHY IT MATTERS                                                       │
│ Short explanation.                                                   │
├──────────────────────────────────────────────────────────────────────┤
│ WHAT CHANGED · 38 MIN AGO                                            │
│ Revised floor edge + improved corner-entry feedback in FP2.         │
├──────────────────────────────────────────────────────────────────────┤
│ EVIDENCE TIMELINE                                                    │
│                                                                      │
│ [All] [Technical] [Quotes] [Sessions] [Analysis]                     │
│                                                                      │
│ 14:22  TECHNICAL CHANGE                                               │
│        Revised floor edge first documented                           │
│        [View evidence]                                                │
│                                                                      │
│ 15:05  DRIVER CLAIM                                                   │
│        Verstappen reports improved entry stability                   │
│        [Source]                                                       │
│                                                                      │
│ 16:10  OUR READ                                                       │
│        Long-run balance looks improved, but tyre life remains open.  │
├──────────────────────────────────────────────────────────────────────┤
│ CURRENT RACE CONTEXT                                                  │
│ Azerbaijan GP · FP2 complete                                         │
│ [Open Race Hub →]                                                     │
├──────────────────────────────────────────────────────────────────────┤
│ WHAT TO WATCH NEXT                                                    │
│ • Qualifying sector 2 stability                                      │
│ • Long-run degradation                                               │
│ • Whether package remains on car                                     │
└──────────────────────────────────────────────────────────────────────┘
```

## Race Hub — destination state

```text
┌──────────────────────────────────────────────────────────────────────┐
│ AZERBAIJAN GRAND PRIX · ROUND 17                                     │
│ FP2 complete · Qualifying next                                       │
├──────────────────────────────────────────────────────────────────────┤
│ [Preview] [Practice] [Qualifying] [Race] [What We Learned]           │
├──────────────────────────────────────────────────────────────────────┤
│ WEEKEND SUMMARY                                                      │
│ 2–3 short paragraphs explaining the weekend so far.                 │
├──────────────────────────────────────────────────────────────────────┤
│ KEY STORYLINES                                                       │
│ [Red Bull rear stability]                                            │
│ [Ferrari tyre warm-up]                                               │
│ [McLaren straight-line loss]                                         │
├──────────────────────────────────────────────────────────────────────┤
│ LATEST ANALYSIS                                                      │
│ [Article] [Article]                                                   │
├──────────────────────────────────────────────────────────────────────┤
│ SESSION TIMELINE                                                     │
│ ...                                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

## Validation questions

- Can a new reader distinguish a Story from an Article without explanation?
- Does the Story Page provide enough value before the user reaches the timeline?
- Is Race Hub navigation visible without dominating the Story Page?
- Does the user understand that the Story persists beyond one race?

---

# 2. Flow B — Search / Social → Article → Story

## Goal

A reader arriving from Google, Reddit, X or another external source should read the article and then be converted into a persistent-story reader instead of leaving the site.

## Flow

```text
GOOGLE / SOCIAL / REFERRAL
          ↓
       ARTICLE
          ↓
  CONTINUE FOLLOWING
          ↓
      STORY PAGE
```

## Article Page — desktop wireframe

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Header                                                               │
├──────────────────────────────────────────────────────────────────────┤
│ PRACTICE ANALYSIS                                                    │
│                                                                      │
│ Red Bull's new floor improved entry stability —                     │
│ but one question remains                                             │
│                                                                      │
│ Standfirst explaining the article's specific contribution.          │
│                                                                      │
│ Published 16 Sep · Updated 18:14 · 6 min read                       │
├──────────────────────────────────────────────────────────────────────┤
│ CONTEXT                                                              │
│ Following: [Red Bull rear stability]                                 │
│ Race:      [Azerbaijan GP]                                           │
│ Team:      [Red Bull]                                                │
├──────────────────────────────────────────────────────────────────────┤
│ ARTICLE BODY                                                         │
│                                                                      │
│ Intro                                                                │
│                                                                      │
│ ## What changed                                                      │
│ Text + original diagram                                              │
│                                                                      │
│ ## What the evidence says                                            │
│ Text + attribution                                                   │
│                                                                      │
│ ## What remains uncertain                                            │
│ Analysis clearly labelled                                            │
├──────────────────────────────────────────────────────────────────────┤
│ EVIDENCE NOTES                                                       │
│ [FIA document] [Team statement] [Session observation]               │
├──────────────────────────────────────────────────────────────────────┤
│ CONTINUE FOLLOWING THIS STORY                                        │
│                                                                      │
│ Red Bull rear stability                                              │
│ 12 updates · latest 38 min ago                                       │
│ [Open Story →]                                                       │
├──────────────────────────────────────────────────────────────────────┤
│ RELATED                                                              │
│ [Race Hub] [Team Page] [Technical Explainer]                         │
└──────────────────────────────────────────────────────────────────────┘
```

## Core behavior

The persistent context block appears near the top; the conversion module appears again after the article body. The reader therefore does not need to know the product model beforehand.

The Story CTA should not say only `Read more`. It should communicate persistence, for example:

```text
Continue following this story
12 updates · latest 38 min ago
```

## Validation questions

- Is the canonical Story visible before the first scroll on common laptop sizes?
- Does the article remain readable without feeling like a navigation page?
- Can a reader identify what is sourced fact versus editorial analysis?
- Is the post-article Story CTA stronger than generic related-article cards?

---

# 3. Flow C — Home → Race Hub → Session Analysis → Story

## Goal

During a live weekend, the Race Hub becomes the central navigation surface. Readers should enter from Home, inspect the current session, open one analysis, then continue into the underlying season-long Story.

## Flow

```text
HOME
 ↓
RACE HUB
 ↓ session tab / latest analysis
SESSION ARTICLE
 ↓ canonical story
STORY PAGE
```

## Live Race Hub wireframe

```text
┌──────────────────────────────────────────────────────────────────────┐
│ AZERBAIJAN GP                                                        │
│ LIVE WEEKEND · QUALIFYING IN 1H 22M                                  │
│ Baku City Circuit · Round 17                                         │
├──────────────────────────────────────────────────────────────────────┤
│ [Preview] [Practice ✓] [Qualifying ●] [Race] [Learned]              │
├──────────────────────────────────────────────────────────────────────┤
│ NOW                                                                  │
│ Practice complete                                                    │
│ Next: Qualifying · 14:00                                             │
├──────────────────────────────────────────────────────────────────────┤
│ WEEKEND SUMMARY                                                      │
│ What the first sessions have changed in our understanding.           │
├──────────────────────────────────────────────────────────────────────┤
│ KEY STORYLINES                                                       │
│ 1. Red Bull rear stability                         [Follow →]        │
│ 2. Ferrari front-tyre preparation                   [Follow →]        │
│ 3. McLaren straight-line deficit                    [Follow →]        │
├──────────────────────────────────────────────────────────────────────┤
│ LATEST SESSION ANALYSIS                                              │
│                                                                      │
│ [Featured Practice Analysis]                                         │
│ Red Bull gains where it struggled yesterday                          │
│ [Read →]                                                             │
│                                                                      │
│ [Article] [Article]                                                   │
├──────────────────────────────────────────────────────────────────────┤
│ SESSION TIMELINE                                                     │
│ 12:05 Technical change                                               │
│ 12:52 Long-run observation                                           │
│ 13:10 Driver quote                                                   │
├──────────────────────────────────────────────────────────────────────┤
│ TECHNICAL UPDATES                                                    │
│ [Red Bull floor] [Ferrari rear wing]                                 │
└──────────────────────────────────────────────────────────────────────┘
```

## Session Article exit

At the article top:

```text
Race: Azerbaijan GP
Following: Red Bull rear stability
```

At article end:

```text
THIS ANALYSIS IS PART OF
Red Bull rear stability
[See the full timeline →]
```

## Validation questions

- Can the user tell what happened in the latest completed session within 10 seconds?
- Is the next session visible without scrolling?
- Do session publications feel subordinate to the Race Hub rather than replacing it?
- Can one session article route into a season-long Story naturally?

---

# 4. Flow D — Team → Story → Evidence Timeline

## Goal

A reader interested in one team should understand its current state, identify the most important active problem or development, and inspect the evidence behind it.

## Flow

```text
TEAM PAGE
   ↓ active story
STORY PAGE
   ↓ timeline event
EVIDENCE DETAIL / SOURCE
```

## Team Page — desktop wireframe

```text
┌──────────────────────────────────────────────────────────────────────┐
│ RED BULL · 2026                                                      │
│ Drivers: Verstappen · [Second driver]                                │
│ [2026 Upgrade Tracker →]                                             │
├──────────────────────────────────────────────────────────────────────┤
│ CURRENT CONTEXT                                                      │
│                                                                      │
│ Concise editorial summary: strengths, active limitations, recent     │
│ direction of development.                                            │
├──────────────────────────────────────────────────────────────────────┤
│ LATEST MEANINGFUL CHANGE                                             │
│ Revised floor appears to improve corner-entry stability              │
│ [Open development →]                                                 │
├──────────────────────────────────────────────────────────────────────┤
│ ACTIVE STORIES                                                       │
│                                                                      │
│ [Rear stability · Developing]                                        │
│ [Tyre degradation · Developing]                                      │
│ [High-speed efficiency · Stable]                                     │
├──────────────────────────────────────────────────────────────────────┤
│ RECENT RACE CONTEXT                                                  │
│ Azerbaijan   Qualifying issue / race recovery       [Race Hub]       │
│ Italy        Strong high-speed phase                 [Race Hub]       │
│ Netherlands  Rear limitation remained               [Race Hub]       │
├──────────────────────────────────────────────────────────────────────┤
│ DEVELOPMENT TIMELINE                                                 │
│ Australia   Front wing                                               │
│ Imola       Floor                                                    │
│ Silverstone Rear suspension                                          │
│ Azerbaijan  Floor edge                                               │
│ [Full tracker →]                                                      │
├──────────────────────────────────────────────────────────────────────┤
│ LATEST ANALYSIS                                                      │
│ [Article] [Article] [Article]                                        │
└──────────────────────────────────────────────────────────────────────┘
```

## Evidence timeline interaction

Clicking an event should open a lightweight detail layer or inline expansion before sending the reader to an external source.

```text
┌──────────────────────────────────────────────────────────────┐
│ 16 SEP · AZERBAIJAN GP · TECHNICAL CHANGE                    │
│                                                              │
│ Revised floor edge                                           │
│                                                              │
│ What is documented                                           │
│ The submitted component differs in X/Y documented respects.  │
│                                                              │
│ Why it matters                                               │
│ Editorial interpretation, explicitly labelled.               │
│                                                              │
│ Evidence                                                     │
│ • FIA technical document                                     │
│ • Team image / official note                                 │
│                                                              │
│ [Open source] [Open race context]                            │
└──────────────────────────────────────────────────────────────┘
```

## Validation questions

- Does the Team Page summarize rather than duplicate every Story?
- Is one current team narrative clearly more prominent than historical detail?
- Can evidence be inspected without the user losing product context?
- Is the distinction between documented change and interpretation obvious?

---

# 5. Flow E — Mobile Race Hub During Live Weekend

## Goal

Support the highest-frequency race-weekend use case on a phone: “What just happened, what is next, and what matters?”

## Mobile wireframe

```text
┌──────────────────────────────┐
│ F1I                     🔍 ☰ │
├──────────────────────────────┤
│ AZERBAIJAN GP                │
│ LIVE · FP2 COMPLETE          │
│ Qualifying in 1h 22m         │
├──────────────────────────────┤
│ Preview Practice Quali Race  │ ← horizontal sticky tabs
├──────────────────────────────┤
│ WHAT MATTERS NOW             │
│                              │
│ 1. Red Bull stability        │
│    improved in FP2           │
│    [Follow story →]          │
│                              │
│ 2. Ferrari tyre warm-up      │
│    remains inconsistent      │
├──────────────────────────────┤
│ WEEKEND SUMMARY              │
│ 3 short paragraphs...        │
│ [Expand]                     │
├──────────────────────────────┤
│ LATEST ANALYSIS              │
│ [Featured article]           │
│                              │
│ [Article]                    │
├──────────────────────────────┤
│ SESSION TIMELINE             │
│ 13:42 Floor update           │
│ 14:05 Long-run change        │
│ 14:37 Driver quote           │
│ [Show all]                   │
├──────────────────────────────┤
│ TECHNICAL UPDATES            │
│ [Update card]                │
├──────────────────────────────┤
│ WHAT TO WATCH IN QUALIFYING  │
│ • Sector 2 stability         │
│ • Ferrari tyre prep          │
│ • McLaren top speed          │
└──────────────────────────────┘
```

## Mobile priority rule

The first screenful should contain:

1. event identity,
2. current state,
3. next session,
4. one or two key storylines.

The user should not need to scroll through hero photography, championship tables or decorative telemetry before reaching those answers.

## Sticky behavior

After the race header scrolls away:

```text
┌──────────────────────────────┐
│ Azerbaijan GP · FP2 complete │
├──────────────────────────────┤
│ Practice   Quali   Race      │
└──────────────────────────────┘
```

The sticky area should remain compact enough not to consume significant vertical space.

## Validation questions

- Is the next session visible immediately?
- Can the user reach one active Story in one tap?
- Can the user understand the weekend without opening an article?
- Does the sticky UI occupy less than roughly 15–20% of the viewport?

---

# 6. Shared Interaction Patterns

## Canonical context chips

Use the same component everywhere:

```text
[Story: Rear stability]
[Race: Azerbaijan GP]
[Team: Red Bull]
```

These should be navigational, not decorative tags.

## Object labels

Use explicit object labels when ambiguity is possible:

```text
STORY
RACE HUB
ANALYSIS
TECHNICAL EXPLAINER
REGULATION
TEAM
```

A user should never have to infer whether a card opens a news article or a persistent object.

## Timeline semantics

Timeline entries use type-first hierarchy:

```text
TECHNICAL CHANGE
DRIVER CLAIM
SESSION OBSERVATION
RACE OUTCOME
OUR READ
```

Visual design can differentiate these later, but labels must remain readable without relying only on color.

## Expand/collapse

Use inline expansion for:

- evidence detail,
- long weekend summaries,
- older timeline events,
- source lists.

Avoid sending readers to separate utility pages for small context fragments.

## Back-navigation safety

When a reader moves:

```text
Race Hub → Article → Story
```

context links should make all three objects reachable without browser back-button dependence.

---

# 7. Low-Fidelity Component Inventory

P0 shared components implied by these wireframes:

```text
AppHeader
MobileMenu
RaceContextStrip
ObjectTypeLabel
EntityChip
CanonicalContextLinks
LeadStoryCard
StoryCard
ArticleCard
RaceCard
UpdateCard
ExplainerCard
CurrentStateBlock
WhyItMattersBlock
WhatChangedBlock
WhatToWatchBlock
RaceHeader
SessionTabs
WeekendSummary
StorylineList
Timeline
TimelineItem
EvidenceDetail
TechnicalUpdateCard
TeamCurrentContext
DevelopmentTimeline
ContinueFollowingCard
NewsletterCTA
AppFooter
```

Do not create separate one-off components for every page if the underlying information pattern is the same.

---

# 8. Responsive Breakpoints — Functional Intent

Exact pixel values remain a design-system decision, but behavior should follow three modes.

## Compact

Phone-sized screens.

- single column,
- horizontal session tabs,
- no permanent sidebars,
- compact sticky context,
- cards stack vertically.

## Medium

Tablet / narrow laptop.

- mostly single column,
- selected two-column modules allowed,
- timeline remains primary-column content,
- no dense dashboard treatment.

## Wide

Desktop.

- main editorial column + optional contextual rail,
- cards may appear in 2–3 column groups,
- timeline width remains constrained for readability,
- contextual rail should never contain content essential to understanding the page.

---

# 9. Prototype Test Script

Before visual design, test these tasks with the low-fidelity prototype.

### Task 1

“You opened the site after seeing that Red Bull changed something on the car. Find what changed and why it matters.”

Expected path:

```text
Home → Lead/Developing Story → Story Page
```

### Task 2

“You found an article from Google. Find the full history of the issue discussed in the article.”

Expected path:

```text
Article → Continue Following → Story Page
```

### Task 3

“You want to know what matters before qualifying starts.”

Expected path:

```text
Home → Race Hub → current state / key storylines
```

### Task 4

“You want to see the evidence behind a claim that a new floor was introduced.”

Expected path:

```text
Team or Story → Timeline Event → Evidence Detail
```

### Task 5

“You are on your phone during a race weekend. Find when the next session starts and the most important current storyline.”

Expected result:

Both answers visible in the first screenful of the mobile Race Hub.

---

# 10. Wireframe Acceptance Criteria

The low-fidelity structure is accepted when all of the following are true:

- a reader can distinguish Article, Story and Race Hub objects without explanation,
- every Article has a visible route into persistent context,
- every active Race Hub exposes current state and next session immediately,
- every Story exposes current understanding before historical detail,
- evidence can be inspected without losing the associated Story/Race context,
- mobile Race Hub answers “what happened / what next / what matters” above the fold,
- Team Pages summarize active narratives rather than duplicate article feeds,
- no P0 flow depends on a desktop-only sidebar,
- no critical information is encoded only through color,
- the interface can be implemented from reusable content-object components rather than page-specific one-offs.

---

# 11. Next Design Step

After these flows are accepted, visual design should proceed in this order:

1. content density and spacing system,
2. typography hierarchy,
3. card/object visual grammar,
4. timeline visual language,
5. race-weekend state treatment,
6. responsive component behavior,
7. brand color and decorative layer.

Do not start with a polished homepage mockup. The Story Page and live mobile Race Hub should be solved first because they contain the product's main differentiation and hardest interaction problems.
