# Design System — ChessNext.ai

Visual language for the entire app. Claude Code must follow these
specs to produce a consistent, professional UI.

---

## Brand Identity

- **Personality:** Expert but approachable. Like a GM friend, not a textbook.
- **Feel:** Dark, focused, premium. Think Lichess dark mode meets Stripe's polish.
- **Not:** Childish, gamified with badges everywhere, cluttered like Chess.com.

## Colors

Built on shadcn/ui with custom chess-themed palette.

```
Background:
  --background:    hsl(220, 20%, 8%)      #111827  (near-black blue)
  --card:          hsl(220, 20%, 12%)     #1a2332  (elevated surface)
  --popover:       hsl(220, 20%, 14%)     #1e2a3a  (dropdowns, modals)

Foreground:
  --foreground:    hsl(210, 20%, 92%)     #e5e9ef  (primary text)
  --muted:         hsl(215, 15%, 55%)     #7d8a9a  (secondary text)

Accent:
  --primary:       hsl(160, 70%, 45%)     #22b573  (green — growth, learning)
  --primary-hover: hsl(160, 70%, 38%)     #1a9660
  --destructive:   hsl(0, 72%, 51%)       #dc2626  (errors, blunders)

Chess-specific:
  --eval-winning:  hsl(160, 70%, 45%)     #22b573  (green — winning)
  --eval-equal:    hsl(215, 15%, 55%)     #7d8a9a  (gray — equal)
  --eval-losing:   hsl(0, 72%, 51%)       #dc2626  (red — losing)
  --concept-new:   hsl(45, 90%, 55%)      #e5a820  (gold — new concept unlocked)

Board:
  --board-light:   hsl(35, 30%, 75%)      #c4a86e  (warm light square)
  --board-dark:    hsl(150, 25%, 35%)     #437a5c  (forest green dark square)
  --board-highlight: hsla(55, 90%, 60%, 0.4)       (yellow move highlight)
  --board-arrow:   hsla(160, 70%, 45%, 0.7)        (green concept arrow)

Light mode overrides (via next-themes):
  --background:    hsl(0, 0%, 98%)
  --card:          hsl(0, 0%, 100%)
  --foreground:    hsl(220, 20%, 12%)
  --muted:         hsl(215, 15%, 45%)
```

## Typography

```
Font stack:
  --font-sans:  "Inter", system-ui, sans-serif    (UI text)
  --font-mono:  "JetBrains Mono", monospace       (FEN, PGN, moves)
  --font-chess: "Noto Sans", sans-serif            (chess notation)

Sizes (Tailwind):
  Page title:     text-3xl font-bold   (30px)
  Section title:  text-xl font-semibold (20px)
  Body:           text-base            (16px)
  Small/caption:  text-sm              (14px)
  FEN/PGN:        text-sm font-mono    (14px monospace)
  Move notation:  text-base font-medium (16px)

Line height: 1.6 for body text, 1.3 for headings
```

## Layout

```
Max content width: 1200px (max-w-6xl), centered
Sidebar (concept list): 280px fixed on desktop, drawer on mobile
Board area: min 360px, max 560px (square, responsive)
Padding: p-4 mobile, p-6 tablet, p-8 desktop
Gap between sections: gap-6

Breakpoints (Tailwind defaults):
  sm: 640px    (large phone landscape)
  md: 768px    (tablet)
  lg: 1024px   (desktop — sidebar appears)
  xl: 1280px   (wide desktop)
```

## Chess Board

```
Board component: react-chessboard
Board width: responsive, 100% of container up to 560px
Piece set: default (cburnett) — most recognizable
Coordinates: shown (a-h, 1-8)
Animation: 200ms piece movement
Orientation: auto-flip based on side to move

Custom board styles:
  Light squares: var(--board-light)
  Dark squares: var(--board-dark)
  Last move highlight: var(--board-highlight) on from and to squares
  Concept arrows: var(--board-arrow), 8px width
  Best move arrow: green with opacity 0.7
  Mistake arrow: red with opacity 0.7
```

## Components (shadcn/ui)

Use shadcn/ui defaults with our color overrides. Key components:

```
Button:      default (primary green), outline, ghost, destructive
Card:        concept cards, analysis cards, position cards
Dialog:      login modal, upgrade modal, settings
Tabs:        concept detail (Learn / Practice / Quiz)
Badge:       difficulty (beginner=green, intermediate=yellow, advanced=red)
Skeleton:    loading states for board, concept list, analysis
Toast:       sonner — bottom-right, auto-dismiss 4s
Tooltip:     on hover for move notation, piece names
Progress:    concept learning progress bar (green fill)
```

## Page Templates

### Landing page
```
Hero (full-width dark bg):
  - Headline + subheadline
  - Animated chess board showing a concept
  - CTA button (green, large)
Features grid (3 columns):
  - Superhuman Concepts
  - Human-Adjusted Eval
  - Root-Cause Analysis
Social proof / concept preview
Pricing cards
Footer
```

### Dashboard (logged in)
```
Sidebar:
  - Concept list (with progress dots)
  - Analysis history
  - Settings
Main area:
  - "Continue learning" card (next concept to review)
  - Recent analyses
  - Stats summary
```

### Concept detail
```
Two-column on desktop, stacked on mobile:
  Left: Chess board with position (interactive)
  Right: Explanation text + move controls (prev/next/flip)
Below: Quiz section (practice positions)
Bottom: Related concepts
```

### Analysis page
```
Input: FEN text field or paste PGN
Board: center, large
Below board: Evaluation bar + best move
Right panel (desktop) / below (mobile):
  - AI coach narrative
  - Matched concepts
  - Move list (if game analysis)
```

## Motion (framer-motion)

```
Page transitions: fade 200ms
Card hover: scale(1.02) 150ms
Board piece: spring animation (default react-chessboard)
Concept reveal: slide-up + fade 300ms
Progress bar: width transition 500ms ease-out
Toast: slide-in from right 200ms
Skeleton pulse: shadcn default
```

## Accessibility

- All interactive elements keyboard-accessible
- Board: arrow keys to navigate moves, space to flip
- Color contrast: minimum 4.5:1 for text, 3:1 for large text
- Screen reader: alt text for board positions ("White king on e1, ...")
- Focus ring: visible on all interactive elements (2px primary color)
- Reduced motion: respect prefers-reduced-motion
```

## Icons

Use Lucide icons (included with shadcn/ui). Key icons:
- Chess piece: use board itself, not icons
- Learning: BookOpen, GraduationCap
- Analysis: Search, BarChart3
- Settings: Settings, User
- Navigation: ChevronLeft, ChevronRight, ArrowLeft
- Status: Check, X, AlertTriangle
```
