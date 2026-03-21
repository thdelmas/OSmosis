# Osmosis Visual Identity

## Logo concept

The Osmosis mark depicts **Moses as a microchip/kernel**, holding a staff tipped with a terminal prompt (`>`), parting the way to device freedom. The golden circuit-board figure bridges the biblical metaphor with the digital reality — a kernel leading hardware out of locked-down ecosystems.

The logo file lives at `frontend/public/logo.png` (transparent background). Use it as the app icon, favicon, and header brand mark.

**Wordmark:** "Osmosis" set in the UI system font stack or, where a brand font is needed, in **Inter** (open source, variable weight). The "**OS**" prefix is rendered in accent color or bold weight to reinforce the triple meaning:

- **OS** — operating system
- **Osmosis** — flowing into any device
- **Moses** — leading hardware to freedom

## CSS variable architecture

Theme colors are decoupled from layout logic using `[data-theme]` selectors. Structural tokens (`--radius-card`, `--radius-btn`, `--transition-fast`) live in `:root` and never change between themes. Color tokens are scoped per theme block so toggling `data-theme` on `<html>` switches the entire palette without touching layout.

```css
:root {
  /* Spacing & Shape */
  --radius-card: 12px;
  --radius-btn: 8px;
  --radius-pill: 20px;
  --font-scale: 1;

  /* Motion */
  --transition-fast: 0.15s ease;
  --transition-med: 0.3s ease;
}

[data-theme="dark"]  { /* dark color tokens */  }
[data-theme="light"] { /* light color tokens */ }
```

The `.theme-light` class is kept as a fallback alias for `[data-theme="light"]`.

## Color palette

The palette shifts from the old electric blue to **Osmosis Teal** — an aqua-teal accent that evokes water, flow, and membranes. The teal sits between blue and green on the color wheel, distinguishing Osmosis from generic blue-themed tools while reinforcing the osmosis metaphor.

### Dark theme (primary)

| Role | CSS variable | Hex | Usage |
|------|-------------|-----|-------|
| Background | `--bg` | `#0b1015` | Page background — deep blue-black, like deep water |
| Surface | `--bg-card` | `#141c24` | Cards, panels, modals |
| Surface hover | `--bg-hover` | `#1c2a36` | Interactive hover states |
| Border | `--border` | `#2a3a4a` | Dividers, card edges |
| Text | `--text` | `#e8eef4` | Primary body text |
| Text dim | `--text-dim` | `#8a9bb0` | Secondary/muted text |
| **Accent (Osmosis Teal)** | `--accent` | `#36d8b7` | Links, active elements, brand color |
| Accent hover | `--accent-hover` | `#5ee8cc` | Hover state for accent |
| Success (Mint) | `--green` | `#3ee8a8` | Confirmations, completed states |
| Warning (Amber) | `--yellow` | `#fcc53a` | Caution, missing dependencies |
| Error (Coral) | `--red` | `#ff8585` | Failures, destructive actions |
| Info (Cyan) | `--cyan` | `#33c4e0` | UI informational elements |

### Light theme

| Role | CSS variable | Hex |
|------|-------------|-----|
| Background | `--bg` | `#f0f4f7` |
| Surface | `--bg-card` | `#ffffff` |
| Surface hover | `--bg-hover` | `#e4ecf2` |
| Border | `--border` | `#c0d0dd` |
| Text | `--text` | `#141c24` |
| Text dim | `--text-dim` | `#4a6078` |
| Accent | `--accent` | `#1a9e88` |
| Accent hover | `--accent-hover` | `#148572` |
| Success | `--green` | `#1ba870` |
| Warning | `--yellow` | `#c89200` |
| Error | `--red` | `#d44040` |
| Info | `--cyan` | `#0e8faa` |

### Terminal sub-palette

The terminal uses a dedicated set of color tokens (`--term-*`) with higher saturation than their UI counterparts. This ensures legibility when reading dense log output at small font sizes against both dark and light terminal backgrounds.

| Role | Dark hex | Light hex | CSS variable |
|------|----------|-----------|-------------|
| Background | `#080c10` | `#edf0f4` | `--term-bg` |
| Command | `#36d8d8` | `#0a6e6e` | `--term-cmd` |
| Success | `#4dffc0` | `#127a52` | `--term-success` |
| Error | `#ff9494` | `#c03030` | `--term-error` |
| Warning | `#ffd04a` | `#8a6800` | `--term-warn` |
| Info | `#7a8ea5` | `#4a6078` | `--term-info` |

### Usage rules

- **Osmosis Teal** is the primary brand color. Use it for the wordmark accent, primary buttons, active states, and links.
- **Mint** signals success and completion — never use it for decoration. Note: teal and mint are adjacent; ensure they are never used in the same context (buttons vs. status).
- **Coral** and **Amber** are reserved for error and warning states. Do not mix them.
- In both themes, text on accent backgrounds must be `#ffffff` (dark theme) or `#0b1015` (light theme) — whichever meets contrast.
- Maintain a minimum contrast ratio of **4.5:1** for body text and **3:1** for large text (WCAG AA).
- Terminal text must meet **4.5:1** against `--term-bg` — use the `--term-*` tokens, not the UI palette.

## Typography

| Element | Font | Weight | Size |
|---------|------|--------|------|
| Body | System stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`) | 400 | `1rem` (scales with `--font-scale`) |
| Headings | System stack | 600–700 | `1.05rem`–`1.8rem` |
| Code / terminal | `'JetBrains Mono', 'Fira Code', 'Consolas', monospace` | 400 | `0.85rem` |
| Labels / section titles | System stack | 600 | `0.9rem`, uppercase, `0.08em` tracking |
| Status pills | System stack | 500 | `0.8rem` |

The `--font-scale` CSS variable supports user-selectable font sizes (`1`, `1.2`, `1.4`). All type sizes multiply against it.

## Spacing and shape

- **Border radius:** `--radius-card` (`12px`) for cards and modals, `--radius-btn` (`8px`) for buttons and inputs, `--radius-pill` (`20px`) for pills, full round for dots and avatars.
- **Shadow (dark):** `0 2px 12px rgba(0,0,0,0.35)` — used sparingly on hover and elevated elements.
- **Shadow (light):** `0 2px 12px rgba(0,0,0,0.08)`.
- **Grid:** Cards use `repeat(auto-fill, minmax(320px, 1fr))` with `1rem` gap.
- **Max content width:** `1100px`, centered.
- **Touch targets:** Minimum `44px` height/width on all interactive elements (WCAG).

## Iconography

Use **emoji** for card icons and illustrations — no icon font dependency. Keep emoji usage functional (representing device types, actions, status), not decorative.

Examples from the UI: device icons, action cards, progress indicators.

## Motion

- **Fast transitions** (`--transition-fast`: `0.15s ease`): color, border, and background changes on buttons, cards, and inputs.
- **Medium transitions** (`--transition-med`: `0.3s ease`): progress dots, help panel expand/collapse.
- **Animations:** `fadeIn` at `0.3s ease` with a `12px` upward translate for wizard steps.
- **Hover transforms:** Goal cards use `translateY(-2px)` with a synchronized shadow growth (`cubic-bezier(0.22, 1, 0.36, 1)` easing) — the shadow and lift arrive together so the effect feels elevated rather than bouncy.
- **Reduced motion:** The stylesheet includes a `prefers-reduced-motion: reduce` media query that collapses all animations and transitions to near-zero duration. This is not optional — it ships today.

## Tone of the brand

The visual identity reflects the manifesto:

- **Dark-first** — we default to a dark interface because our users are technical and often work in low-light environments. Light theme exists as an option, never the default.
- **Fluid** — the osmosis metaphor carries through: OS flows into devices like water through a membrane. Transitions are smooth, not jarring.
- **Transparent** — terminal output is shown directly, not hidden behind spinners. The UI trusts the user to read what's happening.
- **Calm, not flashy** — muted deep-water surfaces with high-contrast teal at interaction points. The interface stays out of the way until you need it.
- **Accessible** — large touch targets, scalable fonts, keyboard focus rings, sufficient contrast. Freedom includes freedom to use the tool however you need to.
