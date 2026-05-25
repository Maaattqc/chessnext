<p align="center">
  <strong>ChessNext.ai</strong><br>
  <em>Superhuman chess concepts, decoded for human minds.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-early%20concept-orange" alt="Status: Early Concept" />
  <img src="https://img.shields.io/badge/phase-1%20of%203-blue" alt="Phase 1 of 3" />
  <img src="https://img.shields.io/badge/Next.js-16-black?logo=next.js" alt="Next.js 16" />
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Python-FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Stockfish-18-green" alt="Stockfish 18" />
  <img src="https://img.shields.io/badge/Leela%20Chess%20Zero-BT4%20Transformer-red" alt="LCZero" />
</p>

---

> **Note** — This project is in active development. The core concept extraction pipeline is validated (Phase 0 complete), and the web application is functional. The vision described below is where we're heading.

---

# Vision

*[EN]*

In 2025, DeepMind published a landmark paper in *PNAS*: ["Bridging the human-AI knowledge gap through concept discovery and transfer in AlphaZero"](https://arxiv.org/abs/2310.16410). They proved that AlphaZero contains chess concepts that **no human has ever named or taught** — and that world champions (Kramnik, Gukesh, Hou Yifan, MVL) measurably improved after learning them.

The paper was a proof of concept. AlphaZero is proprietary. Nobody productized the findings.

**ChessNext.ai is the first attempt to bring superhuman chess concepts to every player.**

We apply the same methodology to [Leela Chess Zero](https://lczero.org/) (LCZero) — an open-source engine that learned chess entirely through self-play, accumulating 2.5 billion games over 7 years. Its 185-million-parameter transformer network doesn't calculate like Stockfish. It *intuits* — and some of what it knows has never existed in human chess theory.

We extract those unnamed concepts, translate them into teachable patterns, and deliver them through an AI coaching platform.

*[FR]*

En 2025, DeepMind a publié un article fondateur dans *PNAS* prouvant qu'AlphaZero contient des concepts d'echecs **qu'aucun humain n'a jamais nommes ni enseignes** — et que des champions du monde se sont mesuralement ameliores apres les avoir appris.

L'article etait une preuve de concept. AlphaZero est proprietaire. Personne n'a productise les resultats.

**ChessNext.ai est la premiere tentative de rendre les concepts echiquens surhumains accessibles a tous les joueurs.**

Nous appliquons la meme methodologie a [Leela Chess Zero](https://lczero.org/) (LCZero) — un moteur open source qui a appris les echecs entierement par self-play, accumulant 2,5 milliards de parties sur 7 ans. Son reseau transformer de 185 millions de parametres ne calcule pas comme Stockfish. Il *intuitionne* — et certaines de ses connaissances n'ont jamais existe dans la theorie echiquenne humaine.

Nous extrayons ces concepts sans nom, les traduisons en patterns enseignables et les livrons via une plateforme de coaching IA.

---

# The Core Insight

```
  STOCKFISH                          LEELA CHESS ZERO (LCZero)
  ──────────                         ────────────────────────────
  Brute-force search                 Neural network intuition
  Evaluates 100M+ positions/sec      Evaluates positions holistically
  Knows WHAT is best                 Knows WHY — implicitly
  No learning, pure calculation      Self-taught via 2.5B games
  Superhuman through depth           Superhuman through understanding
                                     
  "The best move is Nf3."            "Something about this position
                                      feels right — and I can't
                                      tell you why in words."

                     ChessNext.ai
                     ─────────────
                     Extracts the "why" from LCZero
                     Names it, explains it, teaches it
```

Stockfish is a calculator. LCZero is closer to an alien grandmaster who learned chess from scratch and developed its own positional theory. Some of that theory overlaps with human knowledge. Some of it doesn't. **The part that doesn't is what we're after.**

---

# How It Works

```
  LCZero Strong Net (Elo ~3600)      LCZero Weak Net (Elo ~3530)
  ┌─────────────────────────┐        ┌─────────────────────────┐
  │  15-layer BT4            │        │  Same architecture       │
  │  Transformer             │        │  Earlier training         │
  │  185M parameters         │        │  checkpoint (69 Elo gap)  │
  └────────────┬─────────────┘        └────────────┬──────────────┘
               │                                   │
               ▼                                   ▼
       ┌───────────────────────────────────────────────┐
       │         Run 10,000+ positions through both     │
       │         Compare: where do they DISAGREE?       │
       │         (Only 2.9% of positions — subtle gaps) │
       └───────────────────────┬───────────────────────┘
                               │
                               ▼
       ┌───────────────────────────────────────────────┐
       │  Capture hidden-layer activations (327,680 dim)│
       │  PCA reduction -> 150 dimensions               │
       │  K-means clustering -> concept groups          │
       │  Logistic probes -> concept vectors            │
       └───────────────────────┬───────────────────────┘
                               │
                               ▼
       ┌───────────────────────────────────────────────┐
       │  Filter by:                                    │
       │    - Teachability (can another net learn it?)  │
       │    - Novelty (is it absent from human games?)  │
       │  Result: named, teachable superhuman concepts  │
       └───────────────────────────────────────────────┘
```

The key insight from DeepMind's methodology: compare two networks from the **same training run** with a small Elo gap. Where they disagree, the stronger network has learned something the weaker hasn't yet — and those disagreement positions cluster into coherent **concepts**.

---

# Phase 0 Results — Validated

Four superhuman concepts extracted from LCZero's transformer network. Each was filtered for teachability (a separate network can learn to recognize it) and novelty (the pattern doesn't appear in standard human chess theory).

| Concept | Name | Positions | Core Insight |
|---------|------|-----------|--------------|
| 1 | Prophylactic Resilience | 100 | Knight retreats and early king centralization preserve flexibility when routine development fails |
| 2 | Dynamic f-file Counterattack | 68 | Central f-pawn pushes create dynamic play that passive wing expansions miss entirely |
| 3 | King Safety Over Material | 26 | Prophylactic rook moves outperform immediate pawn captures — structural safety > material |
| 4 | Material Imbalance Compensation | 43 | Sacrificed material carries far more compensation than surface evaluation suggests |

**Example — Concept 3 (King Safety Over Material):**

```
  Position: rnbqk2r/p1ppn2p/1p3pp1/2b5/4p2P/P1P1PP1N/1PQPB1P1/RNB1K2R w KQkq

  8  r n b q k . . r       Strong network plays:  Rg1
  7  p . p p n . . p         (prophylactic rook move,
  6  . p . . . p p .          shores up the kingside)
  5  . . b . . . . .
  4  . . . . p . . P       Weak network plays:    fxe4
  3  P . P . P P . N         (wins a pawn immediately)
  2  . P Q P B . P .
  1  R N B . K . . R       The strong net forgoes material
     a b c d e f g h        for structural safety.
                             No human coach teaches this.
```

Full results with all positions, metrics, and methodology: [`docs/PHASE0_RESULTS.md`](docs/PHASE0_RESULTS.md)

---

# The Product — Three Layers

| Layer | What | Status |
|-------|------|--------|
| **Superhuman Concept Teaching** | Named patterns from LCZero that no human coach has ever taught. Interactive board, learn/practice tabs, concept explanations powered by Claude API. | Functional (4 concepts, scaling to 50+) |
| **Human-Adjusted Evaluation** | The best move at *your* rating — not the 3800 Elo engine move. A 1200-rated player shouldn't play a move requiring 15 moves of precise calculation. | Functional (Stockfish + Claude coaching) |
| **Root-Cause Game Analysis** | Upload a PGN. Instead of flagging blunders, traces the *positional* mistake that caused the tactical collapse. | In progress (routes built, analysis mock) |

---

# Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React 19, TypeScript 5, Tailwind CSS 4, shadcn/ui |
| Auth | NextAuth.js v5 (magic link via Resend) |
| Chess Engine API | Python 3.12, FastAPI, Stockfish 18, Claude API (coaching narratives) |
| ML Pipeline | LCZero BT4 Transformer (185M params), PyTorch, PCA, k-means, logistic probes |
| Database | PostgreSQL (Prisma ORM, 8 tables) |
| GPU | GTX 1080 Ti (dev, ~9,000 nodes/sec) / RunPod Serverless RTX 4090 (prod) |
| Payments | Stripe (checkout, webhooks, subscription management) |
| Hosting | Railway (website + chess-engine + PostgreSQL, auto-deploy from GitHub) |
| Tests | 55 passing (37 Vitest + 18 Pytest) |

---

# Repository Structure

```
chessnext/
├── website/              Next.js 16 — auth, interactive board, Stripe,
│   ├── src/                dashboards, concept browser, game analysis
│   │   ├── app/            22 routes (concepts, analysis, pricing, settings...)
│   │   ├── components/     UI components (navbar, footer, chessboard, shadcn/ui)
│   │   └── lib/            Utilities (FEN/PGN validation, rate limiting, Stripe)
│   └── prisma/             Schema + migrations + seed data
│
├── chess-engine/         Python FastAPI — real Stockfish 18 analysis,
│   ├── analysis.py         Claude-powered coaching narratives,
│   ├── coach.py            human-adjusted move recommendations
│   └── main.py
│
├── tools/                Offline ML pipeline (not deployed)
│   ├── leela_transformer.py   LCZero BT4 loader (Smolgen, attention policy, WDL)
│   ├── pipeline_v4.py         Full extraction: positions -> disagreements -> concepts
│   ├── mcts_fast.py           Monte Carlo Tree Search for position generation
│   ├── name_concepts.py       Claude-assisted concept naming
│   └── named_concepts.json    Extracted concept data with positions
│
└── docs/                 Specs: plan, API contracts, database schema,
                            security, design system, deployment, testing
```

---

# Status and Roadmap

**Phase 0 — Validate** — Complete  
Extracted 4 superhuman concepts from LCZero. $0 spent. Pipeline works on a consumer GPU.

**Phase 1 — Build the App** — ~90% complete  
Web app is deployed and functional. Auth, Stripe, interactive board, concept browser, Stockfish analysis, Claude coaching. Remaining: scale to 50+ concepts, wire real game analysis, production GPU inference.

**Phase 2 — Launch and Grow** — Not started  
Weekly free concept posts (content marketing), chess YouTuber outreach, Product Hunt launch, GM endorsement program.

---

# Getting Started

```bash
# Website
cd website
npm install
npx prisma generate
npm run dev

# Chess Engine
cd chess-engine
pip install -r requirements.txt
uvicorn main:app --reload
```

Required environment variables: `DATABASE_URL`, `CLAUDE_API_KEY`, `NEXTAUTH_SECRET`, `STRIPE_SECRET_KEY`, `RUNPOD_API_KEY`

---

# References

- DeepMind paper: [Bridging the human-AI knowledge gap through concept discovery and transfer in AlphaZero](https://arxiv.org/abs/2310.16410) (PNAS, 2025)
- [Leela Chess Zero](https://lczero.org/) — open-source neural network chess engine
- [Stockfish](https://stockfishchess.org/) — strongest traditional chess engine

---

# Author

**Mathieu Fournier** · mathieufournierqc@outlook.com — [@Maaattqc](https://github.com/Maaattqc)

---

<sub>ChessNext.ai is not affiliated with DeepMind, Leela Chess Zero, or Stockfish. This project applies published research methodology to open-source tools.</sub>
