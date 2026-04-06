# Lessons Learned — ChessNext.ai

Errors, gotchas, and hard-won knowledge from development.
Claude Code MUST read this file to avoid repeating past mistakes.

If you hit the same type of error 2+ times, add it here.

---

## Lc0 / Neural Networks

### BN "stddivs" stores variance, not inverse std
- **Error:** Multiplied by `bn_stddivs` instead of dividing by `sqrt(bn_stddivs + eps)`
- **Symptom:** ResNet policy head output all zeros, value head constant. Residual tower looked OK (skip connections masked the bug).
- **Fix:** `gamma * (x - mean) / sqrt(variance + 1e-5) + beta`
- **Rule:** Always check what a weight field actually stores — the field name can be misleading.

### lczero-bindings won't compile on Windows
- **Error:** MSVC `std::chrono` compilation failure on both Python 3.14 and 3.12
- **Fix:** Skip lczero-bindings entirely. Load weights via protobuf + build PyTorch model directly. This gives us activation hooks anyway.
- **Rule:** If a C++ binding fails to compile, check if you can just load the weights in Python instead.

### Python 3.14 is too new for many ML packages
- **Error:** Multiple packages fail to build wheels for Python 3.14
- **Fix:** Use Python 3.12 venv (`py -3.12 -m venv .venv`)
- **Rule:** For ML/scientific work, use the latest stable Python, not bleeding edge.

### Concept extraction needs subtle Elo gap (~75), not massive gap
- **Error:** Used a 20x256 SE-ResNet vs a 20x256 classical (no SE) — ~500 Elo gap, different architectures
- **Symptom:** "Concepts" were basic chess knowledge (central control, rook lifts) that any SE network knows
- **Fix:** Use two checkpoints from the SAME training run, SAME architecture, ~69 Elo apart
- **Rule:** For concept extraction a la DeepMind, both networks must be superhuman. The gap must be subtle.

## Windows / Environment

### Unicode in print() crashes on Windows cp1252
- **Error:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'`
- **Fix:** Use ASCII arrows (`->`) instead of Unicode (`→`, `≈`) in print statements
- **Rule:** Never use Unicode symbols in Python print() on Windows. Stick to ASCII.

### /tmp doesn't map cleanly in Git Bash on Windows
- **Error:** Python sees `/tmp/` differently than Git Bash
- **Fix:** Use full Windows paths (`C:/Users/.../AppData/Local/Temp/`) in Python code
- **Rule:** Always use absolute Windows-style paths when passing between Bash and Python.

### PyTorch attribute names change between versions
- **Error:** `torch.cuda.get_device_properties(0).total_mem` → should be `total_memory`
- **Rule:** Check PyTorch docs for your installed version, don't assume attribute names.

## General Patterns

### stdout is buffered when redirected on Windows
- **Symptom:** Background process shows no output for minutes, looks stuck
- **Fix:** Use `PYTHONUNBUFFERED=1` or `python -u` for any long-running script
- **Rule:** Always run pipeline scripts with `PYTHONUNBUFFERED=1` on Windows.

### Logistic regression on 163K features is too slow
- **Error:** SAGA solver on raw activations (163,840 dims) hung for 10+ minutes
- **Fix:** Run probes on PCA-reduced features (150-200 dims), use LBFGS solver
- **Rule:** Always PCA first, then probe. Never fit sklearn on raw high-dim activations.

### Never defer tests — write them alongside each feature
- **Error:** Coded 13 routes and 5 pages without a single test file
- **Symptom:** Zero test coverage, security rules half-applied, no confidence that code works
- **Fix:** For every feature: write test first (or alongside), commit together. Never "tests later."
- **Rule:** If a commit adds a route/component, it MUST include its test file. No exceptions.

### Apply security rules as you code, not in a "security pass" later
- **Error:** Built auth, Stripe, API routes without security headers, rate limiting, or Sentry
- **Symptom:** Missing CSP, X-Frame-Options, HSTS. No Upstash rate limiting. No structured logging.
- **Fix:** Every API route gets rate limiting + validation + error handling at creation time. Security headers go in proxy.ts on day one.
- **Rule:** Check SECURITY.md before writing any endpoint. Not after.

---

*Add new entries at the bottom of the relevant section. Date optional.*
