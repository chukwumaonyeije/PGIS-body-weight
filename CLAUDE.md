# CLAUDE.md — PGIS BODY WEIGHT

Project conventions for this repo. Read `PGIS-BodyWeight-PRD.md` for the full spec; this file is the operating manual. When the PRD and this file conflict, ask — don't guess.

## What this is

A glucose-aware bodyweight/calisthenics training app for a 60-year-old executive with type 2 diabetes on the Mastering Diabetes (low-fat, whole-food plant-based) protocol. It takes a short intake and generates a progressive, beginner-friendly-but-challenging program. The differentiator is glucose intelligence, not the exercise library.

This is wellness/education software, NOT a medical device. It never diagnoses, doses medication, or replaces a clinician.

## The one rule that governs everything

**The engine decides. The LLM only narrates.**

- Every decision with safety or clinical weight — which exercises, how many, what intensity, whether to attach a glucose-check prompt, whether to route to clearance — lives in the deterministic engine and ONLY there.
- The Anthropic API receives an already-finished program and writes coaching copy ("why this session," encouragement). It MUST NOT make or alter any programming, safety, or dosing decision.
- If the LLM is down, slow, or wrong, the worst outcome is missing/bland prose. The program is unaffected and still safe. Build for that degradation path.

If you ever find yourself reaching for an LLM call to make a clinical or numeric decision, stop — that belongs in the engine as a rule.

## Architecture

- **Language/API:** Python + FastAPI. REST + JSON.
- **Deploy:** Railway (same as the existing PGIS Daily Readiness Engine — reuse its patterns).
- **DB:** PostgreSQL for relational program/exercise data. Reuse the existing PGIS pipeline for glucose/readiness time-series; do not build a parallel one.
- **LLM:** Anthropic API, isolated in `coaching/`, async, optional, non-blocking.

Suggested layout (keep this shape):
```
pgis_bodyweight/
  api/        # FastAPI routers — thin, no business logic
  engine/     # deterministic generator — PURE, no I/O, heavily tested
  library/    # exercise catalog + progression ladders (seedable data, not code)
  pgis/       # glucose + readiness adapters (reuse existing PGIS)
  coaching/   # optional Anthropic API copy generation
  models/     # SQLAlchemy + Pydantic
  tests/      # engine tests are the priority
```

## Engine rules (non-negotiable)

1. `engine/` is **pure**: no network, no DB, no file I/O, no randomness, no system clock reads. Same input → same output, always. Inject anything external as a function argument.
2. The engine stamps every generated program with `engine_version` and the rules applied, so any output is traceable. Never produce a program you can't explain after the fact.
3. **Safety gates are tests first.** Before implementing a rule, write the failing unit test that encodes its guarantee, then make it pass. At minimum these invariants must have tests and must never break:
   - A red-flag (PAR-Q) intake NEVER yields a program — it routes to "get clearance."
   - A knee flag NEVER yields deep/loaded knee-dominant movements; it substitutes the box-squat/glute-bridge regression.
   - Insulin / sulfonylurea / meglitinide ALWAYS sets `hypo_risk = elevated` and attaches a pre-session glucose-check prompt to every session.
   - Starting levels are set PER MOVEMENT PATTERN from the functional tests — never a single global beginner/intermediate toggle.
   - Every prescribed exercise carries an inline regression and progression alternate.

## Clinical content rule

Clinical parameters — progression-ladder thresholds, sit-to-stand cutoffs, medication branches, glucose-check triggers, contraindication tags — live in **reviewable config/data files** (`library/`), never hardcoded inside logic. Reason: a physician (the owner) must be able to audit and correct every number without reading code.

When you don't know a clinical threshold, DO NOT invent a plausible-looking one. Leave a clearly marked `# REVIEW: clinical value needed` placeholder and surface it for human review. A wrong-but-confident number is worse than an obvious gap here.

## Testing

- Engine logic: thorough unit tests, invariants first (see above). This is where coverage matters most.
- API: contract tests on request/response shape.
- The coaching/LLM layer: test that the app behaves correctly when it returns nothing, errors, or is slow — not the prose itself.
- Tests must run without network access (engine is pure; mock the LLM and DB).

## Writing voice (for any prose: copy, docs, comments, commit messages)

- First-person, active, declarative. Technical and direct.
- No em-dashes. Use a period or restructure.
- No filler hype. Say what it does, not how amazing it is.
- This matches the DoctorsWhoCode voice; keep it consistent across the repo.

## Working style

- Build in the PRD's phase order: engine + tests → seed library (data) → API → optional LLM coaching.
- Small, reviewable changes. Show the failing test before the fix.
- Flag anything with clinical or liability weight for human decision rather than resolving it silently.
- Treat glucose, medications, and health data as sensitive from day one: encrypt in transit and at rest, support export and deletion.
