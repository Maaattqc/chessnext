# Technical Conventions

## Website (`website/`)

- **Framework:** Next.js 15 (App Router) + TypeScript
- **Styling:** Tailwind CSS + shadcn/ui components
- **Auth:** NextAuth.js — magic link only (email with verification code, no password)
- **Chess UI:** react-chessboard + chess.js
- **Payments:** Stripe (checkout + subscriptions)
- **State management:** zustand (board state, analysis, navigation)
- **Validation:** zod (forms, API inputs, FEN sanitization)
- **Notifications:** sonner (toast notifications, shadcn ecosystem)
- **Dark mode:** next-themes (light/dark/system)
- **i18n:** next-intl (English + French at launch)
- **Blog/Content:** MDX (weekly concept posts for SEO)
- **SEO:** next-sitemap + JSON-LD structured data
- **OG images:** @vercel/og or satori (chess position previews for social sharing)
- **PWA:** next-pwa (installable, offline basics, no App Store needed)
- **Animations:** framer-motion (board transitions, concept reveals)
- **Keyboard shortcuts:** cmdk (arrow navigation, board flip, power user UX)
- **Loading states:** shadcn skeleton components
- **Tests:** vitest
- **ORM:** Prisma (PostgreSQL)

## Chess Engine (`chess-engine/`)

- **Framework:** Python 3.12 + FastAPI
- **Chess:** python-chess + Stockfish (local binary)
- **GPU inference:** RunPod SDK for Leela in production
- **Coach narratives:** Claude API (Anthropic SDK)
- **Real-time:** Server-Sent Events for analysis progress (Stockfish -> Leela -> Claude, streamed live)
- **Tests:** pytest
- **ORM:** SQLAlchemy (PostgreSQL)

## Email

- **Provider:** Resend (free tier: 3K emails/month)
- **Templates:** React Email (emails built as React components)
- **Usage:** Magic link auth codes, analysis notifications

## Database

- **Provider:** Railway PostgreSQL
- **Access:** Prisma from website, SQLAlchemy from chess-engine
- **Shared via:** `DATABASE_URL` environment variable

## Cache & Rate Limiting

- **Provider:** Upstash Redis (serverless, free tier: 10K commands/day)
- **Usage:** Rate limiting on public endpoints, API response caching, session store

## Monitoring

- **Errors:** Sentry (error tracking, performance traces, alerts)
- **Analytics:** PostHog (funnels, retention, feature flags, free tier: 1M events/month)

## Security

- NEVER put API keys, tokens, passwords, or secrets in code
- All secrets in environment variables (`.env.local`)
- `.env*` must be in `.gitignore`
- No `console.log` of secrets, even in dev
- Validate and sanitize all user inputs server-side (zod everywhere)
- Sanitize FEN strings before passing to Stockfish or Leela
- Rate limiting on all public endpoints (Upstash)
- CORS configured strictly (allow only own domain)
- Helmet for security headers
- Parameterized SQL everywhere, never string concatenation
- HTTPS only in production

## Later (Phase 2+)

- **File storage:** Cloudflare R2 or S3 — for chess diagrams, PGN exports, PDF reports
- **Job queue:** BullMQ (via Upstash Redis) — async analysis pipeline when traffic grows
- **Native mobile:** React Native or Expo — only if PWA traction justifies it

## Not Using (avoid over-engineering)

- GraphQL — REST is enough, FastAPI handles it well
- WebSocket server — SSE covers our needs (analysis is unidirectional)
- Redux — zustand does the same in 10x less code
- Storybook — not enough custom components to justify
- Docker in dev — Railway deploys directly from GitHub

## Code Rules

- Tests for every feature
- Simple first, no over-engineering
- Mobile responsive from day one
- Dark mode from day one
- Git: conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`)
- One branch per feature, merge via PR
- No unused imports, no dead code
- Environment variables for all configuration
