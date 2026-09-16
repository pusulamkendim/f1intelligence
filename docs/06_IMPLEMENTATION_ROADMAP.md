# Implementation Roadmap

## Delivery principle

Build the smallest system that proves the editorial/product thesis before investing in a large autonomous ingestion or publishing platform.

The roadmap therefore starts with content structure and public page templates, then adds automation where repeated work creates clear leverage.

## Phase 0 — Product foundation

Goal: freeze enough product language that implementation does not encode hidden assumptions.

Deliverables:

- product vision
- information architecture
- Story/Evidence model
- source taxonomy
- editorial quality rules
- initial legal/IP checklist
- initial content portfolio

Exit criteria:

- we can explain what a Story is versus an Article,
- we know the first public page types,
- we know what information every source record must preserve,
- we know which decisions still require validation.

## Phase 1 — Public MVP skeleton

Goal: make the intended product navigable before building sophisticated automation.

Required public pages:

- Home
- Race Hub
- Article
- Story
- Team

Required internal capabilities:

- basic CMS/editorial interface
- create/edit Story
- create/edit Evidence reference
- attach Article to Story/Race/Team
- publish/update pages
- internal linking support

Do not build advanced recommendation systems or autonomous publishing yet.

Exit criteria:

- one complete race weekend can be represented manually,
- a Story can persist across multiple articles,
- users can move from current coverage into historical context.

## Phase 2 — Upgrade tracker + evergreen layer

Goal: prove that persistent structured pages have standalone value.

Deliverables:

- Team upgrade tracker
- Technical Explainer template
- Regulation Explainer template
- season/team taxonomy
- stronger internal linking
- sitemap and search metadata

Seed content should include a small number of genuinely useful pages rather than a large empty taxonomy.

Exit criteria:

- at least one team has a coherent season development timeline,
- race articles can link naturally into technical explanations,
- persistent pages can be updated without creating duplicate URLs.

## Phase 3 — Source ingestion MVP

Goal: reduce manual monitoring cost.

Automate:

- source retrieval for selected approved sources,
- timestamp/provenance capture,
- deduplication,
- entity extraction,
- raw-source storage/reference.

Keep source coverage intentionally narrow at first. Reliability and provenance are more important than the number of feeds.

Exit criteria:

- incoming material can be searched by race/team/driver/topic,
- duplicated source items are suppressed,
- raw evidence remains traceable.

## Phase 4 — Story clustering and Analysis Briefs

Goal: turn source monitoring into editorial intelligence.

Deliverables:

- semantic Story matching
- candidate Story creation
- evidence attachment
- timeline generation
- What changed / Why it matters / What to watch next fields
- model-generated Analysis Brief
- editor approval workflow

No unattended public publishing is required.

Exit criteria:

- the system correctly routes a meaningful share of new evidence into existing Stories,
- editors save measurable research time,
- contradictory evidence is visible rather than silently collapsed.

## Phase 5 — Race-weekend operating system

Goal: make the workflow fast enough for live editorial use.

Deliverables:

- race-weekend dashboard
- active Story list
- session-specific evidence queue
- race-hub update controls
- upgrade-entry workflow
- post-session brief generation
- "What we learned" synthesis workspace

Exit criteria:

- one editor can operate a race weekend without manually reconstructing context from many tabs,
- active stories remain synchronized with public Race/Story pages.

## Phase 6 — Growth instrumentation

Goal: understand which content creates durable audience value.

Deliverables:

- analytics
- Search Console integration/workflow
- newsletter attribution
- internal-click tracking
- page-age traffic reporting
- returning-user reporting
- content refresh queue

Important reports:

- persistent vs current-content traffic
- Article -> Story navigation rate
- Race Hub repeat visits
- search impressions by page type
- newsletter conversions by landing page

Exit criteria:

- roadmap decisions can be based on real reader behavior rather than assumptions.

## Phase 7 — Monetization

Goal: monetize without degrading the core reading experience.

Sequence:

1. light display advertising
2. optimize placement based on real RPM/viewability data
3. selected affiliates
4. newsletter sponsorship
5. direct/premium products if demand exists

Advertising should not drive the information architecture.

## Technical decisions intentionally deferred

Do not lock these until the MVP requirements are sufficiently concrete:

- web framework
- CMS implementation
- relational vs hybrid search architecture details
- vector database choice
- queue/orchestration framework
- LLM vendor/model routing
- hosting topology

Likely requirements are already visible — structured relational data, full-text/semantic retrieval, scheduled ingestion and a fast content frontend — but vendor selection should be a separate architecture decision.

## Suggested first implementation backlog

### Product

- [ ] finalise MVP navigation
- [ ] wireframe Home
- [ ] wireframe Race Hub
- [ ] wireframe Story Page
- [ ] wireframe Team Page
- [ ] wireframe Article Page
- [ ] define editorial roles/statuses

### Data

- [ ] convert conceptual Story model into database-level schema proposal
- [ ] define Evidence provenance fields
- [ ] define Race/Team identifiers
- [ ] define Publication relationships
- [ ] define upgrade taxonomy

### Editorial

- [ ] create source trust/provenance policy
- [ ] define correction/update policy
- [ ] define article templates
- [ ] define race-weekend operating checklist
- [ ] define rights/IP checklist

### Growth

- [ ] select first 15–25 evergreen topics
- [ ] select first team upgrade tracker
- [ ] define newsletter MVP
- [ ] define analytics events before launch

## Immediate next decision

The next design task should be **wireframes and data requirements for the five P0 screens**:

1. Home
2. Race Hub
3. Story Page
4. Team Page
5. Article Page

For each screen, specify:

- user question it answers,
- modules/components,
- required data fields,
- source Story/Evidence relationships,
- mobile behavior,
- SEO requirements,
- which fields are manual vs automatically generated.

Once those are defined, a technical stack and database schema can be selected against concrete requirements rather than guesswork.
