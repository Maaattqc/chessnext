# ChessNext.ai ♟️

> AI chess coaching platform that teaches superhuman positional concepts extracted from Leela Chess Zero's neural network.
>
> Plateforme d'entraînement aux échecs par IA qui enseigne des concepts positionnels surhumains extraits du réseau neuronal de Leela Chess Zero.

## 🚀 Overview / Aperçu

**[EN]** ChessNext.ai is a commercial web application that extracts *unnamed superhuman positional concepts* from Leela Chess Zero (Lc0) and delivers them as an AI coaching product. Based on the DeepMind paper ["Bridging the human-AI knowledge gap through concept discovery and transfer in AlphaZero"](https://arxiv.org/abs/2310.16410) (PNAS, 2025) — validated by 4 world champions (Kramnik, Gukesh, Hou Yifan, MVL) — this is the first productization of superhuman chess concept extraction.

**[FR]** ChessNext.ai est une application web commerciale qui extrait des *concepts positionnels surhumains non-nommés* depuis Leela Chess Zero (Lc0) et les propose sous forme de coaching IA. Basé sur l'article DeepMind validé par 4 champions du monde — c'est la première mise en produit de l'extraction de concepts d'échecs surhumains.

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js, TypeScript, Tailwind CSS, NextAuth.js |
| **Chess Engine API** | Python, FastAPI, Stockfish |
| **ML Pipeline** | Leela Chess Zero, custom concept extraction, neural network probing |
| **Database** | PostgreSQL (Railway) |
| **GPU Inference** | Local GTX 1080 Ti (dev) / RunPod Serverless RTX 4090 (prod) |
| **AI Coach** | Claude API for natural language explanations |
| **Payments** | Stripe subscriptions |
| **Hosting** | Railway (auto-deploy from GitHub) |
| **Domain** | chessnext.ai |

## 🧠 Technical Highlights / Défis Techniques

- **Superhuman concept extraction** — probing Lc0's neural network to identify positional patterns that no human chess player or coach has ever named
- **3-layer product architecture** — (1) superhuman concept teaching, (2) human-adjusted evaluation at YOUR rating, (3) root-cause game analysis tracing positional mistakes
- **Hybrid GPU strategy** — local GTX 1080 Ti for 90%+ of development (~9,000 nodes/sec), RunPod cloud bursts for BT4 transformer inference ($0.34/hr)
- **Dual-service deployment** — Next.js website + Python FastAPI chess engine as separate Railway services with internal networking
- **Phase 0 validated** — 4 superhuman concepts discovered and verified before building the product

## ✨ Features / Fonctionnalités

- 🎯 **Superhuman Concepts** — Named patterns from Leela that no human coach has ever taught
- 📊 **Human-Adjusted Evaluation** — The best move at *your* rating, not the 3800 Elo engine move
- 🔍 **Root-Cause Analysis** — Traces the real positional mistake, not just the tactical symptom
- 🌍 **Internationalized** — Multi-language support via Next.js messages
- 💳 **Subscription model** — Tiered plans via Stripe

## 📁 Architecture

```
chessnext/
├── website/          # Next.js + NextAuth.js + TypeScript + Tailwind
├── chess-engine/     # Python FastAPI + Stockfish + ML pipeline
├── tools/            # Offline concept extraction scripts (Lc0 probing)
└── docs/             # Plan, context, security, API contracts, design system
```

## 📦 Installation

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

Requires `DATABASE_URL`, `RUNPOD_API_KEY`, `STRIPE_SECRET_KEY`, `CLAUDE_API_KEY`, `NEXTAUTH_SECRET` environment variables.

## 👤 Author / Auteur

**Mathieu Fournier** — [@Maaattqc](https://github.com/Maaattqc)
