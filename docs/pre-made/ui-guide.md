# UI Guide — CWA Ship Karachi 2026

**Purpose:** A professional, minimal, aesthetically considered UI — built on Material Design 3's structural system, with just enough left open to match the emotional tone of whatever problem we're handed. UI work only starts once the UX guide's journey map is locked.

## Stack

- **React + Vite** — standard, fast, widely used in production. Skip Create React App (deprecated).
- **Tailwind CSS** — utility classes mapped directly to the design tokens below, so nobody hardcodes a random spacing or color value.
- **TypeScript (recommended, not mandatory)** — pairs with the contract-first architecture: generate types from the DRF OpenAPI schema so frontend and backend can't silently drift apart on shape. Drop it if time gets genuinely tight.
- **Serving:** built as static assets, served by Nginx at `/` alongside the API routes — see `architecture.md` §3.4. One origin, no CORS, one deploy command.

## The Split: Locked Structure vs. Adaptive Emotion

Two layers. The **structural system** is fixed now and never changes, regardless of theme. The **emotional layer** — the specific values that make the same structure feel calm, energetic, serious, or playful — is chosen in the first minutes after kickoff, once we know what we're building.

### Locked Now: Structural System (Material Design 3-based)

- **Spacing scale:** 4px base unit — 4, 8, 12, 16, 24, 32, 48, 64. Every margin/padding value comes from this scale. No arbitrary pixel values.
- **Type scale:** M3's scale steps — Display, Headline, Title, Body, Label, each with a small/medium/large variant. The *ratios* are fixed; which font fills them is decided later.
- **Color roles, not colors:** define slots — `primary`, `secondary`, `tertiary`, `surface`, `background`, `error`, plus `-on` variants for text/icons on top of each. Which actual hues fill these roles is decided later; the *role system* (what each color is used for and where) is fixed now.
- **Component states:** every interactive component (button, input, card) must define default, hover, active, disabled, loading, and error states before it's considered done. No component ships with only its "happy path" state styled.
- **Elevation:** used sparingly — M3-style subtle shadows to indicate layering (modals, dropdowns), never as decoration.
- **Iconography:** one icon set for the entire product (Material Symbols is the natural pairing with M3). Never mix icon styles.
- **Accessibility minimums:** ≥4.5:1 text contrast, ≥44px tap targets, visible focus states. Non-negotiable.

### What to Avoid (always, regardless of theme)

- Gradients as a primary design element (a subtle one on a single accent is fine; gradients-as-backgrounds are not)
- Long or complex animations — transitions ≤200ms, simple fade/slide only, never decorative motion
- More than two accent colors in active use at once
- Decorative-only imagery or illustration that doesn't support the journey
- Skeuomorphism, heavy drop shadows, busy textures

### Decided at Kickoff: The Emotional Layer (~5–10 min)

Once the theme is known, fill in the structural system's open slots to match the tone the problem calls for:

- **Font pairing:** one font for Display/Headline, optionally a second for Body if it earns its place. Choose from Google Fonts for fast integration.
- **Seed color:** pick one seed hue and run it through the M3 tonal palette approach to generate the full role-based palette in minutes, not from scratch.
- **Spacing density:** compact (efficient, dense — productivity/utility tools) vs. comfortable (airy, generous — trust/care-oriented products) — still using the locked 4px scale, just choosing which steps dominate.
- **One signature minor element:** a single consistent detail (corner radius amount, a distinctive accent shape, one custom icon treatment) — exactly one, not a collection.

**Quick tone lookup**, to make this a 5-minute decision instead of a debate:

| Problem tone | Font feel | Color direction | Spacing |
|---|---|---|---|
| Trust/care (health, finance, civic) | Clean, rounded sans | Cool blues/greens, moderate saturation | Comfortable |
| Productivity/utility (tools, dashboards) | Crisp, neutral sans | Cooler neutrals, one confident accent | Compact |
| Energetic/social (community, creative) | Slightly warmer/rounder sans | Warmer accent, higher contrast | Comfortable |

## Component Standards

- **Forms:** inline validation, clear error text tied to the specific field, disabled submit state while a request is in flight.
- **Buttons:** one visual style for primary actions, one for secondary — never more than two button styles on a single screen.
- **Navigation:** reflects the locked journey map directly — no navigation items that don't correspond to a step in it.
- **Loading/empty/error states:** every screen that fetches data must design all three, not just the populated state. This maps directly to the response envelope in `architecture.md`.

## Implementation Notes

- Tailwind's config (`tailwind.config.js`) should extend the theme with the design tokens above — spacing scale, color roles as CSS variables, font family variables — rather than components reaching for arbitrary Tailwind values. This is the UI equivalent of the coding guidelines' "no magic numbers, use the standard pattern."
- Once the emotional-layer decisions are made at kickoff, they go into the Tailwind config once, in one place — every component automatically inherits them.
