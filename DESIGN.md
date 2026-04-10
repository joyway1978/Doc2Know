# Design System — Doc2Know

## Product Context

- **What this is:** Doc2Know is a web application that converts Word documents (.docx, .doc, .pdf) into structured Markdown knowledge bases using LLM analysis
- **Who it's for:** Knowledge workers, customer service teams, documentation managers who need to process large volumes of documents and build searchable knowledge bases
- **Space/industry:** Document Management / Knowledge Management SaaS
- **Project type:** Web application with dashboard interface

## Aesthetic Direction

- **Direction:** Professional Minimalist — Linear-style precision with more structural hierarchy than Notion
- **Decoration level:** Minimal — rely on typography hierarchy and whitespace to create rhythm, avoid decorative elements
- **Mood:** Quiet, focused, efficient. The interface should be invisible, letting the content be the hero.
- **Core principle:** Knowledge management tools should reduce cognitive load, so the UI must be calm and unobtrusive.

## Typography

- **Display/Hero:** Geist — Modern geometric sans-serif by Vercel, balances tech sophistication with professionalism
- **Body:** Geist — Same font family for consistency and simplicity
- **UI/Labels:** Geist — Unified type system
- **Data/Tables:** Geist Mono — Monospace for code blocks, file paths, timestamps (supports tabular-nums)
- **Chinese fallback:** system-ui, -apple-system, "PingFang SC", "Microsoft YaHei"
- **Loading strategy:** Google Fonts or self-hosted (Geist is open source)

### Type Scale

| Level | Size | Weight | Usage |
|-------|------|--------|-------|
| Display | 36px | 700 | Hero headings |
| H1 | 28px | 700 | Page titles |
| H2 | 20px | 600 | Section headers |
| H3 | 16px | 600 | Card titles |
| Body | 14px | 400 | Paragraphs, labels |
| Small | 12px | 400 | Metadata, captions |
| Code | 13px | 400 | File paths, code |

## Color

- **Approach:** Restrained — 1 accent + neutral grays, let content be the star

### Primary Palette

| Token | Hex | Usage |
|-------|-----|-------|
| Primary | #0F172A | Main text, buttons, emphasis |
| Primary Muted | #475569 | Secondary text, labels |
| Surface | #FFFFFF | Main background |
| Surface Subtle | #F8FAFC | Card backgrounds, inputs |
| Border | #E2E8F0 | Borders, dividers |
| Accent | #3B82F6 | Interactive elements, progress bars, selected states |
| Accent Hover | #2563EB | Hover states |

### Semantic Colors

| Token | Hex | Usage |
|-------|-----|-------|
| Success | #10B981 | Completed states |
| Warning | #F59E0B | Warning states |
| Error | #EF4444 | Error states |

### Dark Mode

- Primary text: #F8FAFC
- Surface: #0F172A
- Surface Subtle: #1E293B
- Border: #334155
- Reduce all color saturation by 20%

## Spacing

- **Base unit:** 4px
- **Density:** Comfortable — generous whitespace for readability

### Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Tight gaps |
| sm | 8px | Component internals |
| md | 16px | Card padding |
| lg | 24px | Section spacing |
| xl | 32px | Page padding |
| 2xl | 48px | Hero sections |

## Layout

- **Approach:** Hybrid — Left sidebar navigation (Confluence-style) + card-based content area (Notion-influenced)
- **Grid:** 12-column for main content
- **Max content width:** 1400px
- **Sidebar width:** 240px fixed

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| sm | 4px | Buttons, badges, inputs |
| md | 6px | Cards, panels |
| lg | 8px | Modals, large containers |

## Motion

- **Approach:** Minimal-functional — micro-interactions only for state changes
- **Easing:**
  - Enter: ease-out
  - Exit: ease-in
  - Move: ease-in-out
- **Duration:**
  - Micro (hover): 100ms
  - Short (button press): 150ms
  - Medium (page transitions): 250ms

## UI Components

### Buttons

- **Primary:** Blue background (#3B82F6), white text, 4px radius
- **Secondary:** Subtle background (#F8FAFC), dark border, dark text
- **Ghost:** Transparent, muted text, hover shows subtle background
- **Sizes:** sm (compact), default, lg (emphasis)

### Badges

- Default: Subtle border, muted text
- Accent: Blue tint background, blue text
- Success: Green tint background, green text
- Warning: Amber tint background, amber text
- Error: Red tint background, red text
- All use 9999px border-radius (pill shape)

### Progress Bars

- Height: 8px
- Background: Border color
- Fill: Accent color
- Border-radius: 4px
- Smooth width transitions

### Cards

- Background: Surface or Surface Subtle
- Border: 1px solid Border color
- Border-radius: 6px
- Padding: 16px (md)
- Hover: Subtle shadow elevation

## Design Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-04-10 | Professional minimalist aesthetic | Knowledge tools should reduce cognitive load; quiet UI lets content shine |
| 2025-04-10 | Left sidebar + card hybrid layout | Balances enterprise familiarity (Confluence) with modern content presentation (Notion) |
| 2025-04-10 | Restrained color palette (1 accent) | Prevents visual competition with document content |
| 2025-04-10 | Geist type family | Modern, technical, consistent across weights; excellent for SaaS tools |
| 2025-04-10 | 4px base unit with comfortable density | Readable without feeling sparse |
| 2025-04-10 | Minimal functional motion | Progress indication without distraction |

## Research Insights

Based on competitive analysis of Notion, Confluence, and modern DMS tools:

- **Search-first design** is table stakes — users expect to find documents within 2 clicks
- **Progress visibility** is critical for document processing workflows
- **Card-based layouts** improve scannability for knowledge bases
- **Left sidebar navigation** remains the enterprise standard
- **Consumer-grade UX** is now expected in B2B tools (the "Notion effect")

## Safe Choices vs Risks

### Safe (Category Baseline)
1. Left sidebar navigation — enterprise users expect this pattern
2. Card-based content display — modern SaaS standard
3. Blue as primary accent — trust color for B2B products
4. Clear progress indicators — essential for upload/processing workflows

### Risks (Differentiation)
1. **No icon decoration** — Rely entirely on typography hierarchy
   - Benefit: Maximum professionalism, forces content focus
   - Cost: May appear too minimal; ensure interaction feedback is clear

2. **Minimal border-radius (4px)** — Against the "friendly rounded" trend
   - Benefit: More serious, efficient enterprise tool feel
   - Cost: May appear cold; compensate with color and motion warmth

## Preview

See `docs/design-preview.html` for an interactive preview of this design system.
