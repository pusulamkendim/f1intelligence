# F1 Intelligence Documentation

This directory is the living product and strategy knowledge base for the project.

## Documents

1. [`01_PRODUCT_VISION.md`](01_PRODUCT_VISION.md) — product positioning, target user, product principles and differentiation.
2. [`02_INFORMATION_ARCHITECTURE.md`](02_INFORMATION_ARCHITECTURE.md) — site structure, page types and MVP screen definitions.
3. [`03_STORY_AND_CONTENT_MODEL.md`](03_STORY_AND_CONTENT_MODEL.md) — canonical Story Object, evidence, entities, timelines and publication relationships.
4. [`04_CONTENT_PIPELINE.md`](04_CONTENT_PIPELINE.md) — source ingestion, clustering, analysis, editorial review and publishing workflow.
5. [`05_SEO_MONETIZATION_GROWTH.md`](05_SEO_MONETIZATION_GROWTH.md) — traffic model, content portfolio, monetization logic and growth KPIs.
6. [`06_IMPLEMENTATION_ROADMAP.md`](06_IMPLEMENTATION_ROADMAP.md) — staged MVP delivery plan and decision gates.
7. [`07_UI_SPECIFICATION.md`](07_UI_SPECIFICATION.md) — implementation-ready P0 screen structure, shared components, mobile behavior, interaction rules and acceptance criteria.
8. [`08_LOFI_WIREFRAMES.md`](08_LOFI_WIREFRAMES.md) — low-fidelity wireframes for the five critical MVP flows, responsive behavior, component inventory and prototype acceptance criteria.
9. [`09_VISUAL_DESIGN_SYSTEM.md`](09_VISUAL_DESIGN_SYSTEM.md) — visual direction, colour and typography tokens, spacing/grid, card grammar, evidence/timeline language, race states, accessibility and high-fidelity prototype order.
10. [`10_MEDIA_ASSET_AND_IMAGE_PIPELINE.md`](10_MEDIA_ASSET_AND_IMAGE_PIPELINE.md) — media sourcing hierarchy, rights validation, MediaAsset model, Wikimedia/photographer/stock workflows, attribution, derivatives, deduplication, storage, AI-image policy and MVP acceptance criteria.
11. [`11_MEDIA_DISCOVERY_TECHNICAL_SPEC.md`](11_MEDIA_DISCOVERY_TECHNICAL_SPEC.md) — implementation-ready Wikimedia Commons discovery architecture, API strategy, rights evaluator, candidate ranking, persistence, approval transaction, security, observability, testing and delivery phases.
12. [`12_TECH_STACK_DATABASE_AND_REPO.md`](12_TECH_STACK_DATABASE_AND_REPO.md) — selected web/API stack, service boundaries, initial PostgreSQL schema, repository layout, deployment direction and vertical-slice implementation order.
13. [`13_OFFICIAL_SOURCE_INGESTION.md`](13_OFFICIAL_SOURCE_INGESTION.md) — FIA RSS ingestion, deterministic Story matching, deduplication, Evidence attachment, failure handling and MVP acceptance criteria.
14. [`14_LOCAL_PORT_CONFIGURATION.md`](14_LOCAL_PORT_CONFIGURATION.md) — developer-machine port overrides, including Redis host-port configuration without modifying tracked Compose files.\n15. [`media-assets.md`](media-assets.md) — implemented rights-aware media registry, Story image candidates, F1-Fansite discovery, storytelling roles and R2-ready storage boundary.

## Documentation rules

- Product decisions should be recorded here before they become hidden assumptions in code.
- Time-sensitive assumptions should be labelled with a date.
- The Story Object is the canonical knowledge model; article pages are outputs, not the source of truth.
- We do not publish large volumes of lightly rewritten source material. Automation should improve research, linkage, verification and editorial speed.
- New architecture decisions should explain which product requirement they serve.
