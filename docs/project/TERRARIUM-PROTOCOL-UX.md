# The Terrarium Protocol — UX/UI Guidelines

> *Industrial Organics: heavy, bolted-down machinery housing delicate, glowing biological systems.*

The Terrarium Protocol is a design language born from the fusion of
**Bio-Synthetic Integration**, **Analog-Digital Fusion**, and **Bunker Minimalism**.
It imagines humanity inside high-tech, self-contained vaults where every scrap of
nature is precious, every mechanical part is irreplaceable, and every watt of
energy is tracked.

---

## 1. Design Principles

| # | Principle | Description |
|---|-----------|-------------|
| 1 | **Stewardship over consumption** | Users are caretakers of a living system, not passive consumers. Data that is not tended decays. |
| 2 | **Weight implies permanence** | Heavy, tactile interactions guard critical actions. If it matters, it should *feel* like it matters. |
| 3 | **Nature as status** | System health is expressed through biological metaphors — growth, bloom, wilt — not abstract percentages. |
| 4 | **Contradiction is coherence** | Weathered steel frames crisp bioluminescent data. Grime and glow coexist by design. |
| 5 | **Errors are leaks** | A user error is not a mistake — it is a breach in the life-support system. Treat it with urgency and clarity. |

---

## 2. Visual Language (UI)

### 2.1 Color Palette — "Deep Earth + Bioluminescence"

| Role | Token | Value | Usage |
|------|-------|-------|-------|
| Background | `--tp-bg` | Charcoal `#1a1a18` | Vault walls — dark, grounded, absorptive |
| Surface | `--tp-surface` | Oxidized Iron `#2c2824` | Panels, cards — weathered metal texture |
| Border | `--tp-border` | Rust `#5a3e2b` | Bolted edges, riveted dividers |
| Text | `--tp-text` | Pale Lethe `#d8d4c8` | Primary body text — organic off-white |
| Text dim | `--tp-text-dim` | Lichen `#8a8670` | Secondary / muted labels |
| Accent | `--tp-accent` | Bioluminescent Teal `#22e8a0` | Living data, active elements, healthy state |
| Accent warm | `--tp-accent-warm` | Mycelium Gold `#d4a828` | Warnings, nutrient low, attention needed |
| Growth | `--tp-green` | Chlorophyll `#44cc66` | Success, propagation, file saved |
| Stress | `--tp-red` | Red Bioluminescence `#ff4444` | Errors, system stress, life-support threat |
| Decay | `--tp-decay` | Fungal Grey `#6a6258` | Untended data, decomposing elements |

### 2.2 Typography

| Element | Specification | Rationale |
|---------|--------------|-----------|
| **Body** | Monospace (e.g. `JetBrains Mono`, `IBM Plex Mono`) | Industrial reliability; terminal-era heritage |
| **Headings** | Same monospace, heavier weight | Uniformity — no decorative typefaces in a vault |
| **Data readouts** | Monospace + **"Pulse" animation** (subtle opacity oscillation, 3–4 s cycle) | Data is *alive* — it breathes |
| **Labels** | Uppercase, letter-spaced | Stenciled onto machinery |

```css
/* Pulse animation for living data */
@keyframes bio-pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.72; }
}

.data-live {
  animation: bio-pulse 3.5s ease-in-out infinite;
}
```

### 2.3 Texture — "High-Definition Grime"

- **Surfaces** carry subtle noise or scratch overlays (CSS `background-image` grain or SVG filter). The frame is worn; the data inside is pristine.
- **Borders** use uneven widths or slight `border-image` roughness to suggest hand-welded seams.
- **Glowing content** (text, icons, meters) sits *above* the grime layer via layered `z-index` or `mix-blend-mode: screen`.

### 2.4 Iconography

- Combine **mechanical silhouettes** (gears, valves, rivets) with **organic forms** (leaves, roots, cells).
- Icons should feel stamped or etched, not drawn — use flat fills with a single highlight edge.
- Avoid perfectly symmetrical shapes; slight asymmetry suggests hand-made, irreplaceable parts.

---

## 3. Interaction Model (UX)

### 3.1 Navigation — Radial Menus

Primary navigation uses **circular / radial menus**, evoking both mechanical valve wheels and cellular cross-sections.

| Context | Behavior |
|---------|----------|
| **Top-level nav** | Radial dial fixed to screen edge; sections arranged like valve positions |
| **Contextual actions** | Hold-press spawns a radial ring around the cursor / touch point |
| **Breadcrumbs** | Concentric rings — outer ring = current depth, inner rings = parent levels |

### 3.2 Feedback — "Haptic Growth"

| Action | Feedback pattern | Feel |
|--------|-----------------|------|
| **Save / Commit** | Slow rhythmic thrum (250 ms on, 150 ms off, x3) | A root taking hold in soil |
| **Delete / Prune** | Single sharp snap followed by fading vibration | A branch breaking cleanly |
| **Error / Stress** | Rapid irregular pulses | Heartbeat under duress |
| **Loading / Growing** | Gradual vibration crescendo | Germination to bloom |

### 3.3 Mechanical Gating

Critical actions require **analog-style physical interaction** to prevent accidental triggers and reinforce the weight of the action.

- **Low-security:** Single tap/click — standard interaction.
- **Medium-security:** Press-and-hold with a visible pressure gauge filling. Release early = cancel.
- **High-security ("Critical Life Support"):** A two-stage gate:
  1. **Unlock** — slide or rotate an on-screen crank/dial (simulating power generation).
  2. **Confirm** — biometric or passphrase while the gate is open. The gate slowly closes (timeout), forcing deliberate timing.

### 3.4 The Decay Principle

Digital files are not permanent. Untended data visually decomposes.

| Decay stage | Time untouched | Visual treatment |
|-------------|---------------|-----------------|
| **Fresh** | < 7 days | Full color, bioluminescent glow |
| **Aging** | 7–30 days | Color desaturates slightly, glow dims |
| **Wilting** | 30–90 days | Text develops subtle glitch artifacts, edges soften |
| **Composting** | 90+ days | Heavy grain overlay, muted palette, "fungal" texture creep |
| **Reclaimed** | User never returns | Data dissolves into background; nutrients (storage) returned to the system |

> **Design rule:** Decay is *visual only* by default — data is never auto-deleted. The user must choose to "compost" (archive) or "water" (interact with) their files.

---

## 4. System Status — The Biosphere

### 4.1 Life-Sync Bar

Replaces the traditional battery / status bar. A horizontal or arc-shaped meter that communicates system health as **biosphere health**.

```
┌─────────────────────────────────────┐
│  O₂ ████████████░░░░  78%  │ 32°C  │  ← Biosphere Health
│  ▸ Photosynthesis active            │
└─────────────────────────────────────┘
```

| Metric | Biological metaphor | Maps to |
|--------|-------------------|---------|
| CPU / Performance | Metabolic rate | "Respiration: Normal / Elevated / Critical" |
| Storage | Soil nutrients | "Nutrients: Rich / Depleted" |
| Battery / Power | Sunlight exposure | "Light level: Full sun / Dusk / Blackout" |
| Network | Mycelium network | "Root network: Connected / Fragmented / Severed" |
| Memory | Water table | "Hydration: Saturated / Adequate / Drought" |

### 4.2 Notifications — "Environmental Shifts"

Notifications avoid sharp interruptions. Instead, the environment itself shifts.

| Severity | Notification style |
|----------|-------------------|
| **Info** | Screen color temperature warms slightly for 3 s, then returns |
| **Attention** | Ambient light dims as if a cloud passed; a soft chime sounds |
| **Warning** | Background grain intensifies; accent color shifts to `--tp-accent-warm` |
| **Critical** | Red bioluminescence pulses from screen edges; haptic stress pattern fires |

> **Bunker fatigue rule:** Never use flashing, strobing, or high-contrast popups. Occupants of a vault need calm signals, not alarms that cause panic. Mimic circadian rhythms, not sirens.

---

## 5. Component Patterns

### 5.1 Buttons

| Variant | Appearance | Usage |
|---------|-----------|-------|
| **Primary** | Solid `--tp-accent` fill, riveted border, glow on hover | Main actions — "Plant", "Grow", "Commit" |
| **Secondary** | Ghost outline in `--tp-border`, fills on hover | Supporting actions |
| **Destructive** | `--tp-red` outline, fills to solid red on hold-confirm | Pruning, composting, system overrides |
| **Mechanical** | Resembles a physical toggle/switch or lever | Gated actions, mode switches |

### 5.2 Cards / Panels

- Appear as **welded metal plates** with visible corner bolts (border-radius: 2–4 px, not rounded).
- Content inside glows against the weathered frame.
- Expansion uses a vertical "iris" animation — panels dilate open like an aperture.

### 5.3 Forms / Inputs

- Text inputs resemble **etched grooves** in metal — inset borders, dark backgrounds.
- Active focus state: a thin bioluminescent line traces the input border (animated `border-image` or `box-shadow`).
- Dropdowns open as mini radial selectors when space permits.

### 5.4 Progress / Loading

- **Determinate:** A vine grows across the progress track, blooming at 100%.
- **Indeterminate:** Motes drift across the container in a gentle loop.

---

## 6. Motion & Animation

| Principle | Guideline |
|-----------|-----------|
| **Organic easing** | Use `cubic-bezier(0.22, 1, 0.36, 1)` — fast start, slow settle, like a tendril finding its grip |
| **No mechanical snapping** | Elements grow into place, never pop. Minimum transition: 200 ms. |
| **Breathing idle** | Idle UI elements have a faint pulse (`bio-pulse`). A still screen is a dead screen. |
| **Decay transitions** | Wilting animations are slow (800 ms+). Decay is gradual, never sudden. |
| **Growth transitions** | New elements emerge from small to full size ("germination"). Avoid slide-in from off-screen. |

---

## 7. Sound Design (Optional)

| Event | Sound character |
|-------|----------------|
| **Navigation** | Mechanical click — a valve turning, a latch engaging |
| **Success** | A soft, resonant tone — a drop of water hitting a still pool |
| **Error** | A pressurized hiss — a seal breaking |
| **Ambient** | Low hum of air recyclers, distant drip of condensation (toggleable) |

---

## 8. Accessibility

The Terrarium Protocol's atmospheric design must never compromise usability.

| Requirement | Implementation |
|-------------|---------------|
| **Contrast** | Bioluminescent text on dark surfaces must meet WCAG AA (4.5:1 minimum). Test all glow effects against grime textures. |
| **Motion sensitivity** | Provide a `--tp-reduce-motion` toggle that disables pulse, decay, and growth animations. Replaces them with instant state changes. |
| **Color independence** | Never rely on color alone — pair every status color with an icon, label, or pattern. |
| **Screen readers** | Radial menus must have a linear-list fallback. All biological metaphors must have plain-language `aria-label` equivalents (e.g., `aria-label="Battery: 78%"`). |
| **Haptic opt-out** | All haptic patterns are optional and off by default on devices that lack granular haptic control. |

---

## 9. The Designer's Dilemma

> *In this world, a "User Error" isn't just a mistake — it's a leak in the life-support system.*

When designing any new feature, ask:

1. **Is it alive?** — Does this element breathe, grow, or decay? If it's static, it feels dead.
2. **Does it have weight?** — Critical actions should feel heavy. Casual actions should feel light.
3. **What happens if you neglect it?** — Every element should have a "what if the user walks away" state.
4. **Would it exist in a vault?** — If it wouldn't survive resource scarcity, simplify it.

### Example: Music Player as Garden

A playlist is not a list of files — it is a **garden bed**.

- Each song is a **plant species** with a visual form derived from its audio profile (tempo = height, key = color, energy = leaf density).
- Songs "bloom" at their preferred time of day based on listening history. Morning songs flower at dawn; late-night tracks open in darkness.
- A playlist left unplayed for weeks begins to "overgrow" — songs tangle together, suggesting the user re-curate.
- Adding a new song is "planting a seed" — it appears small and grows over the first few listens.
- Removing a song is "pruning" — the plant withers gracefully and its space is reclaimed.
