# Technical Conventions

## Website (`website/`)

- **Framework:** Next.js 15 (App Router) + TypeScript
- **Styling:** Tailwind CSS + shadcn/ui components
- **Auth:** NextAuth.js (email + Google providers)
- **Chess UI:** react-chessboard + chess.js
- **Payments:** Stripe (checkout + subscriptions)
- **Tests:** vitest
- **ORM:** Prisma (PostgreSQL)

## Chess Engine (`chess-engine/`)

- **Framework:** Python 3.12 + FastAPI
- **Chess:** python-chess + Stockfish (local binary)
- **GPU inference:** RunPod SDK for Leela in production
- **Coach narratives:** Claude API (Anthropic SDK)
- **Tests:** pytest
- **ORM:** SQLAlchemy (PostgreSQL)

## Database

- **Provider:** Railway PostgreSQL
- **Access:** Prisma from website, SQLAlchemy from chess-engine
- **Shared via:** `DATABASE_URL` environment variable

## Security

- NEVER put API keys, tokens, passwords, or secrets in code
- All secrets in environment variables (`.env.local`)
- `.env*` must be in `.gitignore`
- No `console.log` of secrets, even in dev
- Validate and sanitize all user inputs server-side
- Sanitize FEN strings before passing to Stockfish or Leela
- Rate limiting on all public endpoints
- CORS configured strictly (allow only own domain)
- Helmet for security headers
- Parameterized SQL everywhere, never string concatenation
- HTTPS only in production

## Code Rules

- Tests for every feature
- Simple first, no over-engineering
- Mobile responsive from day one
- Git: conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`)
- One branch per feature, merge via PR
- No unused imports, no dead code
- Environment variables for all configuration
