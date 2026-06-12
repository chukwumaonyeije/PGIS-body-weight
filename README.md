# PGIS Body Weight

Glucose-aware bodyweight training for the PGIS platform.

PGIS Body Weight is a full-stack MVP that turns a user's intake answers into a personalized 4-week bodyweight training program. It combines a deterministic exercise-programming engine, safety gates, session-level programming, basic account creation, manual glucose logging, and a Next.js frontend.

## Current Status

The app works locally end-to-end:

```text
Register -> Log in -> 4-step intake -> 4-week program -> individual session details
```

As of 2026-06-12, repo hardening, auth/privacy hardening, dependency/security upgrades, and local smoke testing are complete. The next phase is deployment: Railway backend, Vercel frontend, CORS connection, and public smoke test.

## Architecture

| Layer | Purpose | Location | Stack |
|---|---|---|---|
| Frontend | User-facing auth, intake, program, and session screens | `frontend/` | Next.js 15, React, Tailwind |
| Backend API | HTTP routes, auth, persistence, glucose logging, coaching endpoint | `pgis_bodyweight/api/` | FastAPI |
| Training engine | Deterministic program generation, safety rules, autoregulation | `pgis_bodyweight/engine/` | Python dataclasses and pure functions |
| Exercise library | Movement ladders and fixed warmup/cooldown blocks | `pgis_bodyweight/library/` | YAML |
| Data model | Users, intakes, generated programs, session logs, progression states, glucose readings | `pgis_bodyweight/models/` | SQLAlchemy |
| Migrations | Production schema changes | `alembic/` | Alembic |
| Tests | API contracts, persistence, glucose, coaching, safety, autoregulation | `pgis_bodyweight/tests/` | pytest |

The canonical backend ASGI app is:

```text
pgis_bodyweight.api.app:app
```

For a fuller developer map, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Local Development

### Backend

From the repository root:

```bash
uv sync --extra test
uv run alembic upgrade head
uv run uvicorn pgis_bodyweight.api.app:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```text
http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

### Frontend

From `frontend/`:

```bash
npm install
npm run dev
```

The frontend defaults to:

```text
http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL` if the backend is not running on `http://localhost:8000`.

## Environment Variables

### Backend

| Variable | Required | Purpose |
|---|---:|---|
| `DATABASE_URL` | Production | PostgreSQL connection string. Defaults to local SQLite when omitted. |
| `JWT_SECRET` | Production | Secret used to sign auth tokens. Required when `ENVIRONMENT=production`, `APP_ENV=prod`, or `RAILWAY_ENVIRONMENT` is set. |
| `ALLOWED_ORIGINS` | Production | Comma-separated frontend origins allowed by CORS. Defaults to local Next.js origins. |
| `ANTHROPIC_API_KEY` | Optional | Enables AI-generated session coaching text. The app should still work without it. |

Local development uses a fallback JWT secret when no production environment marker is present. Production startup fails if `JWT_SECRET` is missing or set to the development fallback.

### Frontend

| Variable | Required | Purpose |
|---|---:|---|
| `NEXT_PUBLIC_API_URL` | Deployment | Public backend API URL, for example the Railway backend URL. |

Example:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Testing

Backend:

```bash
uv sync --extra test
uv run pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Verified on 2026-06-12:

- `uv run pytest`: 162 passed
- `npm audit --json`: 0 vulnerabilities
- `npm run lint`: passes
- `npm run build`: passes
- Local API and frontend smoke test: passes

## Deployment

The intended deployment shape is:

| Component | Host |
|---|---|
| Backend | Railway |
| Database | Railway PostgreSQL |
| Frontend | Vercel |

### Railway Backend

1. Connect the GitHub repository.
2. Add a Railway PostgreSQL plugin.
3. Set `JWT_SECRET`.
4. Set `ALLOWED_ORIGINS` after the Vercel URL is known.
5. Deploy with:

```text
uvicorn pgis_bodyweight.api.app:app --host 0.0.0.0 --port $PORT
```

6. Confirm `/health` returns `{"status":"ok"}`.

### Vercel Frontend

1. Import the GitHub repository.
2. Set the Vercel root directory to `frontend`.
3. Set `NEXT_PUBLIC_API_URL` to the Railway backend URL.
4. Deploy.
5. Add the Vercel URL to Railway `ALLOWED_ORIGINS`.

### Smoke Test

Use a private/incognito browser window:

1. Register a new account.
2. Complete the intake.
3. Generate a program.
4. Open a session.
5. Log out and log back in.
6. Confirm the program remains accessible.

## Known Limitations

- The app is not yet deployed publicly.
- Error messages may still expose raw API details instead of friendly copy.
- Password reset and email verification are not yet implemented.
- Session completion UI is still an MVP polish item.
- AI coaching requires `ANTHROPIC_API_KEY`; without it, coaching should fail gracefully.
- `next lint` is deprecated and should be migrated before a future Next.js 16 upgrade.

## Clinical and Safety Note

PGIS Body Weight is a medically aware fitness MVP, not a substitute for medical care. It is intended to support safe, progressive exercise planning, but users should follow clinician guidance for diabetes management, exercise restrictions, glucose monitoring, fall risk, and cardiovascular symptoms.

The app includes PAR-Q-style safety gating and exercise substitutions, but clinical thresholds and contraindication rules should remain physician-reviewed and auditable before broad public use.

The frontend displays a health and privacy notice in the auth, intake, program, and session flows. Keep that notice current as the app begins accepting more sensitive data.

## Repository Map

```text
.
├── alembic/                         # database migrations
├── frontend/                        # Next.js app
├── pgis_bodyweight/
│   ├── api/                         # FastAPI app, schemas, routers
│   ├── coaching/                    # optional AI narration layer
│   ├── engine/                      # deterministic training logic
│   ├── library/                     # exercise YAML library
│   ├── models/                      # SQLAlchemy models and DB setup
│   └── tests/                       # pytest suite
├── main.py                          # local uvicorn runner
├── pyproject.toml                   # Python project metadata
├── railway.toml                     # Railway deployment config
└── NEXT_STEPS.md                    # current project roadmap
```
