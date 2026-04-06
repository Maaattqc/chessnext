# Security Rules — ChessNext.ai

These rules are mandatory for ALL code in this project. No exceptions.
Claude Code must follow every rule below when writing or reviewing code.

---

## 1. Secrets Management

- NEVER hardcode API keys, tokens, passwords, database URLs, or any secret in source code
- NEVER commit `.env`, `.env.local`, `.env.production`, or any file containing secrets
- NEVER log secrets with `console.log`, `print()`, `logger.info()`, or any output method
- NEVER include secrets in error messages, stack traces, or API responses
- NEVER put secrets in URL query parameters (they get logged in server access logs)
- All secrets go in environment variables loaded from `.env.local` (dev) or Railway/platform env vars (prod)
- Verify `.env*` is in `.gitignore` before every commit that touches config

## 2. Input Validation

- Validate ALL user input server-side with zod (TypeScript) or pydantic (Python)
- NEVER trust client-side validation alone — it can be bypassed
- FEN strings: validate format with regex AND verify with chess.js/python-chess before passing to any engine
- Reject FEN strings longer than 100 characters
- PGN input: parse with chess.js/python-chess, reject if invalid, limit to 500 moves
- Email: validate format with zod `.email()`, normalize (lowercase, trim)
- Pagination: enforce max page size (100 items), validate page number is positive integer
- File uploads: if ever added, validate MIME type server-side, limit size to 5MB, never execute uploaded files
- Strip HTML from all text inputs to prevent XSS storage
- Use `encodeURIComponent()` when inserting user data into URLs

## 3. Authentication & Sessions

- Auth is magic link only (Resend email with verification code)
- Verification codes: 6 digits, expire after 10 minutes, single use, max 3 attempts
- Sessions: use NextAuth.js with JWT strategy stored in httpOnly secure cookies
- Set `sameSite: 'lax'` on all cookies
- Set `secure: true` on all cookies in production
- Session expiry: 30 days, with sliding window refresh
- On logout, invalidate the session server-side (not just delete client cookie)
- Rate limit login attempts: max 5 per email per 15 minutes

## 4. API Security

- Rate limit ALL public endpoints with Upstash Redis:
  - Auth endpoints: 5 requests/15 min per IP
  - Analysis endpoints: 10 requests/min per user (free), 60/min (paid)
  - General API: 100 requests/min per IP
- Return 429 Too Many Requests with `Retry-After` header when rate limited
- CORS: allow only `chessnext.ai` and `localhost:3000` (dev) — never `*`
- Set security headers via middleware:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://api.chessnext.ai`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- All API responses: never expose internal error details in production (return generic 500 message)
- Never expose database IDs directly — use UUIDs for all public-facing identifiers

## 5. Database Security

- ALWAYS use parameterized queries — Prisma and SQLAlchemy do this by default, never bypass with raw SQL string concatenation
- If raw SQL is absolutely needed, use `prisma.$queryRaw` with template literals (auto-parameterized) or SQLAlchemy `text()` with bound parameters
- Never interpolate user input into SQL strings with f-strings, `format()`, or `+` concatenation
- Database user should have minimal permissions (no DROP, no CREATE in production)
- Enable SSL for database connections in production (`?sslmode=require` in DATABASE_URL)
- Prisma: always use `select` or `include` to avoid leaking unnecessary fields (never return full user records with password hashes or internal fields)

## 6. Chess Engine Security

- FEN validation pipeline before any engine call:
  1. Check string length (< 100 chars)
  2. Check format with regex: `^[rnbqkpRNBQKP1-8/]+ [wb] [KQkq-]+ [a-h1-8-]+ \d+ \d+$`
  3. Parse with python-chess `chess.Board(fen)` — reject if it throws
  4. Verify board is legal: correct number of kings, no pawns on rank 1/8
- Stockfish process: run with resource limits (max 10s per analysis, max 512MB memory)
- Never pass unsanitized strings to shell commands — always use subprocess with argument lists, never `shell=True`
- RunPod API calls: validate response structure before processing, handle timeouts (30s max)
- Claude API calls: sanitize the FEN and position context before including in prompts — never include raw user text in system prompts without escaping

## 7. Payment Security (Stripe)

- NEVER handle raw credit card numbers — Stripe Checkout and Elements do this
- Verify webhook signatures on all Stripe webhook endpoints using `stripe.webhooks.constructEvent()`
- Validate that the payment amount matches the expected plan price server-side — never trust client-provided amounts
- Check subscription status server-side before granting access to paid features — never trust client state
- Store only Stripe customer ID and subscription ID in database, never payment details
- Use idempotency keys for all Stripe API calls that create or modify resources

## 8. XSS Prevention

- React/Next.js escapes output by default — never use `dangerouslySetInnerHTML` unless absolutely necessary
- If `dangerouslySetInnerHTML` is needed (e.g., for rendered MDX), sanitize with DOMPurify first
- Never render user-provided content as raw HTML
- User-generated chess annotations: treat as plain text, escape before display
- CSP headers (see section 4) provide defense in depth

## 9. Dependency Security

- Run `npm audit` and `pip audit` before each release
- Never install packages from untrusted sources
- Pin major versions in package.json (use `^` for minor/patch updates only)
- Review changelogs before major dependency upgrades
- If a dependency has a known vulnerability and no fix is available, find an alternative

## 10. Logging & Error Handling

- Log security events: failed login attempts, rate limit hits, invalid FEN submissions, payment failures
- Never log: passwords, tokens, API keys, full credit card numbers, session tokens
- In production: return generic error messages to users ("Something went wrong"), log full details server-side only
- Use structured logging (JSON format) for easier monitoring in Sentry
- Set up Sentry alerts for: 5xx error spikes, auth failure spikes, rate limit abuse patterns

## 11. Infrastructure

- HTTPS only — redirect all HTTP to HTTPS in production
- Railway auto-provisions SSL — verify it's active
- Keep Node.js and Python updated to latest LTS/stable
- Database backups: Railway provides daily backups — verify they're enabled
- Environment separation: never share secrets between dev/staging/production
- DNS: enable DNSSEC on chessnext.ai if registrar supports it

## 12. Checklist Before Every Deploy

- [ ] No secrets in code (`git grep -i "sk_live\|api_key\|password\|secret" -- ':!.env*'`)
- [ ] `.env*` files are in `.gitignore`
- [ ] All user inputs validated with zod/pydantic
- [ ] Rate limiting active on new endpoints
- [ ] `npm audit` / `pip audit` clean (no critical vulnerabilities)
- [ ] New API endpoints return generic errors in production
- [ ] FEN inputs go through the validation pipeline
- [ ] Stripe webhooks verify signatures
- [ ] No `shell=True` in subprocess calls
- [ ] CORS whitelist hasn't been accidentally broadened
