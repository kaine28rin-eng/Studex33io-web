# STUDYX Academic Study Bot — Design System

## Tone & Aesthetic

**"Web Engineer Tier" — Professional Academic UI with Fluid Motion**

A dark-mode-first, high-contrast academic interface that balances institutional professionalism with modern web engineering polish. Think Figma-style precision meets university portal usability.

## Color Palette

| Role | Token | Value |
|------|-------|-------|
| Background | `--color-bg` | `#0a0f1a` (deep navy, near-black) |
| Surface | `--color-surface` | `#111827` (elevated card background) |
| Surface Hover | `--color-surface-hover` | `#172032` |
| Border | `--color-border` | `#1e293b` (subtle, 50% opacity) |
| Border Hover | `--color-border-hover` | `#334159` |
| Primary | `--color-primary` | `#0ea5e9` (sky blue — academic trust) |
| Primary Glow | `--color-primary-glow` | `#0ea5e920` (inner glow) |
| Primary Hover | `--color-primary-hover` | `#0284c7` |
| Text Primary | `--color-text` | `#f1f5f9` (high readability) |
| Text Secondary | `--color-text-muted` | `#94a3b8` |
| Text Dim | `--color-text-dim` | `#64748b` |
| Accent Green | `--color-accent-green` | `#10b981` (success states) |
| Accent Amber | `--color-accent-amber` | `#f59e0b` (warnings) |
| Accent Red | `--color-accent-red` | `#ef4444` (errors/destructive) |

## Glassmorphism

All elevated surfaces use a frosted glass effect:

```css
background: rgba(255, 255, 255, 0.03);
backdrop-filter: blur(12px);
border: 1px solid rgba(255, 255, 255, 0.05);
```

Cards: `rgba(17, 24, 43, 0.85)` background, `rgba(255,255,255,0.03)` overlay, 12px blur.

## Typography

- **Display**: `Inter` (system: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`)
- **Headings**: `Inter`, weight 6-700, letter-trace tight
- **Body**: `Inter`, weight 400, 16px base
- **Mono**: `JetBrains Mono` or `Fira Code` for file sizes/metadata

## Motion System

### Frame Durations (Framer Motion / CSS)
- **Instant**: 80ms (micro-interactions, hover lifts)
- **Quick**: 180ms (dropdown open, card selection)
- **Standard**: 280ms (page transitions, modal entrance)
- **Slow**: 520ms (hero animations, section reveals)

### Easing Curves
- `--ease-out-quad`: `cubic-bezier(0.25, 0.46, 0.45, 0.94)` (cards, lifts)
- `--ease-in-out-sine`: `cubic-bezier(0.37, 0, 0.63, 1)` (page transitions)
- `--ease-spring`: `cubic-bezier(0.34, 1.56, 0.64, 1)` (elastic bounces)

### Micro-Interactions
1. **Card Hover**: Y-lift 4px, border glow cyan 20%, 80ms ease-out-quad
2. **Card Enter**: Scale from 0.95 → 1.0, opacity 0 → 1, stagger 50ms
3. **Button Press**: Scale 0.97, immediate; ripple from click point
4. **Search Input**: Border color transitions to primary on focus (180ms)
5. **Module Transition**: Fade out current, slide left; fade in new (280ms)
6. **Loading Dots**: Three dots bouncing with 120ms stagger (infinite, 800ms cycle)

### Fluid Motion Frames
- All animations use `transform` and `opacity` for 60fps compositing
- `will-change: transform, opacity` on animating elements
- No layout thrashing — animate transform, never width/height

## Layout Grid
- Max content width: 960px
- Gutter: 24px
- Module card grid: responsive `repeat(auto-fill, minmax(260px, 1fr))`
- Card padding: 24px
- Card border-radius: 16px (lg), 12px (md), 8px (sm)

## Components

### Module Card
```
┌────────────────────────────────┐
│ [icon] Module Name             │
│ Description text               │
│ ────────────────────────────── │
│ 5 materials • Last updated    │
└────────────────────────────────┘
```
- Hover: border `--color-primary-glow` (20% opacity), lift 4px
- Click: scale 0.98, navigate to module view

### Search Bar
- Full-width, 48px height
- Focus ring: cyan glow, 180ms
- Placeholder: "🔍 Search materials across all modules..."

### Material Item
- Flex row: icon + info + download button
- Hover background: `--color-surface-hover`
- Download button: primary color, rounded, 80ms scale on press

### Back Button
- Ghost style (transparent bg, border `--color-border`)
- Hover: `--color-surface-hover` background
- Back arrow icon transitions with slide

## Animation Principles

1. **Hierarchy**: Important state changes (module → materials) use 280ms standard; micro (hover) uses 80ms
2. **Continuity**: Shared element transitions between views (card expands into detail view)
3. **Feedback**: Every interactive element has a press state (scale 0.97)
4. **Loading**: Skeleton screens with shimmer (linear-gradient sweep), not spinners
5. **Staggering**: Lists animate in with 50-100ms stagger per item

## Data Fetching

All data comes from `/api/materials.json` (GitHub Pages) or `/api/modules` (local Flask).
The new frontend must preserve this exact contract:
- `modules[]` → array of module objects `{ id, name, description, material_count }`
- `materials[]` → array of material objects `{ module, title, file_size, mime_type, download_url }`
- `last_updated` → ISO timestamp string