# API Contract — ChessNext.ai

Contract between website (Next.js) and chess-engine (FastAPI).
Both sides MUST follow this spec exactly.

Base URL: `https://api.chessnext.ai` (prod) / `http://localhost:8000` (dev)
Auth: Bearer token (JWT from NextAuth) in `Authorization` header.
Format: JSON everywhere. Dates in ISO 8601. FEN validated server-side.

---

## Auth

Auth is handled by NextAuth.js on the website side. The chess-engine
does NOT handle auth directly — it receives a validated user ID from
the website via internal API calls.

### `POST /api/auth/magic-link` (website only)

Send a magic link code to the user's email.

```
Request:  { "email": "user@example.com" }
Response: { "ok": true }
Errors:   400 invalid email, 429 rate limited (5/15min)
```

### `POST /api/auth/verify` (website only)

Verify the code and create a session.

```
Request:  { "email": "user@example.com", "code": "123456" }
Response: { "ok": true, "session": "..." }
Errors:   400 invalid/expired code, 429 max attempts
```

---

## Concepts

### `GET /api/concepts`

List all concepts. Free users see 3, paid users see all.

```
Response: {
  "concepts": [
    {
      "id": "uuid",
      "name": "Prophylactic Resilience",
      "summary": "Short 1-line description",
      "difficulty": "advanced",
      "positionCount": 100,
      "locked": false
    }
  ]
}
Query params: ?page=1&limit=20
Auth: optional (unauthenticated = free tier view)
```

### `GET /api/concepts/:id`

Get full concept detail with positions and explanation.

```
Response: {
  "id": "uuid",
  "name": "Prophylactic Resilience",
  "description": "Full multi-paragraph explanation (markdown)",
  "difficulty": "advanced",
  "positions": [
    {
      "fen": "r1bqkb1r/2pppp1p/6pn/pp2n3/P1P5/1P5N/3PPPPP/RNBQKBR1 b Qkq - 3 8",
      "strongMove": "g8",
      "weakMove": "g8",
      "explanation": "Why the strong move is better",
      "arrows": [["h6", "g8"]]
    }
  ],
  "quiz": [
    {
      "fen": "...",
      "correctMove": "Ng8",
      "hints": ["Think about regrouping", "Which piece needs better coordination?"]
    }
  ]
}
Auth: required for locked concepts
Errors: 403 concept locked (upgrade needed), 404 not found
```

### `GET /api/concepts/:id/progress`

Get user's progress on a specific concept.

```
Response: {
  "conceptId": "uuid",
  "score": 0.72,
  "positionsCompleted": 18,
  "positionsTotal": 25,
  "lastReviewed": "2026-04-06T12:00:00Z",
  "nextReview": "2026-04-08T12:00:00Z",
  "streakDays": 5
}
Auth: required
```

### `POST /api/concepts/:id/answer`

Submit an answer to a concept quiz position.

```
Request:  { "fen": "...", "move": "Ng8" }
Response: {
  "correct": true,
  "explanation": "Exactly! Ng8 regroups the knight...",
  "nextPosition": { "fen": "...", "hints": [...] } | null
}
Auth: required
```

---

## Analysis

### `POST /api/analysis/position`

Analyze a single position. Returns Stockfish eval, matched concepts,
and AI coach narrative.

```
Request: {
  "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
  "userRating": 1500
}
Response: {
  "id": "uuid",
  "fen": "...",
  "evaluation": {
    "score": 0.35,
    "bestMove": "e5",
    "bestLine": ["e5", "Nf3", "Nc6"],
    "depth": 24
  },
  "humanMove": {
    "move": "e5",
    "explanation": "At your level, e5 is the most natural and strong response."
  },
  "concepts": [
    {
      "id": "uuid",
      "name": "Central Control",
      "relevance": 0.85,
      "explanation": "This position demonstrates central tension..."
    }
  ],
  "coachNarrative": "In this position, Black should focus on..."
}
Auth: required
Rate limit: 1/day (free), 60/day (Plus), unlimited (Pro/Coach)
Errors: 400 invalid FEN, 429 daily limit reached, 503 engine unavailable
```

### `POST /api/analysis/game`

Analyze a full game (PGN). Root-cause analysis.

```
Request: {
  "pgn": "1. e4 e5 2. Nf3 Nc6...",
  "userColor": "white",
  "userRating": 1500
}
Response: {
  "id": "uuid",
  "moves": [
    {
      "moveNumber": 1,
      "move": "e4",
      "evaluation": 0.35,
      "classification": "good",
      "comment": null
    },
    {
      "moveNumber": 15,
      "move": "Bxf7",
      "evaluation": -1.2,
      "classification": "mistake",
      "comment": "This sacrifice doesn't work because...",
      "rootCause": {
        "conceptId": "uuid",
        "explanation": "The real issue started at move 12..."
      }
    }
  ],
  "summary": "You played a solid opening but the bishop sacrifice on move 15..."
}
Auth: required (Plus+ only)
Rate limit: 5/day (Plus), 20/day (Pro), unlimited (Coach)
Errors: 400 invalid PGN, 403 plan upgrade needed
```

### `GET /api/analysis/history`

Get user's analysis history.

```
Response: {
  "analyses": [
    {
      "id": "uuid",
      "type": "position" | "game",
      "fen": "..." | null,
      "createdAt": "2026-04-06T12:00:00Z",
      "summary": "Short 1-line summary"
    }
  ]
}
Query params: ?page=1&limit=20
Auth: required
```

---

## User

### `GET /api/user/profile`

```
Response: {
  "id": "uuid",
  "email": "user@example.com",
  "plan": "free" | "plus" | "pro" | "coach",
  "rating": 1500,
  "createdAt": "2026-04-06T12:00:00Z",
  "stats": {
    "conceptsCompleted": 12,
    "conceptsTotal": 50,
    "analysesThisMonth": 28,
    "streakDays": 5
  }
}
Auth: required
```

### `PATCH /api/user/profile`

```
Request:  { "rating": 1650 }
Response: { "ok": true }
Auth: required
```

---

## Subscription

### `POST /api/subscription/checkout`

Create a Stripe checkout session.

```
Request:  { "plan": "plus" | "pro" | "coach" }
Response: { "checkoutUrl": "https://checkout.stripe.com/..." }
Auth: required
```

### `GET /api/subscription/status`

```
Response: {
  "plan": "plus",
  "status": "active" | "canceled" | "past_due",
  "currentPeriodEnd": "2026-05-06T12:00:00Z",
  "cancelAtPeriodEnd": false
}
Auth: required
```

### `POST /api/subscription/cancel`

```
Response: { "ok": true, "cancelAtPeriodEnd": true }
Auth: required
```

### `POST /api/webhooks/stripe` (website only)

Stripe webhook handler. No auth header — verified by Stripe signature.

```
Events handled:
  - checkout.session.completed -> activate subscription
  - invoice.paid -> renew subscription
  - invoice.payment_failed -> mark past_due
  - customer.subscription.deleted -> deactivate
```

---

## Error Format

All errors follow this format:

```json
{
  "error": {
    "code": "INVALID_FEN",
    "message": "The provided FEN string is not a valid chess position.",
    "status": 400
  }
}
```

Error codes:
- `INVALID_FEN` (400)
- `INVALID_PGN` (400)
- `VALIDATION_ERROR` (400)
- `UNAUTHORIZED` (401)
- `PLAN_REQUIRED` (403)
- `NOT_FOUND` (404)
- `RATE_LIMITED` (429)
- `ENGINE_UNAVAILABLE` (503)
- `INTERNAL_ERROR` (500)

---

## Internal Communication

Website -> Chess Engine calls are internal (not exposed to users).
Use Railway internal networking: `http://chess-engine.railway.internal:8000`

### `POST /internal/analyze` (chess-engine)

Called by the website's API route, not by the client directly.

```
Headers: X-Internal-Key: <shared secret>
Request: { "fen": "...", "userRating": 1500, "depth": 24 }
Response: { evaluation, concepts, coachNarrative }
```
