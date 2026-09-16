# Visual Design System

## Purpose

This document defines the visual language for the F1 Intelligence public product before high-fidelity mockups or frontend implementation begin.

The product should feel like an **editorial intelligence publication for motorsport**, not an imitation of Formula 1's official visual identity and not a generic sports-news template.

The system is designed around five product requirements:

1. readers must understand information hierarchy very quickly during live race weekends,
2. persistent Story, Race and Team objects must look different from disposable news cards,
3. sourced fact, source claim, observation and editorial interpretation must be visually distinguishable,
4. long-form reading and evidence timelines must remain comfortable on mobile,
5. the visual language must scale from quiet evergreen explainers to high-tempo live-weekend states without becoming sensational.

---

# 1. Visual direction

## Positioning

Target character:

- precise,
- modern,
- technical,
- editorial,
- calm under pressure,
- information-dense without feeling like a trading terminal,
- premium without relying on decorative luxury cues.

Avoid:

- copying F1 broadcast graphics,
- using an F1-like red/black identity as the primary brand shorthand,
- chequered-flag motifs,
- faux carbon-fibre textures,
- heavy gradients everywhere,
- excessive speed lines,
- gaming/esports aesthetics,
- flashing live indicators,
- dense dashboard chrome.

The product should communicate speed through **hierarchy and responsiveness**, not visual noise.

## Core visual idea

The design should combine:

- a restrained editorial base,
- one distinctive cool accent colour,
- semantic race-state colours,
- strong typography,
- thin structural rules,
- compact metadata,
- generous reading whitespace.

The default impression should be closer to a high-quality technical publication than a sports portal.

---

# 2. Colour system

## Base palette

Recommended initial palette:

```text
Ink 950        #111318
Ink 800        #252932
Ink 600        #555C68
Ink 400        #8A919D

Paper 000      #FFFFFF
Paper 050      #F7F8FA
Paper 100      #EEF0F3
Paper 200      #E0E3E8
```

Use `Paper 000` or `Paper 050` as the primary reading surface. Avoid pure-black page backgrounds as the default experience because long evidence-heavy reading is central to the product.

## Brand accent

Recommended launch accent:

```text
Signal Blue 700   #155EEF
Signal Blue 600   #2970FF
Signal Blue 100   #DDE8FF
Signal Blue 050   #F0F5FF
```

Signal Blue is used for:

- primary interactive controls,
- selected tabs,
- canonical-object links,
- active navigation,
- key informational emphasis.

It should not colour every card or heading.

The colour is intentionally distinct from the red-dominant identity strongly associated with official Formula 1 branding.

## Semantic colours

```text
Positive 700    #16794B
Positive 100    #DDF4E8

Attention 700   #A15C00
Attention 100   #FFF0D2

Critical 700    #B42318
Critical 100    #FEE4E2

Info 700        #176B87
Info 100        #DDF3F8
```

Semantic colour is reserved for meaning. It must not be used as decoration.

## Race-state colours

Race state is a product-specific semantic layer.

```text
Upcoming       neutral / Ink 600
Live           Attention 700
Completed      Positive 700
Archived       Ink 400
Delayed        Critical 700
```

`Live` should not mean bright-red flashing UI. A compact amber/orange signal is sufficient.

Example:

```text
● LIVE WEEKEND
Qualifying in 1h 22m
```

The dot may use `Attention 700`; the rest of the module remains neutral.

## Dark mode

Dark mode is not required for MVP launch.

If added later, it should be implemented through semantic tokens rather than custom component-level overrides.

---

# 3. Typography

## Recommended type families

Primary UI/body:

- `Inter`

Editorial/display:

- `Space Grotesk`

Both are widely available, legible and suitable for a technical editorial product.

Fallback stacks:

```css
--font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
--font-display: "Space Grotesk", "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
```

Do not rely on a stylized motorsport typeface for brand identity.

## Type scale

Desktop starting scale:

```text
Display XL     52 / 56    600
Display L      42 / 48    600
H1             34 / 40    600
H2             28 / 34    600
H3             22 / 28    600
Body L         18 / 30    400
Body M         16 / 26    400
Body S         14 / 22    400
Label M        13 / 18    600
Label S        11 / 16    650, uppercase optional
```

Mobile:

```text
H1             30 / 36
H2             24 / 30
H3             20 / 26
Body L         17 / 28
Body M         16 / 25
Body S         14 / 21
```

Large headlines should not consume the full first viewport on mobile.

## Editorial typography rules

Article body:

- ideal line length: 62–74 characters,
- body size: 17–18 px on desktop,
- line height: approximately 1.6,
- paragraph spacing should be visually stronger than sentence spacing,
- bold should be used sparingly,
- inline links should remain identifiable without relying only on colour.

Technical explainers may use slightly wider layouts when diagrams require it, but prose should return to the standard reading column.

---

# 4. Spacing and layout

## Base spacing unit

Use a 4 px base system.

Core spacing tokens:

```text
space-1     4
space-2     8
space-3    12
space-4    16
space-5    20
space-6    24
space-8    32
space-10   40
space-12   48
space-16   64
space-20   80
space-24   96
```

Prefer these values over arbitrary component spacing.

## Page widths

```text
Application max width       1280 px
Editorial content width      760 px
Wide analysis content        960 px
Full-width module            1280 px
```

Desktop outer gutters:

- 32–48 px depending on viewport.

Tablet:

- 24 px.

Mobile:

- 16 px.

## Grid

Desktop:

- 12-column grid,
- 24 px gutters.

Tablet:

- 8 columns.

Mobile:

- 4 columns,
- components usually span all four columns.

The grid should support editorial asymmetry. Not every section needs equally sized cards.

---

# 5. Surfaces, borders and depth

## Border system

Primary structural border:

```text
1 px Paper 200
```

Strong divider:

```text
1 px Ink 950
```

Strong dividers should be rare and primarily used for editorial section boundaries.

## Radius

Recommended:

```text
radius-sm     4 px
radius-md     8 px
radius-lg    12 px
radius-pill  999 px
```

Avoid very rounded cards. The product should feel editorial rather than consumer-app playful.

## Shadows

Cards should normally rely on borders and contrast rather than shadow.

Use subtle elevation only for:

- popovers,
- search overlays,
- mobile sheets,
- evidence detail layers.

Example:

```text
0 8px 24px rgba(17,19,24,0.10)
```

---

# 6. Card grammar

The product has different canonical object types. Their visual grammar must make this visible without requiring users to learn the data model.

## Story Card

Purpose: persistent developing narrative.

Visual characteristics:

- small `STORY` eyebrow,
- status indicator,
- stronger title than metadata,
- latest meaningful change,
- `why it matters` excerpt where space allows,
- last updated time,
- optional entity chips.

Example:

```text
STORY · DEVELOPING

Red Bull rear stability

New floor geometry improved entry behaviour in FP2,
but long-run tyre life remains unresolved.

Updated 38m ago     Red Bull · Azerbaijan
```

Story cards may use a subtle Signal Blue edge or eyebrow to indicate canonical persistent context.

## Article Card

Purpose: time-bound editorial publication.

Visual characteristics:

- publication type,
- headline,
- timestamp,
- standfirst/summary,
- optional image,
- reading time.

Article cards should not use Story-status language.

## Race Card

Purpose: event entry point.

Include:

- event name,
- round,
- date,
- state,
- latest/next session,
- 1–3 key storylines when expanded.

Race-state semantics should be visible but restrained.

## Update Card

Purpose: one concise meaningful change.

Compact layout:

```text
13:42
TECHNICAL
Red Bull revised the floor edge.
[Rear stability →]
```

Do not make update cards look like breaking-news alerts unless the information is genuinely urgent.

## Explainer Card

Purpose: evergreen education.

Should visually feel more durable than news:

- `TECHNICAL EXPLAINER` or `REGULATION GUIDE`,
- direct question/title,
- optional diagram thumbnail,
- no urgency styling.

---

# 7. Chips and metadata

## Entity chip

Examples:

```text
Red Bull
Azerbaijan GP
Rear suspension
```

Default:

- `Paper 100` background,
- Ink text,
- 12–13 px type,
- 24–28 px height.

Clickable chips receive a clear hover/focus treatment.

## Status chip

Story statuses:

```text
Emerging
Developing
Stable
Resolved
```

Use neutral/blue treatment rather than success/error colours. These statuses describe lifecycle, not quality.

## Content-type eyebrow

Examples:

```text
STORY
PRACTICE ANALYSIS
TECHNICAL CHANGE
SOURCE CLAIM
OUR READ
```

Small uppercase labels may be used here because they help scanning.

---

# 8. Evidence and interpretation visual language

This distinction is central to the product.

## Fact / documented event

Visual treatment:

- neutral surface,
- standard Ink text,
- source link visible,
- no special warning treatment.

Label examples:

```text
DOCUMENTED CHANGE
SESSION RESULT
OFFICIAL DOCUMENT
```

## Source claim

Use a quote/source icon and attribution.

```text
SOURCE CLAIM
Max Verstappen · post-FP2 interview
```

Do not visually present a source claim as verified fact merely because the speaker is prominent.

## Observation

Use `Info` semantics.

```text
OBSERVATION
Long-run rear degradation was higher over the final six laps.
```

## Interpretation

Use a visually distinct but calm module.

Recommended treatment:

- `Signal Blue 050` background,
- Signal Blue left rule,
- `OUR READ` or `ANALYSIS` label.

Example:

```text
│ OUR READ
│ The package appears to have moved the balance in a useful direction,
│ but there is not yet enough evidence to conclude that tyre life improved.
```

Interpretation should never share exactly the same visual treatment as sourced fact.

---

# 9. Timeline system

The Story timeline is a signature UI component.

## Desktop timeline

Structure:

```text
DATE / RACE
   │
   ├── 14:22  TECHNICAL CHANGE
   │           Revised floor edge documented
   │           FIA submission · [Evidence]
   │
   ├── 15:05  SOURCE CLAIM
   │           Driver reports improved entry stability
   │           [Source]
   │
   └── 16:10  OUR READ
               Long-run balance appears improved...
```

Rules:

- vertical line is structural, not decorative,
- event icon/marker changes by event type,
- date/race groups should be clear,
- collapsed events show 2–3 lines maximum,
- expansion happens inline or in a detail sheet,
- external source should never be the only way to understand the event.

## Timeline event markers

Recommended marker semantics:

```text
Technical change     square
Source claim         quotation mark / speech icon
Session observation  circle
Race result          flag-like neutral icon, not official F1 asset
Analysis             diamond
Regulation            document icon
```

Do not rely on colour alone to differentiate event types.

## Mobile timeline

Use single-column event blocks with a thin left rail.

The priority is:

1. event type,
2. event title,
3. concise meaning,
4. source/evidence,
5. expandable detail.

Filters may be hidden behind `Filter` on mobile when timeline volume requires them.

---

# 10. Race-state visual language

Race pages must change emphasis with state while retaining the same structure.

## Upcoming

Primary information:

- when the weekend starts,
- key pre-race questions,
- circuit context,
- known technical changes.

Visual tone: neutral.

## Live weekend

Primary information:

- current state,
- latest completed session,
- next session,
- what materially changed.

Use one compact amber live signal.

Do not create a wall of live badges.

## Post-race

Primary information:

- result context,
- what changed in season-long stories,
- What We Learned,
- evidence and technical follow-up.

Use completed state, but do not visually flatten the page into an archive immediately after the race.

## Archived

Primary information:

- durable synthesis,
- key stories,
- session analysis links,
- historical upgrade context.

Urgency UI is removed.

---

# 11. Navigation states

## Header

Desktop target height:

```text
64–72 px
```

Mobile:

```text
56–64 px
```

The header remains understated.

## Current race strip

Maximum height should remain compact enough not to dominate mobile.

Desktop example:

```text
AZERBAIJAN GP · LIVE WEEKEND        Qualifying · 14:00 UTC     Open hub →
```

Mobile:

```text
AZERBAIJAN GP · LIVE
Qualifying in 1h 22m     Open hub →
```

## Sticky context

Permitted sticky elements:

- mobile race session navigation,
- compact Story identity after scrolling,
- header on selected templates.

Avoid stacking multiple sticky bars that reduce viewport height.

---

# 12. Buttons and links

## Primary button

Use sparingly for actions such as:

- newsletter signup,
- opening the main live Race Hub from a prominent event block.

Style:

- Signal Blue background,
- white text,
- 8 px radius,
- minimum 44 px touch height.

## Secondary button

Use outline or neutral surface.

## Editorial links

Most navigation inside content should look like editorial links, not application buttons.

Examples:

```text
Open story →
See full timeline →
Read the analysis →
```

This keeps the publication feel intact.

---

# 13. Images, diagrams and visual evidence

## Photography

Use only properly licensed imagery.

Avoid relying on official F1/team logos or protected visual assets when rights are unclear.

## Technical diagrams

Original diagrams are strategically important because they can:

- increase explainer value,
- visually distinguish the site,
- support search/social distribution,
- avoid dependence on copyrighted photography.

Diagram style:

- neutral technical drawing,
- Paper background,
- Ink outlines,
- Signal Blue callouts,
- minimal labels,
- no faux engineering complexity.

## Charts

Use charts only when the data answers a clear editorial question.

Default chart styling:

- minimal axes,
- direct labels where possible,
- strong annotation,
- no 3D effects,
- no team colour assumptions unless legally and semantically appropriate.

---

# 14. Motion

Motion is functional, not decorative.

Recommended durations:

```text
micro interaction     120–160 ms
menu/sheet            180–240 ms
content expansion     180–240 ms
```

Respect `prefers-reduced-motion`.

No animated racing lines, pulsing cards or constantly moving live graphics.

---

# 15. Responsive principles

## Mobile first

On mobile:

- preserve reading rhythm,
- put current race state before secondary metadata,
- use full-width Story cards,
- collapse secondary card metadata,
- keep evidence source actions touch-friendly,
- avoid horizontal card carousels for primary content,
- use horizontal scrolling only for small controls such as session tabs.

## Desktop

Desktop allows:

- context side rails,
- wider evidence layouts,
- parallel modules,
- richer timeline filtering.

Do not make desktop density the basis of the mobile product.

---

# 16. Accessibility requirements

MVP requirements:

- WCAG AA contrast for text and essential controls,
- visible keyboard focus,
- minimum 44x44 px touch targets for primary mobile controls,
- semantic heading order,
- event types not distinguished by colour alone,
- `aria-current` for active navigation/session states,
- useful alt text for editorial images and diagrams,
- decorative imagery uses empty alt text,
- timeline remains understandable without icons,
- live state does not use flashing animation.

---

# 17. Screen-level visual application

## Story Page

The most important high-fidelity design target.

Visual hierarchy:

```text
Story identity
↓
Current state
↓
What changed
↓
Evidence timeline
↓
What to watch next
```

The timeline should be visually memorable without becoming a dashboard.

## Mobile Race Hub

Second high-fidelity design target.

First viewport should contain:

- race identity,
- state,
- next/latest session,
- session tabs,
- beginning of `What matters now` or weekend summary.

## Home

Home should inherit the visual grammar established by Story and Race pages rather than invent a separate card system.

## Article

Article is intentionally quieter than the Home/Race surfaces. Long-form readability wins over visual density.

---

# 18. Initial CSS token draft

This section is illustrative and can be translated to CSS variables, Tailwind tokens or another implementation system later.

```css
:root {
  --color-ink-950: #111318;
  --color-ink-800: #252932;
  --color-ink-600: #555c68;
  --color-ink-400: #8a919d;

  --color-paper-000: #ffffff;
  --color-paper-050: #f7f8fa;
  --color-paper-100: #eef0f3;
  --color-paper-200: #e0e3e8;

  --color-accent-700: #155eef;
  --color-accent-600: #2970ff;
  --color-accent-100: #dde8ff;
  --color-accent-050: #f0f5ff;

  --color-positive-700: #16794b;
  --color-positive-100: #ddf4e8;
  --color-attention-700: #a15c00;
  --color-attention-100: #fff0d2;
  --color-critical-700: #b42318;
  --color-critical-100: #fee4e2;
  --color-info-700: #176b87;
  --color-info-100: #ddf3f8;

  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
}
```

These are design-direction defaults, not immutable implementation contracts. High-fidelity prototype testing may justify small changes.

---

# 19. High-fidelity prototype order

Do not design every page simultaneously.

Recommended sequence:

### Prototype 1 — Story Page desktop

Validate:

- canonical Story identity,
- fact vs interpretation distinction,
- evidence timeline,
- current-state hierarchy,
- related Race/Team context.

### Prototype 2 — Story Page mobile

Validate:

- timeline density,
- sticky story context,
- evidence expansion,
- readability.

### Prototype 3 — Live Race Hub mobile

Validate:

- race-state hierarchy,
- sticky session tabs,
- `what matters now`,
- latest session analysis,
- Story routing.

### Prototype 4 — Live Race Hub desktop

Validate:

- parallel story/session context,
- technical update module,
- timeline density.

### Prototype 5 — Home

Build using the card grammar proven in the prior prototypes.

### Prototype 6 — Article / Team

Finish the remaining P0 templates after the object grammar is stable.

---

# 20. Design QA checklist

Before a high-fidelity screen is accepted:

- Can a reader identify whether an object is a Story, Article or Race surface?
- Is the most important information visible within the first viewport?
- Is analysis visually distinguishable from documented fact?
- Does semantic colour communicate meaning rather than decoration?
- Is the layout still understandable in grayscale?
- Does the screen work at 375 px width?
- Are primary tap targets at least 44 px?
- Does text remain readable at 200% browser zoom?
- Are source/evidence actions easy to find without dominating the page?
- Does the design avoid dependence on protected F1/team branding?
- Does the user have an obvious next canonical destination?

---

# 21. Decision status

For the first high-fidelity prototypes, use this document as the default design direction.

The following remain intentionally testable rather than permanent:

- exact accent blue,
- Space Grotesk as the display family,
- card border/radius balance,
- desktop timeline width,
- amount of metadata displayed on compact Story cards.

Any change should be evaluated against readability, object distinction and race-weekend scanning speed rather than personal visual preference alone.
