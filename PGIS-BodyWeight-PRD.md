# Product Requirements Document — PGIS BODY WEIGHT

**Product:** PGIS BODY WEIGHT (a Performance Glycemic Intelligence System module)
**Author:** Chukwuma Onyeije, MD, FACOG
**Version:** 0.1 (Draft for backend + programming engine)
**Date:** June 6, 2026
**Status:** Draft — scoping the backend and program-generation engine following landing-page launch

---

## 1. Summary

PGIS BODY WEIGHT is a glucose-aware bodyweight and calisthenics training app. It asks a new user a focused set of intake questions, then generates a structured, progressive training program that is *challenging but beginner-friendly*. The reference experience is Fitify (intake-driven personalization, short 15–25 minute sessions, a large exercise library, prebuilt and custom workouts, recovery sessions, and progress tracking).

The differentiator — and the reason this belongs inside PGIS rather than being another generic workout app — is **glucose intelligence**: the program adapts to the user's metabolic state, medication profile, CGM/wearable data, and the post-meal movement timing that matters most for someone managing type 2 diabetes. Fitify optimizes for aesthetics and fitness goals. PGIS BODY WEIGHT optimizes for *glycemic outcomes plus strength, mobility, and longevity* in a deconditioned-but-motivated adult.

This document scopes the **backend and the program-generation engine**. The landing page already exists. Native mobile UI is out of scope here except where it constrains the API contract.

---

## 2. Target user

**Primary persona — "The Executive Beginner"**

A 60-year-old executive with type 2 diabetes following the Mastering Diabetes (low-fat, whole-food plant-based) protocol. Characteristics that drive every product decision:

- **Deconditioned but capable and motivated.** Likely sedentary or lightly active. Needs a real on-ramp, not a HIIT class. But intelligent, goal-oriented, and will quit anything that feels patronizing or pointless.
- **Time-constrained.** Travels, has back-to-back meetings. Sessions must fit in 10–25 minutes and slot into the day, including "exercise snacks."
- **Metabolically motivated.** The *why* is glucose control, insulin sensitivity, weight, energy, and avoiding complications — not a beach body.
- **Joint-cautious.** Sixty-year-old knees, shoulders, and lower back. Needs joint-friendly options and clean regressions.
- **Data-literate.** Comfortable with a CGM, a Garmin, dashboards, and numbers. Trusts the program more when it shows its reasoning.

**Secondary personas (future):** prediabetic adults; post-bariatric patients; the broader Mastering Diabetes community; clinicians prescribing the program to patients.

---

## 3. Goals and non-goals

### Goals
- Generate a personalized, progressive bodyweight program from a short intake.
- Keep every session beginner-accessible via explicit per-exercise progressions and regressions.
- Make programming **glucose-aware**: timing, intensity, and safety guidance informed by the user's metabolic and medication profile, and (when available) CGM/wearable data.
- Autoregulate using RPE and readiness rather than fixed prescriptions the user can't meet.
- Track adherence, progression, and — uniquely — the relationship between training and glycemic response.

### Non-goals (for this version)
- Not a medical device and not a substitute for the user's care team. No insulin dosing, no medication titration, no diagnosis.
- No gym/barbell/machine programming. Bodyweight and minimal equipment (chair, band, pull-up bar) only.
- No nutrition/meal planning engine. PGIS BODY WEIGHT *assumes* the user is on Mastering Diabetes and references meal timing only as it relates to exercise windows.
- No social feed, no live classes, no native UI build in this scope.

---

## 4. Competitive framing vs. Fitify

| Capability | Fitify | PGIS BODY WEIGHT |
|---|---|---|
| Intake-driven personalization | Experience, goal, time | + medications, glycemic profile, joint limits, balance/fall risk |
| Session length | 15–25 min | 10–25 min + "exercise snacks" (2–8 min) |
| Exercise library | 900+ (incl. equipment) | Curated, fully-tagged bodyweight + minimal equipment, with explicit progression ladders |
| Progression model | Plan refresh | Per-movement-pattern progression ladders with autoregulation |
| Recovery sessions | Stretch / yoga / foam rolling | + mobility for older adults + post-session glucose-settling walks |
| **Glucose awareness** | **None** | **Core: timing nudges, pre-session readiness, CGM/Garmin integration, post-session glycemic response tracking** |
| Population fit | General | Optimized for 60+ adult with T2D on WFPB |

The moat is the last two rows. Anyone can clone an exercise library; the glucose-aware programming and the PGIS data loop are the defensible product.

---

## 5. Clinical and safety foundation

These rules are non-negotiable and bound the engine's output.

**Exercise guidelines (ADA / ACSM framing).** Adults with T2D benefit from ≥150 min/week of moderate aerobic activity plus resistance training on 2–3 nonconsecutive days. Older adults add balance/neuromotor work 2–3x/week for fall prevention. The engine targets these as a north star, ramping toward them rather than starting there.

**Mastering Diabetes context.** The low-fat WFPB protocol frequently reduces or eliminates insulin and oral hypoglycemic agents. This *lowers but does not eliminate* exercise-related hypoglycemia risk. The engine must therefore branch on **medication class**, not assume.

**Hypoglycemia screening.** Intake must capture whether the user takes insulin, sulfonylureas, or meglitinides (the agents that cause exercise hypoglycemia). If yes → conservative timing guidance, pre/post glucose-check prompts, and explicit "stop" thresholds surfaced in-app. If no → lighter monitoring, still educational.

**Pre-session safety gates (surfaced as guidance, not auto-blocking medical decisions):**
- Don't begin a hard session if glucose is very low or very high with symptoms; defer or substitute a gentle walk.
- Hydration, footwear, and stop-if-symptomatic reminders.
- Foot-care note for anyone with neuropathy risk.

**Post-meal movement.** Light-to-moderate movement 30–60 minutes after meals blunts postprandial glucose excursions. The engine should *prefer* scheduling activity in those windows for this population.

**Medical disclaimer + clearance gate.** First-run flow includes a "talk to your clinician before starting" gate and an ongoing disclaimer. Red-flag intake answers (recent cardiac event, uncontrolled symptoms, etc.) route to a "get clearance first" state instead of a generated program.

---

## 6. Functional requirements

### 6.1 Intake assessment (FR-INTAKE)

A single guided flow, ~2–4 minutes, that produces the inputs the engine needs. Grouped:

**Demographics & baseline**
- Age, sex, height, weight (for relative-effort scaling, not shaming).
- Self-reported activity level (sedentary → very active).

**Functional capacity (objective mini-tests, beginner-safe)**
- 30-second sit-to-stand count (lower-body strength + a proxy for starting squat progression).
- Wall/incline push-up max reps (upper-body push starting level).
- Single-leg stand time, eyes open (balance / fall-risk screen).
- Optional: how far can you walk comfortably without stopping.

**Goals (rank or multi-select)**
- Glucose control, weight, strength, mobility/independence, energy, general health.

**Constraints**
- Days/week available and minutes/session.
- Equipment available (none / sturdy chair / resistance band / pull-up bar).
- Joint or pain limitations (knee, shoulder, lower back, wrist, hip) → drives regressions and substitutions.

**Glycemic profile (PGIS core)**
- Medications (insulin / sulfonylurea / metformin only / none / other) — drives the hypoglycemia branch.
- Typical fasting glucose range and recent A1c (optional).
- CGM in use? (brand) — gates the integration features.
- Wearable in use? (Garmin etc.) — gates HR/readiness features.

**Safety screen**
- Brief PAR-Q-style red-flag screen (chest pain, dizziness, recent cardiac/orthopedic event, etc.).

### 6.2 Program generation (FR-GEN)

From the intake, generate a **multi-week mesocycle** (default 4 weeks, then re-assess) composed of weekly microcycles and individual sessions.

- **Movement-pattern coverage.** Every program balances six patterns: squat, hinge, horizontal push, horizontal/vertical pull, core/anti-extension brace, and single-leg/balance. Plus warm-up, cool-down/mobility, and an optional post-meal walk block.
- **Starting level per pattern** set from the functional tests, not a single global "beginner/intermediate/advanced" toggle. A user can be level 1 in push and level 3 in squat.
- **Volume & intensity** scaled to time budget and days/week. Default beginner dose: 2–3 sessions/week, 2 sets per exercise, RPE 5–7, with a 10th-week-style deload built in (mirrors the PGIS deload philosophy).
- **Beginner-friendly + challenging.** Each prescribed exercise carries an explicit regression (drop-down) and progression (level-up) so the same session works on a hard day and a strong day. The challenge comes from progression cadence, not from starting too hard.
- **Glucose-aware scheduling.** When meal-timing or CGM data is available, prefer post-meal windows; suggest "exercise snack" placements for time-constrained days; tag sessions with a recommended pre-session glucose check when the medication branch warrants it.
- **Generation strategy:** deterministic rules engine first (auditable, safe, testable), with an *optional* LLM layer (Anthropic API) used only to write coaching copy / session rationale — never to make safety or dosing decisions. The rules engine is the source of truth.

### 6.3 Progression & autoregulation (FR-PROG)

- After each session, capture completion + per-exercise RPE (or a simple "easy / right / too hard").
- Progress a pattern's level when the user hits the top of the prescribed rep/time range at RPE ≤ target across the required sessions.
- Regress automatically when sessions are repeatedly missed or rated "too hard."
- Insert a deload week on schedule or when readiness (HRV/glucose/sleep, if available) trends down — reusing the PGIS Daily Readiness Engine logic.

### 6.4 Exercise library (FR-LIB)

A curated, fully-tagged catalog of bodyweight and minimal-equipment movements. Each exercise carries: movement pattern, primary muscles, equipment, joint-load tags (knee/shoulder/back-friendly flags), a difficulty level within its progression ladder, pointers to its regression and progression, cues, contraindications, and a demo asset reference (video/animation). Curated and deep, not "900 for the marketing number."

### 6.5 Session player contract (FR-SESSION)

Backend must serve a session as an ordered list of blocks (warm-up → main → cool-down → optional walk), each block an ordered list of timed/rep-based exercise instances with cues, rest, and the regression/progression alternates inline so the player can swap mid-session without a round-trip.

### 6.6 Tracking & PGIS loop (FR-TRACK)

- Log sessions, adherence, progression history.
- Ingest glucose (CGM or manual) and wearable readiness where available.
- **Glycemic response view:** correlate sessions with post-session glucose behavior (the unique insight). Surface a simple "this is how movement is moving your numbers" chart (Chart.js, consistent with existing PGIS dashboards).

---

## 7. Program-generation logic (reference rules)

This is the heart of the engine; stated explicitly so it can be implemented and unit-tested.

**Step 1 — Safety gate.** Any red flag → no program; route to "get clearance." Insulin/sulfonylurea/meglitinide → set `hypo_risk = elevated`, attach monitoring protocol to every session.

**Step 2 — Per-pattern starting level.**
- Squat: from sit-to-stand count (e.g., <8 → chair-assisted sit-to-stand; 8–14 → box squat; 15+ → bodyweight squat).
- Push: from wall/incline push-up max (e.g., 0–5 → wall; 6–12 → incline/counter; 13+ → knee→full progression).
- Pull: default to band rows / inverted-row regressions absent a bar; conservative start.
- Hinge / core / balance: start at safe baselines, gated by balance test and back-pain flag.

**Step 3 — Dose from constraints.** Map days/week × minutes/session to sets and pattern coverage per session. Honor a hard joint-flag → substitute (e.g., knee flag → swap deep squats for box squats and glute bridges).

**Step 4 — Glycemic layer.** If CGM/meal data present, tag preferred session windows post-meal; if time-poor, fragment into exercise snacks; attach pre-session glucose-check prompt when `hypo_risk = elevated`.

**Step 5 — Assemble mesocycle.** 4 weeks, progressive, with deload. Each session = warm-up + balanced patterns + cool-down/mobility (+ optional post-meal walk).

**Step 6 — Coaching copy (optional LLM).** Generate the human-readable "why this session" and encouragement from the structured plan. Engine output remains canonical.

---

## 8. Backend architecture

Aligned with the existing PGIS stack so this slots into what's already deployed.

- **Runtime/API:** Python + FastAPI (consistent with the PGIS Daily Readiness Engine on Railway). REST + JSON.
- **Datastore:** PostgreSQL for relational program/exercise data; the readiness/glucose time-series can reuse the existing PGIS data path.
- **Generation engine:** a pure, deterministic Python module (no I/O) so it is unit-testable and auditable — `generate_mesocycle(intake) -> Program`. The LLM coaching layer calls the Anthropic API and is fully optional/degradable.
- **Integrations:** CGM (manual entry first; vendor API later), Garmin/wearable readiness (reuse PGIS ingestion), notification service for session/timing nudges.
- **Auth:** standard token auth; PHI-conscious from day one (see §11).
- **Deploy:** Railway, matching existing PGIS services.

**Suggested module layout**
```
pgis_bodyweight/
  api/            # FastAPI routers
  engine/         # deterministic program generator (no I/O, heavily tested)
  library/        # exercise catalog + progression ladders (seedable)
  pgis/           # glucose + readiness adapters (reuse existing PGIS)
  coaching/       # optional Anthropic API copy generation
  models/         # SQLAlchemy / Pydantic
  tests/          # engine unit tests are the priority
```

---

## 9. Data model (core entities)

| Entity | Key fields |
|---|---|
| `User` | id, profile, medication_class, cgm_flag, wearable_flag, created_at |
| `IntakeAssessment` | id, user_id, demographics, functional_tests (sit_to_stand, pushup_max, balance_s), goals[], constraints (days, minutes, equipment[], joint_flags[]), glycemic_profile, parq_flags[], completed_at |
| `Exercise` | id, name, pattern, primary_muscles[], equipment, joint_tags[], level, regression_id, progression_id, cues, contraindications[], demo_asset |
| `ProgramTemplate` | id, pattern_schema, dose_rules (versioned) |
| `Program` (generated) | id, user_id, weeks[], deload_week, generated_at, engine_version |
| `Session` | id, program_id, week, day, blocks[] (warmup/main/cooldown/walk), glucose_check_required, preferred_window |
| `SessionExercise` | id, session_id, exercise_id, sets, reps_or_time, rest, target_rpe, regression_alt, progression_alt |
| `SessionLog` | id, session_id, user_id, completed, per_exercise_rpe[], notes, started_at, finished_at |
| `ProgressionState` | id, user_id, pattern, current_level, last_changed |
| `GlucoseReading` / `ReadinessSnapshot` | reuse existing PGIS time-series; linked to SessionLog for the glycemic-response view |

---

## 10. API surface (representative)

| Method & path | Purpose |
|---|---|
| `POST /v1/intake` | Submit intake; returns safety-gate result |
| `POST /v1/programs/generate` | Generate mesocycle from latest intake |
| `GET /v1/programs/current` | Current program + progression state |
| `GET /v1/sessions/next` | Next session as a player-ready block list (with regression/progression alternates inline) |
| `POST /v1/sessions/{id}/log` | Log completion + per-exercise RPE; triggers autoregulation |
| `GET /v1/exercises` | Library, filterable by pattern/equipment/joint flag |
| `POST /v1/glucose` | Manual glucose entry (CGM adapter later) |
| `GET /v1/insights/glycemic-response` | Session ↔ glucose correlation data for the dashboard |

---

## 11. Non-functional requirements

- **Privacy/PHI:** treat glucose, medications, and health data as sensitive. Encrypt in transit and at rest; support data export and deletion (Fitify's own store listing shows this is now table stakes). Be explicit in-app about what's collected and why.
- **Offline-tolerant session player:** sessions should be servable for offline execution (Fitify works offline; this population travels).
- **Auditability:** every generated program records `engine_version` and the rules applied, so a clinician (or you) can review *why* a program was produced.
- **Graceful degradation:** no CGM, no wearable, no LLM → the app still produces a safe, useful program from intake alone.
- **Performance:** program generation is synchronous and fast (deterministic, in-process). LLM coaching copy is async/optional and never blocks a session.

---

## 12. MVP scope and phasing

**Phase 1 — Backend MVP (this scope).** Intake + safety gate; deterministic generation engine; seeded exercise library with progression ladders for the six patterns; session-serving + logging; rule-based autoregulation; manual glucose entry. *Glucose awareness in this phase = medication-branch monitoring prompts + post-meal timing guidance.*

**Phase 2 — PGIS loop.** CGM/Garmin ingestion (reuse existing PGIS pipeline), glycemic-response insights dashboard, readiness-driven deloads.

**Phase 3 — Coaching & polish.** Anthropic-API coaching copy, exercise-snack scheduling, notification nudges, demo media, expanded library.

**Phase 4 — Distribution.** Native client(s) against this API, freemium model, clinician-prescribed pathway for patients.

---

## 13. Success metrics

- **Activation:** % completing intake who start session 1; % reaching session 4.
- **Adherence:** sessions/week vs. prescribed; 4- and 12-week retention.
- **Progression:** % advancing ≥1 pattern level by week 4.
- **Glycemic (north star):** trend in post-session glucose excursions; time-in-range on training vs. non-training days; A1c trend over 12 weeks (self-reported).
- **Safety:** zero unsafe prescriptions; red-flag users correctly routed to clearance.

---

## 14. Open questions

1. CGM integration order — which vendor API first, or stay manual through Phase 2?
2. How prescriptive should pre-session glucose thresholds be in-app vs. "consult your clinician" given device-only liability concerns?
3. Default mesocycle length — 4 weeks with re-assessment, or 6?
4. Should the clinician-prescribed pathway (your patients) be a Phase-2 fast-follow given your practice and OpenMFM distribution channels?
5. Where does the Mastering Diabetes relationship sit — informal alignment, or a partnership/affiliate path worth scoping into positioning?

---

*PGIS BODY WEIGHT is wellness/education software, not a medical device. It does not diagnose, treat, or replace medical care. Users are gated to consult their clinician before beginning.*
