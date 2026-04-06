# Testing Strategy — ChessNext.ai

Every feature requires tests. No PR merges without passing tests.

---

## Test Types

### 1. Unit Tests

Test individual functions and components in isolation.

**Website (vitest):**
- Utility functions: FEN validation, move formatting, Elo calculations
- Zod schemas: verify valid/invalid inputs for all API schemas
- React components: render with mock data, verify output (React Testing Library)
- Zustand stores: test state transitions (board state, analysis state)
- Stripe helpers: price calculations, plan checks
- Auth logic: token validation, session expiry checks

**Chess Engine (pytest):**
- FEN sanitization: valid positions pass, malformed/malicious strings rejected
- Stockfish wrapper: correct eval parsing, timeout handling
- Concept matching: given activations, correct concept identified
- Claude prompt builder: output format is valid, no user input injection
- API schemas: pydantic model validation

**Rules:**
- One test file per source file: `utils.ts` -> `utils.test.ts`
- Test file lives next to source file, not in a separate folder
- Each test should be independent — no shared mutable state
- Mock external services (Stripe, Resend, RunPod, Claude API, Stockfish)
- Never mock the function you're testing

### 2. Integration Tests

Test how modules work together, with real database and real API routes.

**Website (vitest):**
- API routes: test full request -> response cycle with test database
- Auth flow: magic link generation -> verification -> session creation
- Stripe webhooks: receive event -> update subscription in database
- Protected routes: unauthenticated -> redirect, authenticated -> render

**Chess Engine (pytest):**
- Full analysis pipeline: FEN in -> Stockfish eval + concept match -> JSON out
- Database queries: create user, store analysis, retrieve history
- Rate limiting: verify requests are counted and blocked correctly

**Rules:**
- Use a test database (separate Railway PostgreSQL or SQLite for speed)
- Reset database between test suites (not between individual tests — too slow)
- Use real HTTP requests to API routes (supertest / httpx)
- Environment: `NODE_ENV=test` / `TESTING=1` to disable external services

### 3. End-to-End Tests (E2E)

Test full user flows in a real browser.

**Tool: Playwright**

**Critical flows to test:**
- Sign up: enter email -> receive magic link -> click -> logged in
- Concept browsing: view concept list -> click concept -> see positions + explanation
- Analysis: paste FEN -> submit -> loading state -> see evaluation + concepts
- Subscription: click upgrade -> Stripe checkout -> return -> access unlocked
- Responsive: same flows on mobile viewport (375px width)

**Rules:**
- Only test critical user paths — not every button and link
- Run against a staging environment, not production
- Use Playwright fixtures for auth state (don't re-login in every test)
- Maximum 20 E2E tests total — they're slow and fragile, keep them focused
- Run E2E on CI before merge to master, not on every commit

### 4. Security Tests

Verify the rules in SECURITY.md are enforced.

**Automated (in unit/integration tests):**
- FEN injection: submit malicious FEN strings, verify rejection
- SQL injection: submit `'; DROP TABLE users; --` in all text fields, verify parameterized queries prevent it
- XSS: submit `<script>alert(1)</script>` in all text inputs, verify it's escaped on render
- Auth bypass: access protected endpoints without token, verify 401
- Rate limiting: send burst of requests, verify 429 after limit
- CORS: send request from unauthorized origin, verify rejection
- Stripe webhook: send unsigned webhook, verify rejection

**Manual (before each release):**
- Run `npm audit` and `pip audit`
- Run `git grep -i "sk_live\|api_key\|password\|secret" -- ':!.env*' ':!*.md'`
- Review CSP headers with browser dev tools
- Verify HTTPS redirect on production URL

## Test Configuration

### Website (`website/`)

```
vitest.config.ts
- Environment: jsdom (for component tests) or node (for API tests)
- Setup file: loads test env vars from .env.test
- Coverage: aim for 80%+ on utilities and API routes
- Timeout: 10s per test (30s for integration)
```

### Chess Engine (`chess-engine/`)

```
pytest.ini / pyproject.toml
- Markers: @pytest.mark.unit, @pytest.mark.integration, @pytest.mark.slow
- Fixtures: test_db, mock_stockfish, mock_runpod, mock_claude
- Coverage: aim for 80%+ on core analysis logic
- Timeout: 10s per test (60s for integration with Stockfish)
```

### E2E (`e2e/`)

```
playwright.config.ts
- Browsers: chromium only (add firefox/webkit later)
- Base URL: http://localhost:3000 (dev) or staging URL
- Retries: 1 (flaky tests get one retry)
- Screenshots: on failure only
```

## CI Pipeline (GitHub Actions)

```
On push to dev:
  1. Lint (eslint + ruff)
  2. Type check (tsc --noEmit + mypy)
  3. Unit tests (vitest + pytest)
  4. Integration tests (vitest + pytest with test DB)

On PR to master:
  All of the above, plus:
  5. E2E tests (Playwright)
  6. Security audit (npm audit + pip audit)
  7. Build verification (next build + docker build)
```

## Naming Conventions

```
# Unit test
describe("validateFEN", () => {
  it("accepts valid starting position", () => { ... })
  it("rejects FEN with 3 kings", () => { ... })
  it("rejects FEN longer than 100 chars", () => { ... })
})

# Python
def test_validate_fen_starting_position(): ...
def test_validate_fen_rejects_three_kings(): ...
def test_validate_fen_rejects_long_string(): ...
```

Pattern: `test_[function]_[scenario]` or `it("[verb]s [expected behavior]")`

## What NOT to Test

- Framework internals (Next.js routing, Prisma query builder)
- Third-party library behavior (chess.js move generation)
- Styling/layout (use visual review instead)
- One-off scripts in `tools/` (concept extraction pipeline)
- Generated code (`net_pb2.py`)
