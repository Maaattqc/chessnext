# ChessNext.ai

AI chess coaching app that teaches superhuman positional concepts extracted from Leela Chess Zero's neural network.

## Current Phase

**Phase 1: Build the App** (Weeks 7-18)
Phase 0 completed April 6, 2026 — 4 superhuman concepts validated.

## Key Files

- `docs/PLAN.md` — Business plan, phases, pricing, architecture
- `docs/CONTEXT.md` — Project context, what Leela is, how concept extraction works
- `docs/TECH.md` — Technical conventions, stack, libraries
- `docs/SECURITY.md` — **MANDATORY** security rules. Read before writing any code.
- `docs/TESTING.md` — Testing strategy: unit, integration, E2E, security tests
- `docs/API.md` — API contract between website and chess-engine (endpoints, formats, errors)
- `docs/DATABASE.md` — Database schema (all tables, relations, indexes, plan limits)
- `docs/PROMPTS.md` — Claude API prompt templates for AI coach features
- `docs/DESIGN.md` — Design system (colors, typography, layout, components, board styling)
- `docs/DEPLOYMENT.md` — Railway deployment, env vars, domain setup, first-time setup
- `docs/PHASE0_RESULTS.md` — Phase 0 results: 4 concepts, metrics, positions

## Repo

- GitHub: `Maaattqc/chessnext` (private)
- Domain: `chessnext.ai`

## Structure

```
chessnext/
  website/        Next.js 15 + TypeScript + Tailwind + shadcn/ui
  chess-engine/   Python 3.12 + FastAPI + Stockfish + Leela
  tools/          Offline concept extraction (not deployed)
  CLAUDE.md       This file
  PLAN.md         Business plan
  CONTEXT.md      Project context
  TECH.md         Technical conventions
```
