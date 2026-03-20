# FlashWizard Visual Identity

## Logo concept

The FlashWizard mark combines a **lightning bolt** (flash) with a **wizard hat** silhouette. The bolt cuts through the hat at an angle, suggesting speed and transformation. Use the bolt alone as a compact favicon or app icon.

```
     /\
    /  \
   / /\ \
  / /⚡ \ \
 / /______\ \
   ‾‾‾‾‾‾‾‾
```

**Wordmark:** "Flash" in bold weight, "Wizard" in regular weight, no space. Set in the UI system font stack or, where a brand font is needed, in **Inter** (open source, variable weight).

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

### Dark theme (primary)

| Role | CSS variable | Hex | Usage |
|------|-------------|-----|-------|
| Background | `--bg` | `#0f1117` | Page background |
| Surface | `--bg-card` | `#1a1d27` | Cards, panels, modals |
| Surface hover | `--bg-hover` | `#242836` | Interactive hover states |
| Border | `--border` | `#3a3f50` | Dividers, card edges |
| Text | `--text` | `#f0f2f7` | Primary body text |
| Text dim | `--text-dim` | `#a8adc0` | Secondary/muted text |
| **Accent (Electric Blue)** | `--accent` | `#5a9bff` | Links, active elements, brand color |
| Accent hover | `--accent-hover` | `#7db4ff` | Hover state for accent |
| Success (Mint) | `--green` | `#3ee8a8` | Confirmations, completed states |
| Warning (Amber) | `--yellow` | `#fcc53a` | Caution, missing dependencies |
| Error (Coral) | `--red` | `#ff8585` | Failures, destructive actions |
| Info (Cyan) | `--cyan` | `#33e0f5` | UI informational elements |

### Light theme

| Role | CSS variable | Hex |
|------|-------------|-----|
| Background | `--bg` | `#f4f6fa` |
| Surface | `--bg-card` | `#ffffff` |
| Surface hover | `--bg-hover` | `#ebeef5` |
| Border | `--border` | `#cdd2e0` |
| Text | `--text` | `#1a1d27` |
| Text dim | `--text-dim` | `#5a6078` |
| Accent | `--accent` | `#2d7aef` |
| Accent hover | `--accent-hover` | `#1a66d6` |
| Success | `--green` | `#1ba870` |
| Warning | `--yellow` | `#c89200` |
| Error | `--red` | `#d44040` |
| Info | `--cyan` | `#0ea5bd` |

### Terminal sub-palette

The terminal uses a dedicated set of color tokens (`--term-*`) with higher saturation than their UI counterparts. This ensures legibility when reading dense log output at small font sizes against both dark and light terminal backgrounds.

| Role | Dark hex | Light hex | CSS variable |
|------|----------|-----------|-------------|
| Background | `#0a0c10` | `#f0f2f5` | `--term-bg` |
| Command | `#40e8ff` | `#0b7a8e` | `--term-cmd` |
| Success | `#4dffc0` | `#127a52` | `--term-success` |
| Error | `#ff9494` | `#c03030` | `--term-error` |
| Warning | `#ffd04a` | `#8a6800` | `--term-warn` |
| Info | `#8892a8` | `#5a6078` | `--term-info` |

### Usage rules

- **Electric Blue** is the primary brand color. Use it for the wordmark accent, primary buttons, active states, and links.
- **Mint** signals success and completion — never use it for decoration.
- **Coral** and **Amber** are reserved for error and warning states. Do not mix them.
- In both themes, text on accent backgrounds must be `#ffffff`.
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
- **Shadow (dark):** `0 2px 12px rgba(0,0,0,0.3)` — used sparingly on hover and elevated elements.
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
- **Transparent** — terminal output is shown directly, not hidden behind spinners. The UI trusts the user to read what's happening.
- **Calm, not flashy** — muted surfaces with high-contrast accent colors at interaction points. The interface stays out of the way until you need it.
- **Accessible** — large touch targets, scalable fonts, keyboard focus rings, sufficient contrast. Freedom includes freedom to use the tool however you need to.
