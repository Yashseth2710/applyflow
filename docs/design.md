# Design

The rules the interface is built on, and the reasoning behind each. Anything on
screen that contradicts this file is drift: either change the element or change
this file, deliberately, and say which.

Kept in `docs/` beside the API and schema notes rather than at the repo root,
because it is the same kind of document — a description of how one part of the
system works.

---

## The product, and what each surface is for

ApplyFlow tracks a job search: applications, the resume version sent with each
one, interviews, and what needs doing next. One person, their own data, used in
bursts over the weeks a search lasts.

Most of the app is **working software**, and working software has different
obligations from a marketing page. Scanability, consistent placement and quiet
surfaces beat expression. Someone opening the dashboard on a Tuesday morning
wants to know what needs doing, not to be impressed.

| Surface | Job | What that means here |
|---|---|---|
| `/` | Persuade | The only place with display-scale type and a lifted object. Show the product rather than describing it. |
| `/login`, `/register`, reset flow | Persuade, briefly | The brand panel is the one large colour field in the app. The form half stays plain. |
| Dashboard, applications, board, resumes, analytics | Operate | Density over drama. The page answers a question and gets out of the way. |
| Settings | Operate, quietest | Nothing here should attract attention. Destructive actions are the exception. |

Applying landing-page energy to a working screen is the failure mode to watch
for. It is how the dashboard ended up with four hero-metric tiles.

---

## Type

Two families, chosen for stated reasons rather than defaults.

**Fraunces** — display. An old-style serif with an optical-size axis, so the
serifs thin as the type grows instead of the 14px cut being scaled up. It gives
the product a voice in the two seconds before anyone reads a word. Chosen partly
for what it is not: Inter, Geist, Space Grotesk and Instrument Serif appear on
enough sites that they have stopped meaning anything, and Geist in particular is
the Next.js scaffold default — the single clearest signal that nobody chose.

**Public Sans** — body and all UI. Humanist, legible at 12px, and with real
tabular figures, which this app leans on constantly: every count, date and
pipeline number has to align in a column.

**Geist Mono** stays for the rare monospace need.

Both faces are fetched at build time and served from our own origin. This is not
incidental — the CSP in `next.config.ts` has no `font-src` exception for a third
party, and adding one to load a font would be the wrong trade.

### Where the serif is allowed

The serif is a **display** voice, not a heading voice. It goes on:

- `h1` on every page, via `class="display"`
- the landing hero and the auth brand panel

It never goes on a section label, a card title, or anything at 14px or below,
where serifs turn to mush and look like a mistake.

Everything else — `h2`, `h3`, table headers, card titles — is Public Sans, and
earns its rank from weight and colour instead of a second typeface.

### The scale

Defined in `globals.css` under `@theme`. Steps are roughly 1.25 apart, wide
enough that two adjacent levels are never mistaken for each other.

| Token | Size | Used for |
|---|---|---|
| `--text-display` | 3.25rem | Landing hero only |
| `--text-title` | 2rem | Auth panel headline |
| `--text-section` | 1.25rem | Sub-headings inside a page |
| `--text-label` | 0.75rem | The `.eyebrow` section label |

Page titles sit at `1.75rem` set inline. Body is 16px. **Nothing functional
below 12px**, table cells and labels included.

There is deliberately no blanket `h1, h2, h3, h4` rule. There used to be, and it
gave four levels the same face and tracking — so rank depended on size alone,
and the sizes sat within a few pixels of each other. Everything read as equally
important, which is the same as nothing being important.

### Spacing of letters and lines

- Body leading 1.5–1.7. Headings tighten as they grow, down to 1.04 at display.
- Tracking floor `-0.028em`. Crushing type tighter to look designed costs
  legibility.
- Wide tracking (`0.07em`) is only ever on `.eyebrow`: short, uppercase, small.
- Never set a paragraph in caps. Word shape is how people read.
- Prose containers get `.measure` (68ch), inside the 65–75 characters the eye
  can track without losing the return sweep.

### No kicker

A tracked uppercase label sitting *above* a heading is banned outright. No
version of the brief earns it back — the heading carries its own weight.

`.eyebrow` is not a kicker. It is the section's own `h2`, naming a region that is
not competing for attention. The distinction is whether another heading follows
it.

---

## Colour

Two families, deliberately kept apart:

- **Brand violet** drives interactive things only: buttons, links, focus rings,
  the current nav item.
- **Status and stage colours** describe data, and skip the 275–310 hue band
  entirely so a status can never be mistaken for something clickable.

That separation is the whole colour system. If the accent ever appears meaning
something other than "this is interactive or current", one of the two uses is
wrong.

**Neutrals carry a trace of violet chroma** — around 0.01 or less. Invisible as
colour, visible as intent. Pure `oklch(x 0 0)` grey is what a screen looks like
when nobody chose. Above ~0.01 it stops being a trace and starts being beige,
which is its own tell.

Everything is OKLCH, which is perceptually uniform: two hues at the same
lightness genuinely look equally bright. That matters for the twelve stage
colours, which have to sit beside each other on the board without any one
jumping out.

**Every colour is a token with a job.** A raw value at a call site is a colour
nobody chose. Add it to `globals.css` first.

### Ink variants

`--success-ink`, `--danger-ink`, `--stage-*-ink` and friends exist because a
fill and a letterform have different obligations. A bar only has to be
distinguishable; text has to clear 4.5:1. The stage fills read between 2.6:1 and
3.5:1 as text on their own tint in light mode. Darkening the fills would have
muted every chart and dot in the app, so the ink is a separate token and each
value is the lightest that clears 4.6:1 on the tint it actually sits on.

Use the ink token whenever a stage or status colour is a letterform.

### Contrast

4.5:1 for body and placeholder text, 3:1 for large text, **in both themes**.
This is a design constraint, not a checklist item at the end — it is why the ink
tokens exist at all.

Grey text on a coloured ground almost always fails. Tint the secondary text from
the ground's own hue instead.

---

## Shape and depth

**An edge or an elevation, never both.** A hairline border together with a
diffuse shadow on the same element is two mechanisms saying "this is a separate
thing", applied at once because neither was chosen. It is also one of the most
recognisable generated-UI signatures.

A shadow additionally claims the element is physically lifted off the page, and
a panel that just sits there is not lifted.

`Panel` (`components/ui/panel.tsx`) encodes this:

| Level | Treatment | When |
|---|---|---|
| `flat` | Hairline border, card ground | The default. Almost every region. |
| `raised` | Shadow, **no** border | Genuinely lifted only: dialogs, menus, mid-drag, the product still on the landing page. |
| `sunken` | Soft border, recessed ground | Inert or awaiting something: empty states, read-only extracts. |

Buttons take the same deal from the other side: the filled variant has a shadow
and a transparent border, the outline variant has a border and no shadow.

Fields invert it deliberately — a 1px **inset** shadow, so an input reads as a
slot cut into the page rather than another rectangle on it. That is what tells
you at a glance which things you press and which you type into.

**Shadows always carry an offset and a soft blur**, in two layers: a tight one
for the contact edge, a wide one for the ambient falloff. A zero-offset ring is
a halo, not depth. They are tinted with the brand hue in light mode, because a
neutral shadow over faintly violet neutrals goes muddy at the edges.

### Radius

`--radius` is 0.625rem (10px); cards land at 14px via `--radius-xl`. Past about
16px everything rounds into the same soft blob. Full-pill is for tags, badges
and avatars only.

### Banned furniture

Each of these is a default reached for when nobody decided:

- **Icon tiles** — a small accent-tinted rounded square holding a glyph, above
  or beside a heading. Icons sit inline, in the line of the thing they label, in
  a muted colour, helping someone find a row rather than decorating one.
- **Side-tab accent borders** — a thick coloured border on one edge of a card.
  It fights the corner radius besides.
- **Nested cards.** Separate with spacing, a rule, or type weight. `flat` exists
  so the inner thing needs no second border.
- **Boxed list rows.** Rows in a list are siblings; a hairline between them says
  so more quietly than forty borders. A box is earned only when a row is
  selectable and must show a chosen state.
- **The hero-metric block** — big number, small label, supporting stats, accent.
- **Gradient text**, decorative glass and blur, radial hazes behind a section,
  grid-line backgrounds, and coloured glows behind cards.
- **Unicode glyphs standing in for icons** (`→`, `←`, `↗`). A text arrow
  inherits the body font's idea of an arrow, sits on the baseline instead of
  optically centred, and is announced as "rightwards arrow". Use lucide.

---

## Layout

**Range left.** A centred headline over a centred paragraph over two centred
buttons is the shape every generated landing page arrives in, and it reads worse
regardless — the eye has to hunt for the start of each line. Centre a single
short line, or nothing.

**Break the identical grid.** Same-sized cards with an icon, a heading and a
line of text, repeated three or six times, is the default homepage. A ruled
index or a two-column definition list says the same thing with less furniture.

**Spacing has rhythm**: tight within a group, generous between sections. One
value everywhere is the absence of a system. A heading always gets more space
above it than below, so it reads as belonging to what follows.

Minimum 12–16px padding inside any bordered or tinted container, and body text
never touches the viewport edge.

---

## Motion

- Animate `transform` and `opacity`. Layout properties are the exception, not
  the habit, and the pipeline bars animating `width` on a data change are the
  one deliberate case.
- Ease-out, `cubic-bezier(0.2, 0, 0, 1)`, 150ms for interface feedback. No
  bounce, no elastic.
- **Nothing animates that is not actually changing.** No pulsing status dots —
  a decorative pulse makes static data look live. Skeletons pulse because data
  genuinely is in flight.
- Content is visible at rest. No reveal-on-scroll that leaves the page blank if
  a script fails.
- `prefers-reduced-motion` is honoured globally in `globals.css`. Nobody who has
  asked the OS to stop animating things should have to ask this app separately.

---

## Copy

- Name what the product literally does. Banned: *streamline, empower,
  supercharge, seamless, world-class, enterprise-grade, unlock, elevate,
  powerful.*
- Buttons name the outcome. "Get started", "Learn more" and "Continue" name
  nothing. "Create account", "Add application", "Send reset link" do.
- Headlines say something specific enough that they could not sit on a
  competitor's page unchanged.
- At most one em-dash per block of prose, and prefer a full stop. Strings of
  em-dash-joined clauses have a recognisable cadence.
- The manufactured-contrast aphorism — "Not X. Just Y." — at most once in the
  product. Once is a voice; three times is a tell.
- Errors name the problem *and* the recovery.
- Typographic apostrophes (`’`), never `&apos;`. The straight quote is a
  vertical tick, and at display size in a serif it is glaring.

---

## States

A screen is not finished when the happy path looks good.

- **Loading** — skeletons shaped like the content that replaces them, so nothing
  jumps when the data lands.
- **Empty** — and it must know *which* empty. "You have never added an
  application" and "your filter matched nothing" are different situations, and
  offering the first message to someone with twenty applications reads as an app
  not paying attention.
- **Error** — written for a person, never a stack trace, always with a way
  forward.
- **Long content** — the longest plausible job title, the largest number, a
  filename that does not wrap.

---

## Semantics and accessibility

These are design constraints, not a separate audit.

- Anything that navigates is an `<a>`; anything that acts is a `<button>`. A
  button component rendered "as" a link announces `role="button"`, which lies
  about what happens next. Use `buttonVariants()` on a `Link`, or Base UI's
  `render` prop.
- Heading levels never skip.
- Decorative icons get `aria-hidden`. Icon-only controls get an `aria-label`
  **and** a visible tooltip — the label is for a screen reader, the tooltip is
  for a sighted person who does not recognise the glyph.
- Focus is always visible. Handled once, globally, on `:focus-visible`.
- Native controls follow the theme via `color-scheme`, or a dark-mode `<select>`
  popup keeps its white ground and inherits light text.

---

## Before shipping a screen

1. Any font, colour, radius or size not in this file?
2. Any icon tile, side-tab border, nested card, boxed list row, decorative
   gradient, glow, or border-plus-shadow?
3. Is the type scale doing real work, or is everything within 2px of everything
   else?
4. Does the accent mean exactly one thing on this screen?
5. Could someone who actually uses this product have written the copy? Count the
   em-dashes.
6. Do loading, empty and error states exist, and does empty know which kind it
   is?
7. Longest line under ~75 characters? Contrast passing in **both** themes?
8. Is anything animated that is not actually changing?

Prefer removing to adding. Most of these problems are furniture, and the fix is
usually a rule, a weight change, or nothing at all.
