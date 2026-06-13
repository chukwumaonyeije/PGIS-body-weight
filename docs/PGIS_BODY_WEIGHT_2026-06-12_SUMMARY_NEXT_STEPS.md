# PGIS Body Weight - High-Level Summary and Next Steps (06/12/26)

**Roadmap label:** PGIS-Body Weight circa 061226  
**Repository:** `chukwumaonyeije/PGIS-body-weight`  
**Branch:** `main`  
**Stop point:** local hardening complete; first production deployment complete
**Checkpoint commit:** `f96412b43b10c10ff070f27cd64cf3e0a3c9d5c6`

## High-Level Assessment

PGIS Body Weight is now best understood as a full-stack, medically aware exercise-planning MVP rather than a static page or simple prototype. It has a FastAPI backend, deterministic bodyweight program engine, SQLAlchemy persistence, Alembic migrations, JWT-based user auth, manual glucose logging, optional AI coaching, and a Next.js frontend.

The app has enough working surface area for a limited technical MVP, but it also handles health-sensitive data. That means the near-term priority is privacy/safety review and user-facing polish before broad use.

## What We Did on 06/12/26

- Cloned and organized the GitHub repository locally.
- Reframed the README around the real full-stack application.
- Created and maintained `NEXT_STEPS.md` as the working roadmap under the label `PGIS-Body Weight circa 061226`.
- Repaired the Alembic migration chain so a fresh database can be created cleanly.
- Verified backend setup with `uv sync --extra test`, Alembic upgrade, and the full pytest suite.
- Added `.venv/` to `.gitignore`.
- Verified frontend dependency setup with `npm install`, lint, and production build.
- Fixed Next.js build failures caused by `useSearchParams()` needing Suspense boundaries.
- Upgraded frontend security dependencies: Next.js and `eslint-config-next` to `15.5.18`, and `postcss` to a patched version.
- Reduced `npm audit` findings to zero vulnerabilities.
- Aligned frontend and backend intake schema handling for `non_binary` sex values.
- Added architecture documentation at `docs/ARCHITECTURE.md`.
- Added JWT enforcement for user-specific backend routes.
- Hardened production secret behavior so `JWT_SECRET` is required in production.
- Added visible health/privacy safety notices in the frontend flows.
- Ran a local smoke test across backend and frontend routes.
- Pushed the hardening checkpoint to GitHub.
- Deployed the backend to Railway with PostgreSQL.
- Deployed the frontend to Vercel.
- Ran a public smoke test across Railway and Vercel.

## Current Verification State

- Backend tests: `uv run pytest` -> 162 passed.
- Frontend audit: `npm audit --json` -> 0 vulnerabilities.
- Frontend lint: `npm run lint` -> passes.
- Frontend build: `npm run build` -> passes.
- Local API smoke test: registration, intake, program generation, session retrieval, session logging, and glucose logging all passed.
- Frontend route smoke test: `/`, `/login`, `/register`, `/intake`, `/program`, and `/program/session` all returned 200 locally.
- Railway `/health`: passed.
- Vercel production routes: `/`, `/login`, `/register`, `/intake`, `/program`, and `/program/session` all returned 200.
- Public API flow: registration, intake submission, program generation, next-session retrieval, session logging, and glucose logging all succeeded.

## Production URLs

- Frontend: `https://frontend-kappa-five-97.vercel.app`
- Backend: `https://backend-production-4e8af.up.railway.app`
- Backend health: `https://backend-production-4e8af.up.railway.app/health`

## Current Architecture

| Layer | Current Shape |
|---|---|
| Frontend | Next.js 15 app in `frontend/` |
| Backend | FastAPI app at `pgis_bodyweight.api.app:app` |
| Training engine | Deterministic Python engine under `pgis_bodyweight/engine/` |
| Persistence | SQLAlchemy models and Alembic migrations |
| Local database | SQLite by default |
| Production database | Railway PostgreSQL intended |
| Backend host | Railway |
| Frontend host | Vercel |

## Next Steps

1. Replace raw API error messages with friendly user-facing copy.
2. Improve session completion UI around backend session logging.
3. Add a basic progress dashboard.
4. Add password reset and email verification.
5. Add account deletion/export language before real users enter sensitive data.
6. Decide whether to enable AI coaching for the deployed MVP by setting `ANTHROPIC_API_KEY`.
7. Perform privacy/compliance review before inviting real users.

## Post-Deployment Polish

- Replace raw API error messages with friendly user-facing copy.
- Improve session completion UI around backend session logging.
- Add a basic progress dashboard.
- Add password reset and email verification.
- Add account deletion/export language before real users enter sensitive data.
- Enable AI coaching only when `ANTHROPIC_API_KEY` is configured, and keep graceful fallback behavior.

## Risks and Notes

- `next lint` still works but is deprecated before Next.js 16.
- Clinical thresholds, substitution logic, glucose messaging, and disclaimer copy should remain physician-reviewed.
- The app rejects development JWT fallback secrets when production markers are present.
- Any move toward real users should include a privacy/compliance review because intake and glucose data are health-sensitive.
