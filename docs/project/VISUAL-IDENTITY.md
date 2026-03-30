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

The palette follows **The Terrarium Protocol** design language — "Deep Earth" tones contrasted with bioluminescent overlays. Heavy, weathered surfaces frame crisp, glowing data. See [TERRARIUM-PROTOCOL-UX.md](TERRARIUM-PROTOCOL-UX.md) for the full UX/UI guidelines.

### Dark theme (primary) — "Deep Earth + Bioluminescence"

| Role | CSS variable | Hex | Usage |
|------|-------------|-----|-------|
| Background | `--bg` | `#1a1a18` | Vault walls — dark, grounded charcoal |
| Surface | `--bg-card` | `#222018` | Cards, panels — oxidized iron |
| Surface hover | `--bg-hover` | `#2c2824` | Interactive hover states |
| Border | `--border` | `#3a3228` | Riveted dividers, welded seams |
| Text | `--text` | `#d8d4c8` | Primary body text — pale lethe off-white |
| Text dim | `--text-dim` | `#8a8670` | Secondary/muted — lichen |
| **Accent (Bioluminescent)** | `--accent` | `#22e8a0` | Living data, active elements, healthy state |
| Accent hover | `--accent-hover` | `#44f0b4` | Hover glow |
| Success (Chlorophyll) | `--green` | `#44cc66` | Confirmations, growth, file saved |
| Warning (Mycelium Gold) | `--yellow` | `#d4a828` | Caution, nutrient low |
| Error (Red Bioluminescence) | `--red` | `#ff4444` | Failures, system stress |
| Info (Teal) | `--cyan` | `#22c8a0` | Informational elements |

### Light theme — "Bleached Vault"

| Role | CSS variable | Hex |
|------|-------------|-----|
| Background | `--bg` | `#eae6de` |
| Surface | `--bg-card` | `#f4f0e8` |
| Surface hover | `--bg-hover` | `#ddd8ce` |
| Border | `--border` | `#b8b0a0` |
| Text | `--text` | `#2a2418` |
| Text dim | `--text-dim` | `#6a6050` |
| Accent | `--accent` | `#146e55` |
| Accent hover | `--accent-hover` | `#125e48` |
| Success | `--green` | `#2a8848` |
| Warning | `--yellow` | `#a08020` |
| Error | `--red` | `#c03030` |
| Info | `--cyan` | `#18786a` |

### Terminal sub-palette

The terminal uses a dedicated set of color tokens (`--term-*`) with bioluminescent saturation. This ensures legibility when reading dense log output at small font sizes against both dark and light terminal backgrounds.

| Role | Dark hex | Light hex | CSS variable |
|------|----------|-----------|-------------|
| Background | `#161614` | `#e2ded6` | `--term-bg` |
| Command | `#22e8a0` | `#186858` | `--term-cmd` |
| Success | `#44cc66` | `#2a6838` | `--term-success` |
| Error | `#ff4444` | `#a02828` | `--term-error` |
| Warning | `#d4a828` | `#886818` | `--term-warn` |
| Info | `#6a6258` | `#6a6050` | `--term-info` |

### Usage rules

- **Bioluminescent Green** is the primary accent. Use it for active states, links, and primary buttons.
- **Chlorophyll** signals success and growth — never use it for decoration.
- **Red Bioluminescence** and **Mycelium Gold** are reserved for system stress and warnings.
- On accent backgrounds, text must be `#1a1a18` (dark enough to meet contrast on bright green).
- Maintain a minimum contrast ratio of **4.5:1** for body text and **3:1** for large text (WCAG AA).
- Terminal text must meet **4.5:1** against `--term-bg` — use the `--term-*` tokens, not the UI palette.
- Active data elements use the `bio-pulse` animation (subtle 3.5s opacity cycle) to indicate "living" state.

## Typography

| Element | Font | Weight | Size |
|---------|------|--------|------|
| Body | Monospace (`'JetBrains Mono', 'IBM Plex Mono', 'Fira Code', 'Consolas', monospace`) | 400 | `1rem` (scales with `--font-scale`) |
| Headings | Monospace | 600–700 | `1.05rem`–`1.8rem` |
| Labels / section titles | Monospace | 600 | `0.9rem`, uppercase, `0.12em` tracking (stenciled) |
| Status pills | Monospace | 500 | `0.8rem`, uppercase |
| Buttons | Monospace | 600 | `1rem`, uppercase, `0.04em` tracking |

The `--font-scale` CSS variable supports user-selectable font sizes (`1`, `1.2`, `1.4`). All type sizes multiply against it. Monospace throughout reinforces the industrial/terminal heritage of the Terrarium Protocol.

## Spacing and shape

- **Border radius:** `--radius-card` (`4px`) for cards and modals — welded metal plates, not rounded plastic. `--radius-btn` (`3px`) for buttons and inputs. `--radius-pill` (`10px`) for pills.
- **Shadow (dark):** `0 2px 12px rgba(0,0,0,0.5)` — deeper shadows for vault depth.
- **Shadow (light):** `0 2px 12px rgba(0,0,0,0.1)`.
- **Glow:** Bioluminescent elements use `box-shadow: 0 0 8-12px rgba(34,232,160,0.1-0.3)` for living glow.
- **Grain:** A fractal noise SVG overlay (`mix-blend-mode: overlay`) adds texture to all surfaces.
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
