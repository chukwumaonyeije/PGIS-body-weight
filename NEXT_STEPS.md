# PGIS Body Weight — Next Steps

**As of:** 2026-06-08  
**Branch:** main  
**Test suite:** 92 passing  
**Status:** Phase 1 backend complete; ready for first Railway deploy

---

## Deploy now

The codebase is deployable as-is. To go live:

1. Push `main` to GitHub
2. Railway dashboard → New project → Deploy from GitHub repo
3. Add a **PostgreSQL plugin** to the service (Railway auto-injects `DATABASE_URL`)
4. First deploy calls `create_tables()` at startup — no manual step needed

---

## Phase 1 — Remaining items before the schema stabilises

These are the last Phase 1 gaps. Do them before iterating on the data model so schema changes are managed safely.

### 1. Alembic migrations (highest priority before schema changes)

`create_tables()` creates tables once but never alters them. Any future column add or rename will silently do nothing on an already-deployed database.

- `pip install alembic`
- `alembic init alembic/`
- Point `alembic/env.py` at `pgis_bodyweight.models.base.Base` and the `DATABASE_URL` env var
- Generate the initial migration: `alembic revision --autogenerate -m "initial schema"`
- Replace the `create_tables()` call in `lifespan` with `alembic upgrade head` (or keep `create_tables()` for dev and run Alembic only in Railway's release command)

### 2. STS age bands 65–89 (physician review required)

`pgis_bodyweight/engine/types.py` — `STS_LEVEL_THRESHOLDS` has `None` entries for every age band outside 60–64. The engine raises `ValueError` (→ HTTP 422) if a user outside that cohort submits an intake.

Fill from **Rikli & Jones 2013, Table 7** (30-Second Chair Stand normative data):

| Band | Male normal lower bound | Female normal lower bound |
|---|---|---|
| 65–69 | REVIEW | REVIEW |
| 70–74 | REVIEW | REVIEW |
| 75–79 | REVIEW | REVIEW |
| 80–84 | REVIEW | REVIEW |
| 85–89 | REVIEW | REVIEW |

The level-1/2 sub-boundary within each band also needs physician judgment (currently only the level-2/3 boundary is Rikli & Jones-cited).

### 3. Session autoregulation + ProgressionState table

After a session is logged, the engine should check per-exercise RPE and advance or hold the user's level for each pattern. Currently `POST /v1/programs/{id}/sessions/log` saves the log but does nothing with it.

- Add `ProgressionState` table: `(user_id, pattern, current_level, last_changed)`
- Write engine function `autoregulate(log, current_levels) -> new_levels` — pure, no I/O
- Call it from the log endpoint; persist updated levels
- Add tests for the autoregulation rules before implementing them

### 4. Manual glucose entry

PRD endpoint: `POST /v1/glucose` — stores a manual reading against `user_id` and an optional `session_log_id`. This is the last data-entry endpoint for Phase 1. CGM ingestion (Phase 2) replaces manual entry once the PGIS pipeline is wired in.

### 5. Open REVIEW items in clinical constants

These values in `library/exercises/*.yaml` and `engine/types.py` are flagged `REVIEW` and need physician sign-off before clinical use:

- `squat.yaml` — knee_safe track: confirm box_squat and glute_bridge are appropriate for all knee conditions at intake
- `types.py` — `DEEP_KNEE_FLEXION_EXERCISE_IDS`: confirm which conditions trigger this axis and whether "deep" requires a flexion-angle qualifier
- `types.py` — `HIGH_IMPACT_EXERCISE_IDS`: confirm which conditions trigger this axis independently of JointFlag.KNEE
- `types.py` — `PUSHUP_LEVEL_THRESHOLDS`: implementer approximations, no normative citation; physician must confirm 0–5 / 6–12 / ≥13 cutoffs
- All `single_leg_stand_s` cutoffs in `patterns.py` — currently implementer-derived; need a cited reference for 60-year-old adults

---

## Phase 2 — PGIS data loop

_Start after Phase 1 schema is stable and deployed._

- **CGM / Garmin ingestion** — reuse the existing PGIS Daily Readiness Engine pipeline; do not build a parallel time-series store
- **Glycemic-response insights** — `GET /v1/insights/glycemic-response`: correlate `SessionLog.finished_at` with glucose readings in the PGIS pipeline; surface post-session excursion trend
- **Readiness-driven deloads** — if the PGIS readiness score falls below a threshold on a training day, the engine substitutes a recovery session; requires reading readiness state at session-serve time (inject as a function argument — engine stays pure)
- **`GlucoseReading` + `ReadinessSnapshot`** — link to `SessionLog`; do not duplicate what the PGIS pipeline already stores

---

## Phase 3 — Coaching and polish

_Start after Phase 2 glycemic loop is live and producing data._

- **`coaching/` module** — Anthropic API copy generation; async, optional, non-blocking; isolated from all clinical/programming decisions (engine decides, LLM narrates)
- **Exercise-snack scheduling** — 2–8 min sessions that slot into calendar gaps; new session type in the engine, new `GET /v1/sessions/snack` endpoint
- **Expanded exercise library** — seed additional exercises per pattern; add equipment variants (pull-up bar, heavier band); each entry needs physician-reviewed contraindication tags
- **Demo media** — video/image asset IDs attached to each `exercise_id`; served from CDN, not the API

---

## Phase 4 — Distribution

- Native client(s) against this API
- Freemium model and payment integration
- Clinician-prescribed pathway (consider as a Phase 2 fast-follow given the OpenMFM distribution channel and the practice context)

---

## Open product questions (from PRD §14)

1. CGM integration order — Dexcom, Libre, or stay manual through Phase 2?
2. How prescriptive should pre-session glucose thresholds be in-app vs. "consult your clinician"? Liability line needs defining.
3. Default mesocycle length — 4 weeks with re-assessment (current) or 6?
4. Clinician-prescribed pathway — Phase 2 fast-follow?
5. Mastering Diabetes relationship — informal alignment or a partnership worth scoping?
