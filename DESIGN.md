# LaunchLens — Design system

Light, restrained, decision-first. Calibre: Linear / Stripe / Notion. The verdict reads
first; everything else recedes. All color is OKLCH; neutrals are tinted toward the brand
hue (285, indigo-violet). Never `#000`/`#fff`.

## Color (OKLCH)
Neutrals (tinted, hue 285):
- bg `oklch(0.985 0.004 285)` · surface `oklch(0.995 0.0015 285)` · panel/2nd-neutral `oklch(0.975 0.005 285)`
- border `oklch(0.92 0.008 285)` · border-strong `oklch(0.88 0.01 285)`
- text `oklch(0.27 0.02 285)` · muted `oklch(0.55 0.018 285)` · faint `oklch(0.68 0.015 285)`

Accent (indigo-violet, actions/selection/focus/live only, ≤10% of surface):
- accent `oklch(0.55 0.19 280)` · accent-strong `oklch(0.50 0.20 280)` · accent-soft `oklch(0.955 0.02 285)`

Semantic (verdict + data roles only):
- GO `oklch(0.58 0.15 150)` · NO-GO `oklch(0.56 0.20 25)` · NICHE `oklch(0.66 0.13 75)`
- demand (blue) `oklch(0.55 0.16 250)` · supply (amber) `oklch(0.60 0.15 55)`
- each with a `-bg` (~0.96 L, low chroma) and `-bd` (~0.86 L) tint.

## Typography
- Family: `"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` (one family).
- Fixed rem scale, ratio ~1.2: 0.75 / 0.8125 / 0.9375(base) / 1.0 / 1.25 / 1.5 / 1.9 rem.
- Weights: 400 body, 600 labels/headings, 800 verdict word / brand.
- Prose ≤ 72ch. No display fonts in UI; no gradient text.

## Elevation
Three soft, hue-tinted steps (never harsh black):
- sm `0 1px 2px oklch(0.45 0.03 285 / .06)`
- md `0 6px 20px oklch(0.45 0.05 285 / .08)`
- lg `0 16px 40px oklch(0.45 0.06 285 / .14)` (hover only)

## Motion
- 150–220 ms, `cubic-bezier(0.22, 1, 0.36, 1)` (ease-out-quint). State + reveal only.
- Animate transform/opacity only. No bounce, no orchestrated page loads.

## Components
- **Verdict card** — the hero. Tinted semantic header (GO/NO-GO/NICHE), then labelled rows
  (Demand / Price band / Differentiation / Positioning), optional overall line.
- **Product card** — image, title, price, stars, reviews; hover lift (transform only).
- **Message** — user = solid accent bubble; assistant = surface card with full border.
- **Sidebar / rail** — 2nd-neutral panels (solid, no glass), accent-soft for the active chat.
- **Inputs/buttons** — full borders, accent focus ring; solid accent primary (no decorative gradient).

## Bans (enforced)
No gradient text, no decorative glassmorphism, no side-stripe borders, no em dashes, no
hero-metric template, no `#000`/`#fff`.
