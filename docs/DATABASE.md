# Database Schema — ChessNext.ai

Railway PostgreSQL. Prisma ORM (website), SQLAlchemy (chess-engine).
All IDs are UUIDs. All timestamps are UTC. Soft delete where noted.

---

## Tables

### users

The central user table. Managed by NextAuth + custom fields.

```sql
users
  id              UUID        PK, default gen_random_uuid()
  email           TEXT        UNIQUE, NOT NULL
  plan            TEXT        NOT NULL, default 'free'  -- free|plus|pro|coach
  rating          INT         default 1500              -- self-reported chess rating
  stripe_customer_id  TEXT    UNIQUE, nullable
  created_at      TIMESTAMPTZ default now()
  updated_at      TIMESTAMPTZ default now()
```

### sessions

NextAuth session management (JWT strategy, but store for revocation).

```sql
sessions
  id              UUID        PK
  user_id         UUID        FK -> users.id, NOT NULL
  expires_at      TIMESTAMPTZ NOT NULL
  created_at      TIMESTAMPTZ default now()
```

### verification_tokens

Magic link codes for email auth.

```sql
verification_tokens
  id              UUID        PK
  email           TEXT        NOT NULL
  code            TEXT        NOT NULL            -- 6-digit code
  expires_at      TIMESTAMPTZ NOT NULL            -- 10 minutes from creation
  attempts        INT         default 0           -- max 3
  used            BOOLEAN     default false
  created_at      TIMESTAMPTZ default now()

INDEX: (email, code)
```

### subscriptions

Stripe subscription state. Source of truth for plan access.

```sql
subscriptions
  id                  UUID        PK
  user_id             UUID        FK -> users.id, UNIQUE, NOT NULL
  stripe_subscription_id  TEXT    UNIQUE, NOT NULL
  plan                TEXT        NOT NULL          -- plus|pro|coach
  status              TEXT        NOT NULL          -- active|canceled|past_due
  current_period_start TIMESTAMPTZ NOT NULL
  current_period_end   TIMESTAMPTZ NOT NULL
  cancel_at_period_end BOOLEAN    default false
  created_at          TIMESTAMPTZ default now()
  updated_at          TIMESTAMPTZ default now()
```

### concepts

Chess concepts extracted from Leela. Populated by the tools/ pipeline.

```sql
concepts
  id              UUID        PK
  slug            TEXT        UNIQUE, NOT NULL      -- url-friendly: "prophylactic-resilience"
  name            TEXT        NOT NULL              -- "Prophylactic Resilience"
  summary         TEXT        NOT NULL              -- 1-line description
  description     TEXT        NOT NULL              -- full markdown explanation
  difficulty      TEXT        NOT NULL              -- beginner|intermediate|advanced
  position_count  INT         NOT NULL
  sort_order      INT         default 0
  is_free         BOOLEAN     default false         -- true = available to free users
  created_at      TIMESTAMPTZ default now()
  updated_at      TIMESTAMPTZ default now()
```

### concept_positions

Individual positions within a concept. Each has a "right" move and explanation.

```sql
concept_positions
  id              UUID        PK
  concept_id      UUID        FK -> concepts.id, NOT NULL
  fen             TEXT        NOT NULL
  strong_move     TEXT        NOT NULL              -- UCI format: "h6g8"
  weak_move       TEXT        NOT NULL              -- what the weaker net plays
  explanation     TEXT        NOT NULL              -- why strong move is better
  arrows          JSONB       default '[]'          -- [["h6","g8"]] for board display
  sort_order      INT         default 0
  created_at      TIMESTAMPTZ default now()

INDEX: (concept_id, sort_order)
```

### concept_progress

User's learning progress per concept. Drives spaced repetition.

```sql
concept_progress
  id              UUID        PK
  user_id         UUID        FK -> users.id, NOT NULL
  concept_id      UUID        FK -> concepts.id, NOT NULL
  score           FLOAT       default 0.0           -- 0.0 to 1.0
  positions_completed INT     default 0
  correct_streak  INT         default 0
  last_reviewed   TIMESTAMPTZ nullable
  next_review     TIMESTAMPTZ nullable              -- spaced repetition schedule
  created_at      TIMESTAMPTZ default now()
  updated_at      TIMESTAMPTZ default now()

UNIQUE: (user_id, concept_id)
INDEX: (user_id, next_review)  -- "what should I review today?"
```

### analyses

Saved position/game analyses.

```sql
analyses
  id              UUID        PK
  user_id         UUID        FK -> users.id, NOT NULL
  type            TEXT        NOT NULL              -- position|game
  fen             TEXT        nullable              -- for position analysis
  pgn             TEXT        nullable              -- for game analysis
  user_color      TEXT        nullable              -- white|black (game only)
  result          JSONB       NOT NULL              -- full analysis result
  created_at      TIMESTAMPTZ default now()

INDEX: (user_id, created_at DESC)
```

### daily_usage

Track daily usage for rate limiting and quotas.

```sql
daily_usage
  id              UUID        PK
  user_id         UUID        FK -> users.id, NOT NULL
  date            DATE        NOT NULL
  position_analyses INT       default 0
  game_analyses     INT       default 0
  created_at      TIMESTAMPTZ default now()

UNIQUE: (user_id, date)
```

---

## Relationships

```
users
  ├── sessions (1:N)
  ├── subscriptions (1:1)
  ├── concept_progress (1:N)
  ├── analyses (1:N)
  └── daily_usage (1:N)

concepts
  ├── concept_positions (1:N)
  └── concept_progress (1:N)
```

---

## Plan Limits

Enforced in application code, not database constraints.

| Plan  | Concepts | Position analyses/day | Game analyses/day |
|-------|----------|-----------------------|-------------------|
| free  | 3        | 1                     | 0                 |
| plus  | all      | 60                    | 5                 |
| pro   | all      | unlimited             | 20                |
| coach | all      | unlimited             | unlimited         |

---

## Migrations

- Use Prisma Migrate for schema changes (`npx prisma migrate dev`)
- Never modify production database directly
- Every migration must be reversible
- Seed script for concepts data: `prisma/seed.ts`

## Indexes Summary

```
users:              (email) UNIQUE
subscriptions:      (user_id) UNIQUE, (stripe_subscription_id) UNIQUE
verification_tokens: (email, code)
concepts:           (slug) UNIQUE
concept_positions:  (concept_id, sort_order)
concept_progress:   (user_id, concept_id) UNIQUE, (user_id, next_review)
analyses:           (user_id, created_at DESC)
daily_usage:        (user_id, date) UNIQUE
```
