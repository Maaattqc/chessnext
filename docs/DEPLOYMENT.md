# Deployment — ChessNext.ai

Everything runs on Railway. One project, multiple services.

---

## Railway Project Structure

```
Railway Project: chessnext
  ├── website          (Next.js, auto-deploy from GitHub /website)
  ├── chess-engine     (FastAPI, auto-deploy from GitHub /chess-engine)
  └── PostgreSQL       (managed database, one-click provision)
```

## Services

### website (Next.js)

```
Source:         GitHub repo, root directory: /website
Build command:  npm run build
Start command:  npm start
Port:           3000
Domain:         chessnext.ai (custom domain)
                chessnext-website.up.railway.app (Railway default)
```

### chess-engine (FastAPI)

```
Source:         GitHub repo, root directory: /chess-engine
Build command:  pip install -r requirements.txt
Start command:  uvicorn main:app --host 0.0.0.0 --port 8000
Port:           8000
Domain:         api.chessnext.ai (custom domain)
                chessnext-engine.up.railway.app (Railway default)
Internal:       chess-engine.railway.internal:8000 (for website -> engine calls)
```

### PostgreSQL

```
Provisioned via Railway one-click.
Connection: DATABASE_URL (auto-injected by Railway)
SSL: required in production
Backups: Railway daily automatic backups
```

---

## Environment Variables

### website

```
DATABASE_URL=postgresql://...         # Railway auto-injects
NEXTAUTH_URL=https://chessnext.ai     # Production URL
NEXTAUTH_SECRET=xxx                   # Generate: openssl rand -base64 32
RESEND_API_KEY=re_xxx                 # From resend.com dashboard
STRIPE_SECRET_KEY=sk_live_xxx         # From Stripe dashboard
STRIPE_WEBHOOK_SECRET=whsec_xxx       # From Stripe webhook config
STRIPE_PRICE_PLUS=price_xxx           # Stripe price ID for Plus plan
STRIPE_PRICE_PRO=price_xxx            # Stripe price ID for Pro plan
STRIPE_PRICE_COACH=price_xxx          # Stripe price ID for Coach plan
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_xxx
NEXT_PUBLIC_POSTHOG_KEY=phc_xxx       # From PostHog dashboard
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
SENTRY_DSN=https://xxx@sentry.io/xxx  # From Sentry dashboard
CHESS_ENGINE_URL=http://chess-engine.railway.internal:8000
CHESS_ENGINE_INTERNAL_KEY=xxx         # Shared secret for internal calls
```

### chess-engine

```
DATABASE_URL=postgresql://...         # Railway auto-injects
RUNPOD_API_KEY=rp_xxx                # From RunPod dashboard
CLAUDE_API_KEY=sk-ant-xxx            # From Anthropic console
CHESS_ENGINE_INTERNAL_KEY=xxx         # Must match website's value
SENTRY_DSN=https://xxx@sentry.io/xxx
STOCKFISH_PATH=/usr/bin/stockfish     # Installed in Docker image
```

---

## Deploy Flow

```
Development:
  git push origin dev                 # Push to dev branch
  -> Railway auto-deploys preview     # Test on preview URL

Production:
  PR from dev -> master               # Create pull request
  -> Review + merge                   # Merge to master
  -> Railway auto-deploys production  # Live on chessnext.ai
```

Railway watches the GitHub repo. Every push triggers a build.
- Pushes to `dev` -> preview deployment
- Pushes to `master` -> production deployment

---

## First-Time Setup

### 1. Railway

```bash
# Install Railway CLI (optional, dashboard works too)
npm install -g @railway/cli

# Login
railway login

# Create project
railway init

# Add PostgreSQL
# -> Railway dashboard -> New -> Database -> PostgreSQL

# Add website service
# -> Railway dashboard -> New -> GitHub Repo -> select chessnext -> root: /website

# Add chess-engine service
# -> Railway dashboard -> New -> GitHub Repo -> select chessnext -> root: /chess-engine

# Set environment variables
# -> Railway dashboard -> each service -> Variables tab
```

### 2. Domain

```
In Railway dashboard -> website service -> Settings -> Domains:
  1. Add custom domain: chessnext.ai
  2. Railway provides CNAME target
  3. In domain registrar: add CNAME record pointing to Railway

In Railway dashboard -> chess-engine service -> Settings -> Domains:
  1. Add custom domain: api.chessnext.ai
  2. Same CNAME process
```

### 3. Stripe

```
1. Create Stripe account at stripe.com
2. Create 3 products (Plus, Pro, Coach) with monthly prices
3. Copy price IDs to environment variables
4. Set up webhook endpoint: https://chessnext.ai/api/webhooks/stripe
5. Copy webhook signing secret to STRIPE_WEBHOOK_SECRET
```

### 4. Resend

```
1. Create Resend account at resend.com
2. Add domain chessnext.ai and verify DNS records
3. Copy API key to RESEND_API_KEY
```

### 5. Database Migration

```bash
cd website
npx prisma migrate deploy    # Run migrations on production
npx prisma db seed           # Seed concepts data
```

---

## Monitoring

- **Sentry:** errors and performance at sentry.io
- **Railway:** logs and metrics in Railway dashboard
- **PostHog:** user analytics at app.posthog.com
- **Stripe:** payment events at dashboard.stripe.com
- **Upstash:** Redis metrics at console.upstash.com

## Rollback

```
Railway dashboard -> service -> Deployments tab
  -> Click on previous deployment -> Redeploy
```

Railway keeps all previous deployments. One-click rollback.
