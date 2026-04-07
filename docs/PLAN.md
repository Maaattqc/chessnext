# ChessNext.ai — Execution Plan

## What This Is
A standalone web app that extracts unnamed superhuman positional
concepts from Leela Chess Zero's neural network and sells them
as an AI coaching product. Built solo with Claude Code.

## Based On
DeepMind paper "Bridging the human-AI knowledge gap through
concept discovery and transfer in AlphaZero" (PNAS, March 2025)
- Paper: https://arxiv.org/abs/2310.16410
- Method validated by 4 world champions (Kramnik, Gukesh, Hou Yifan, MVL)
- Nobody has productized this. AlphaZero is proprietary. Gap is open.

## The Product (3 Layers)
1. **Superhuman Concept Teaching** — named patterns from Leela that no human coach has ever taught
2. **Human-Adjusted Evaluation** — the best move at YOUR rating, not the 3800 Elo engine move
3. **Root-Cause Game Analysis** — traces the real positional mistake, not just the tactical symptom

## Architecture
```
chessnext-ai/
  website/        Next.js + NextAuth.js + TypeScript + Tailwind
  chess-engine/   Python FastAPI + Stockfish + ML pipeline
  tools/          Offline concept extraction (not deployed)

Railway Project:
  website         (service 1, auto-deploys from GitHub)
  chess-engine    (service 2, auto-deploys from GitHub)
  PostgreSQL      (one-click database)
```

## Three Providers
- **Railway** — hosts website + chess-engine + PostgreSQL. One dashboard, one bill.
- **RunPod** — GPU for Leela inference. Serverless: pay per second.
- **Stripe** — payments and subscriptions.

## Env Config (5 variables)
```
DATABASE_URL=postgresql://...railway.internal
RUNPOD_API_KEY=rp_xxx
STRIPE_SECRET_KEY=sk_xxx
CLAUDE_API_KEY=sk-ant-xxx
NEXTAUTH_SECRET=xxx
```

## GPU Strategy
- GTX 1080 Ti local for 90%+ of dev work (11GB VRAM, ~9000 nodes/sec)
- RunPod cloud bursts when BT4 transformer net needed ($0.34/hr RTX 4090)
- RunPod Serverless for production user analysis

## Phases

### Phase 0: Validate (Weeks 1-6) — $0 to $50 ✓ COMPLETED Apr 6, 2026
1. ✓ Lc0 transformer (15x1024 BT4) loaded in PyTorch on 1080 Ti
2. ✓ Encoder layer activations captured via forward hooks
3. ✓ 287 disagreements from 10K positions (69 Elo gap, same-run transformers)
4. ✓ PCA + k-means clustering + logistic probes for concept vectors
5. ✓ Filtered by teachability + novelty
6. **GO: 4 clean superhuman concepts. $0 spent. See tools/PHASE0_RESULTS.md**

### Phase 1: Build the App (Weeks 7-18) — $800 to $2,000 ⏳ ~90% Apr 6, 2026
1. ⚠️ Scale to 30-50 concepts (4 done, 50K positions generated, pipeline ready)
2. ✓ Next.js website: auth (magic link), chessboard (Learn/Practice tabs),
   Stripe (checkout + webhooks + cancel + plan locking),
   dashboards (stats, progress, history, settings)
3. ✓ FastAPI chess-engine: real Stockfish 18 + Claude API Sonnet coach
4. ✓ Human-adjusted eval: route + Claude prompt connected
5. ⚠️ Root-cause game analysis: route + PGN page built, results still mock
6. ✓ Deploy on Railway: website + chess-engine + PostgreSQL, master = prod
7. Remaining: scale concepts (run pipeline on 50K), wire real game analysis,
   RunPod Leela for prod (Phase 2), Stripe products when ready to sell

### Phase 2: Launch and Grow (Week 18+) — NOT STARTED
- Weekly free concept blog posts (viral content)
- Chess YouTuber outreach (GothamChess, Naroditsky)
- Product Hunt launch
- GM endorsement (free lifetime access)

## Pricing
- **Free:** 3 concepts, 1 analysis/day
- **Plus ($12-15/mo):** 50+ concepts, unlimited analysis, progress tracking
- **Pro ($30-40/mo):** Plus + weakness detection, priority concepts, export
- **Coach ($60-100/mo):** Pro + bulk student analysis, curriculum builder

## Costs
- Claude Code: $0 (employer pays)
- GM consultant: $0 (DeepMind already validated)
- GPU dev: $0 (1080 Ti local)
- Year 1 total: $2,000 to $5,000
- **Break-even: 8-12 paying users**

## Key Resources
- DeepMind paper: https://www.pnas.org/doi/10.1073/pnas.2406675122
- ArXiv PDF: https://arxiv.org/abs/2310.16410
- Leela + weights: https://lczero.org/
- Lc0 GitHub: https://github.com/LeelaChessZero/lc0
- Python bindings: pip install lczero-bindings
- ChessBench: https://github.com/google-deepmind/searchless_chess
- Lichess DB: https://database.lichess.org/
- Railway: https://railway.app/
- RunPod: https://www.runpod.io/
