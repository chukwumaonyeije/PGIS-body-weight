# PGIS Body Weight - Next Steps

**As of:** 2026-06-12
**Branch:** main
**Status:** Works locally; repo hardening before public deployment
**Roadmap label:** PGIS-Body Weight circa 061226

---

## Guiding Principle

Do not deploy a confusing repository.

The app is close enough to deploy that discipline matters now. The immediate goal is to make the repository accurate, reproducible, and safe to share from a clean checkout before adding features or pushing to production.

---

## Completed or Present in the Codebase

- FastAPI backend app at `pgis_bodyweight.api.app:app`
- Next.js frontend under `frontend/`
- SQLAlchemy models for users, intake submissions, generated programs, session logs, progression states, and glucose readings
- Alembic migration setup and migration files
- Deterministic 4-week program generator
- PAR-Q safety gate and hypo-risk branching
- Exercise-library YAML files
- Session logging endpoint
- ProgressionState/autoregulation support
- Manual glucose entry endpoint at `POST /v1/glucose`
- Optional coaching endpoint
- Railway deployment config
- Backend pytest suite

---

## Phase 1 - Repo Hardening

Goal: make the project coherent and reproducible from a fresh clone.

### 1. README rewrite

Status: complete.

The README now describes the actual full-stack app instead of the older static landing page.

### 2. Refresh this next-steps document

Status: complete.

This document now separates completed work, hardening tasks, deployment tasks, clinical review items, and future roadmap items.

### 3. Verify backend dependency setup

Status: complete.

Tasks:

- [x] Run `uv sync --extra test`.
- [x] Run `uv run pytest`.
- [x] Confirm all backend tests pass: `142 passed`.
- [x] Confirm Alembic migration chain works against a fresh temporary SQLite database.
- [x] Review `pyproject.toml` test dependency `httpx2>=2`; confirmed intentional for this FastAPI/Starlette stack.
- [x] Confirm `bcrypt` is installed correctly in a fresh environment.
- [x] Add `.venv/` to `.gitignore`.

Acceptance criteria:

- A fresh clone can install backend dependencies and run tests with documented commands.
- No hidden manual dependency installation is required.

Notes:

- The Alembic migration chain had placeholder migrations and failed when run against the existing local SQLite database. The migrations now create the core schema, progression state table, glucose readings table, and auth columns in order.
- The ignored local `pgis_bodyweight.db` may still reflect pre-hardening local state. Fresh database verification was performed against a temporary SQLite database.

### 4. Verify frontend dependency setup

Status: complete.

Tasks:

- [x] Run `npm install` from `frontend/`.
- [x] Run `npm run lint`: no warnings or errors.
- [x] Run `npm run build`: production build succeeds.
- [x] Confirm `frontend/package-lock.json` is current after install.
- [x] Fix Next.js `useSearchParams()` build failure by wrapping `/program` and `/program/session` in Suspense boundaries.

Acceptance criteria:

- A fresh clone can install, lint, build, and run the frontend using documented commands.

Notes:

- `npm install` reported deprecation warnings and 8 vulnerabilities.
- `next@14.2.3` was flagged by npm as having a security vulnerability. Plan a dependency upgrade pass before public deployment.
- The initial build failed because `useSearchParams()` was used on `/program` and `/program/session` without a Suspense boundary. This has been fixed.

### 4a. Frontend dependency/security upgrade pass

Status: complete.

Tasks:

- [x] Run `npm audit`.
- [x] Upgrade Next.js to a patched compatible version: `next@15.5.18`.
- [x] Upgrade `eslint-config-next` to `15.5.18`.
- [x] Override/pin `postcss` to patched `^8.5.10`.
- [x] Set `outputFileTracingRoot` in `next.config.mjs` so Next does not infer a parent workspace root from unrelated lockfiles.
- [x] Re-run `npm audit`: 0 vulnerabilities.
- [x] Re-run `npm run lint`: no warnings or errors.
- [x] Re-run `npm run build`: production build succeeds.
- [x] Review whether ESLint 8 deprecation requires a larger config migration now or can wait.

Notes:

- `next lint` still works but is deprecated and will be removed in Next.js 16.
- Defer migration to the ESLint CLI until a future Next 16 upgrade pass.

### 5. Align frontend and backend schemas

Status: complete.

Known likely mismatch:

- [x] Frontend allows `sex: "non_binary"`.
- [x] Backend now accepts `Sex.NON_BINARY`.
- [x] Backend maps `non_binary` to female STS norming bands as the conservative default documented in the engine.
- [x] Frontend `IntakePayload.sex` type now matches allowed backend values.
- [x] API contract tests cover `non_binary` intake assessment and program generation.

Decision needed:

- Decision: support `non_binary` / prefer-not-to-say in the backend and use female STS norms for current conservative programming.

Acceptance criteria:

- [x] The intake form cannot submit values the backend rejects under normal use.
- [x] The norming decision is documented in code comments and tests.

Verification:

- `uv run pytest`: `144 passed`.
- `npm run lint`: no warnings or errors.
- `npm run build`: production build succeeds.

### 6. Add or update architecture documentation

Status: complete.

Task:

- [x] Add a concise architecture section to README.
- [x] Add `docs/ARCHITECTURE.md`.
- [x] Link the architecture guide from README.

Include:

- [x] API app entrypoint
- [x] Route layout
- [x] Model and migration layout
- [x] Engine boundaries
- [x] Frontend API client
- [x] Deployment shape

Acceptance criteria:

- [x] A developer can understand the project layout in under 10 minutes.

---

## Phase 2 - Auth, Privacy, and Safety Boundaries

Goal: make the app safer to expose beyond localhost.

### 1. Enforce JWT authentication on user-specific routes

Status: complete.

Current concern:

- [x] The backend issues JWTs.
- [x] The frontend sends `Authorization: Bearer <token>`.
- [x] User-specific stateful backend routes now validate bearer tokens.
- [x] Routes still accepting `user_id` for frontend compatibility now require it to match the token subject.

Tasks:

- [x] Add a backend dependency that validates JWTs.
- [x] Derive current user ID from the token.
- [x] Stop trusting client-submitted `user_id` for protected operations.
- [x] Ensure users can only access their own intakes, programs, session logs, and glucose readings.
- [x] Add tests for missing token, invalid token, and wrong-user access.

Acceptance criteria:

- [x] User-specific data cannot be read or modified by changing a `user_id` parameter.

Verification:

- `uv run pytest`: `157 passed`.
- `npm run lint`: no warnings or errors.
- `npm run build`: production build succeeds.

### 2. Harden production secrets behavior

Status: complete.

Tasks:

- [x] Require `JWT_SECRET` in production.
- [x] Reject the development fallback secret in production.
- [x] Keep the development fallback explicitly local-only.
- [x] Treat `ENVIRONMENT=production`, `APP_ENV=prod`, or `RAILWAY_ENVIRONMENT` as production markers.
- [x] Document production env vars.

Required backend env vars:

```text
DATABASE_URL
JWT_SECRET
ALLOWED_ORIGINS
ANTHROPIC_API_KEY optional
```

Required frontend env vars:

```text
NEXT_PUBLIC_API_URL
```

Verification:

- `uv run pytest`: `162 passed`.

### 3. Improve clinical and privacy language

Status: complete.

Tasks:

- [x] Add visible app-level disclaimer language.
- [x] Keep README safety note current.
- [x] Confirm logs do not include raw intake or glucose values.
- [x] Confirm raw error responses do not expose sensitive payloads.

Implementation:

- Added reusable frontend `SafetyNotice` component.
- Displayed notice during login/register, intake, program, and session views.
- Notice identifies the app as exercise-planning support, not medical care.
- Notice reminds users that intake and glucose entries are health-sensitive.

Verification:

- `uv run pytest`: `162 passed`.
- `npm audit --json`: 0 vulnerabilities.
- `npm run lint`: no warnings or errors.
- `npm run build`: production build succeeds.

---

## Phase 3 - Local Verification

Status: complete.

Goal: prove the app runs cleanly before deployment.

### Backend checklist

```bash
uv sync
uv run pytest
uv run alembic upgrade head
uv run uvicorn pgis_bodyweight.api.app:app --reload --host 0.0.0.0 --port 8000
```

Confirm:

- [x] `/health` returns `{"status":"ok"}`
- [x] Register works
- [x] Authenticated intake submission works
- [x] Authenticated program generation works
- [x] Authenticated program/session retrieval works
- [x] Authenticated session logging works
- [x] Authenticated manual glucose logging works

### Frontend checklist

```bash
cd frontend
npm install
npm run lint
npm run build
npm run dev
```

Confirm:

- [x] Login page loads
- [x] Registration page loads
- [x] Intake page loads
- [x] Program page loads
- [x] Session page loads
- [x] Frontend production build succeeds

### End-to-end smoke test

1. [x] Start backend locally against temporary SQLite database.
2. [x] Start frontend locally.
3. [x] Verify backend `/health`.
4. [x] Register a new account through the API.
5. [x] Submit intake with bearer token.
6. [x] Generate a program with bearer token.
7. [x] Fetch generated program and next session with bearer token.
8. [x] Log a session with bearer token.
9. [x] Log a glucose reading linked to the session log with bearer token.
10. [x] Verify frontend routes return 200: `/`, `/login`, `/register`, `/intake`, `/program`, `/program/session`.

Verification:

- `uv run pytest`: `162 passed`.
- `npm audit --json`: 0 vulnerabilities.
- `npm run lint`: no warnings or errors.
- `npm run build`: production build succeeds.
- Local API smoke test produced a 4-week program, session log, and glucose reading.

---

## Phase 4 - Deployment

Goal: deploy only after repo hardening and local verification.

### Railway backend

1. Generate `JWT_SECRET`.
2. Connect GitHub repo `chukwumaonyeije/PGIS-body-weight`.
3. Deploy from `main`.
4. Add PostgreSQL plugin.
5. Confirm Railway injects `DATABASE_URL`.
6. Add `JWT_SECRET`.
7. Add `ALLOWED_ORIGINS` after Vercel URL is known.
8. Confirm:

```text
https://<railway-url>/health
```

Expected:

```json
{"status":"ok"}
```

### Vercel frontend

1. Import same GitHub repo.
2. Set root directory to `frontend`.
3. Add:

```text
NEXT_PUBLIC_API_URL=https://<railway-url>
```

4. Deploy.
5. Add Vercel URL to Railway `ALLOWED_ORIGINS`.
6. Run public end-to-end smoke test.

---

## Phase 5 - MVP UX Polish

Prioritized items:

1. Friendly error messages instead of raw API JSON.
2. Session completion UI wired to backend session logging.
3. Basic progress dashboard.
4. Better loading and empty states.
5. Password reset.
6. Email verification.
7. Account deletion/export language if real users enter sensitive data.

---

## Phase 6 - PGIS Platform Expansion

Near-term:

- Enable AI coaching with `ANTHROPIC_API_KEY`.
- Keep AI coaching non-decisional: the engine decides, the LLM narrates.
- Show graceful UI fallback when coaching is unavailable.

Medium-term:

- Workout history and analytics
- Manual glucose trends around sessions
- CGM and wearable integration through existing PGIS pipeline
- Readiness-driven deloads
- Exercise-snack recommendations

Long-term:

- Physician dashboard for prescribed programs
- Broader PGIS ecosystem integration
- Multi-modal programs: strength, cardio, mobility, recovery
- Research/outcomes collection with appropriate consent and governance

---

## Clinical Review Items

Keep these separate from ordinary engineering tasks.

- Sex/norming strategy for users who do not map cleanly to male/female normative tables
- STS age-band thresholds and citations
- Pushup threshold rationale
- Single-leg balance thresholds
- Knee, hip, shoulder, wrist, and lower-back substitution logic
- Hypoglycemia-risk messaging
- Liability boundary for pre-session glucose guidance
- User-facing disclaimer language

Clinical decisions should be reflected in code comments, tests, and user-facing copy.

---

## Launch Readiness Definition

The app is ready for a limited public MVP when:

- Fresh backend setup succeeds.
- Fresh frontend setup succeeds.
- Backend tests pass.
- Frontend lint and build pass.
- Frontend/backend schema mismatch is resolved.
- JWT auth is enforced on user-specific routes.
- Production env vars are documented.
- Railway backend health check passes.
- Vercel frontend completes the full smoke test.
- Clinical/safety disclaimers are visible enough for the launch audience.
