# ChessNext.ai — Context for Claude Code

## What are we building?
A chess coaching web app that teaches positional concepts
extracted from Leela Chess Zero's neural network — concepts
that exist at 3800 Elo but have no human name or explanation.

## Why does this work?
DeepMind proved in March 2025 (PNAS paper) that AlphaZero
contains novel chess concepts beyond human knowledge. They
tested 4 world champions who all improved after learning them.
We apply the same method to Leela Chess Zero (open source,
stronger than AlphaZero, transformer-based since 2022).

## What is Leela Chess Zero?
- Open source chess engine inspired by AlphaZero
- Deep neural network (191M params transformer) + MCTS search
- Trained via self-play on 2.5 billion games over 7 years
- We do NOT train it. We download pre-trained weights and
  run inference to extract hidden layer activations.

## How concept extraction works
1. Run positions through Leela, capture hidden layer activations
2. Find "disagreement positions" where old vs new Leela networks
   choose different moves (complex concepts learned late in training)
3. Convex optimization to find concept vectors in activation space
4. Filter: teachable (another net can learn it) + novel (not in human games)
5. Result: clusters of positions sharing the same unnamed pattern
6. We name them, explain them, create puzzles from them

## Tech decisions
- **Next.js + TypeScript** for website/ (I have 5 years web dev experience)
- **Python FastAPI** for chess-engine/ (best for ML and Stockfish)
- **Railway** hosts everything (website + chess-engine + PostgreSQL)
- **NextAuth.js** for auth (no Supabase, less vendor lock-in)
- **RunPod Serverless** for GPU inference in production
- **Stripe** for payments
- **GTX 1080 Ti** local for development
- **Claude Code** builds 99% of the code

## Current phase
Phase 1: Build the App (~90% complete as of April 6, 2026).

Phase 0 completed: 4 superhuman concepts extracted from Lc0 transformer
(15x1024 BT4, 69 Elo gap, 287 disagreements from 10K positions).
See docs/PHASE0_RESULTS.md for full results.

App is deployed and functional:
- Website: Next.js 16 on Railway (22 routes, auth, Stripe, interactive board)
- Chess-engine: FastAPI on Railway (real Stockfish 18 + Claude API coach)
- Database: Railway PostgreSQL (8 tables, 4 concepts seeded)
- 55 tests passing (37 vitest + 18 pytest), 0 vulnerabilities

Remaining for Phase 1: scale to 30-50 concepts (50K positions ready),
wire real game analysis (currently mock), Stripe products when ready to sell.

## Repo structure
```
chessnext/
  website/        Next.js 16 + React 19 + Tailwind 4 + shadcn/ui
  chess-engine/   Python FastAPI + Stockfish 18 + Claude API
  tools/          Offline concept extraction (Lc0 transformer pipeline)
  docs/           All specs (PLAN, API, DATABASE, SECURITY, DESIGN, etc.)
  CLAUDE.md       Entry point for Claude Code
```

## Deployed at
- Website: https://website-production-7ee4.up.railway.app
- Domain: chessnext.ai (to be configured)
