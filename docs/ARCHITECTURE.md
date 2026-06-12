# PGIS Body Weight Architecture

This document is a quick technical map for developers entering the PGIS Body Weight repository.

## System Shape

PGIS Body Weight is a full-stack app with a Next.js frontend and a FastAPI backend.

```text
Browser
  -> Next.js frontend in frontend/
  -> FastAPI backend at pgis_bodyweight.api.app:app
  -> SQLAlchemy persistence
  -> SQLite locally or PostgreSQL in production
```

The core training logic is intentionally kept outside the API layer. The backend routes translate HTTP payloads into engine dataclasses, call deterministic engine functions, and persist the results.

## Backend Entry Point

The canonical ASGI app is:

```text
pgis_bodyweight.api.app:app
```

It is created in:

```text
pgis_bodyweight/api/app.py
```

The app setup does four main things:

- Configures CORS using `ALLOWED_ORIGINS`.
- Runs startup database setup.
- Includes all API routers.
- Exposes `/health` for deployment health checks.

Startup behavior:

- If `DATABASE_URL` starts with `postgresql`, Alembic migrates to `head`.
- Otherwise, local/dev SQLite uses `Base.metadata.create_all()`.

## API Routes

Router files live in:

```text
pgis_bodyweight/api/routers/
```

Current routers:

| Router | Prefix | Purpose |
|---|---|---|
| `auth.py` | `/v1/auth` | Register and login with bcrypt + JWT |
| `users.py` | `/v1/users` | Legacy/simple user creation and deletion |
| `intake.py` | `/v1/intake` | Stateless intake assessment and persisted intake submission |
| `programs.py` | `/v1/programs` | Program generation, current program lookup, next session, session logging |
| `coaching.py` | `/v1/programs/{program_id}/sessions/{week}/{day}/coaching` | Optional coaching prose |
| `glucose.py` | `/v1/glucose` | Manual glucose reading entry |

HTTP schemas live in:

```text
pgis_bodyweight/api/schemas.py
```

Conversion from API schema objects into engine dataclasses lives in:

```text
pgis_bodyweight/api/_conversion.py
```

## Training Engine

The deterministic training engine lives in:

```text
pgis_bodyweight/engine/
```

Important files:

| File | Purpose |
|---|---|
| `types.py` | Engine dataclasses, enums, clinical/programming constants |
| `safety.py` | PAR-Q gate, hypoglycemia risk, impact suppression |
| `patterns.py` | Starting movement-pattern levels from intake tests |
| `generator.py` | 4-week mesocycle generation |
| `autoregulate.py` | Level progression/hold logic after logged RPE |

The engine should remain pure where possible:

- No database access
- No network calls
- No randomness
- No clock reads in core generation

This makes program generation auditable and testable.

## Exercise Library

Exercise definitions live in:

```text
pgis_bodyweight/library/exercises/
```

These YAML files define fixed warmup/cooldown blocks and movement-pattern ladders. The loader layer converts those YAML definitions into engine exercise objects.

Key principle: contraindication tags and substitutions should be clinically reviewed before broad use.

## Persistence

Database setup lives in:

```text
pgis_bodyweight/models/
```

Important files:

| File | Purpose |
|---|---|
| `base.py` | SQLAlchemy declarative base |
| `db.py` | Engine/session factory and `DATABASE_URL` handling |
| `tables.py` | ORM table definitions |

Current tables:

- `users`
- `intake_submissions`
- `generated_programs`
- `session_logs`
- `progression_states`
- `glucose_readings`

Sensitive data note:

- `intake_json`, glucose readings, RPE, and health-related notes should not be logged raw.
- Production storage/privacy expectations should be reviewed before accepting real users.
- The frontend displays a reusable `SafetyNotice` in the auth, intake, program, and session flows.

## Migrations

Alembic configuration lives at:

```text
alembic.ini
alembic/
```

Migration files live in:

```text
alembic/versions/
```

The migration chain now creates the schema in order:

1. Core users/intake/program/session tables
2. Progression state table
3. Glucose readings table
4. Auth fields on users

Verify migrations against a fresh temporary SQLite database with:

```bash
$env:DATABASE_URL='sqlite:///C:/tmp/pgis_bodyweight_migration_check.db'
uv run alembic upgrade head
```

## Frontend

The frontend is a Next.js app in:

```text
frontend/
```

Current App Router pages:

| Route | File | Purpose |
|---|---|---|
| `/` | `frontend/src/app/page.tsx` | Redirects to login or program |
| `/login` | `frontend/src/app/login/page.tsx` | Login screen |
| `/register` | `frontend/src/app/register/page.tsx` | Registration screen |
| `/intake` | `frontend/src/app/intake/page.tsx` | 4-step intake wizard |
| `/program` | `frontend/src/app/program/page.tsx` | Generated program view |
| `/program/session` | `frontend/src/app/program/session/page.tsx` | Individual session view |

Shared frontend helpers:

| File | Purpose |
|---|---|
| `frontend/src/lib/api.ts` | Backend API client and shared TypeScript types |
| `frontend/src/lib/auth.ts` | localStorage token/user helpers |
| `frontend/src/lib/utils.ts` | UI utility helpers |
| `frontend/src/components/AuthForm.tsx` | Shared login/register form |

The frontend reads the backend base URL from:

```text
NEXT_PUBLIC_API_URL
```

If unset, it defaults to:

```text
http://localhost:8000
```

## Authentication Boundary

Current state:

- The backend can register and log in users.
- Passwords are hashed with bcrypt.
- JWTs are issued by `/v1/auth/register` and `/v1/auth/login`.
- The frontend stores token and user ID in `localStorage`.
- The frontend sends `Authorization: Bearer <token>`.

Hardening still needed:

- Validate JWTs on user-specific routes.
- Derive the current user ID from the token.
- Stop trusting submitted/query-string `user_id` for protected operations.
- Add tests for missing token, invalid token, expired token, and wrong-user access.

## Primary Data Flow

```text
Register/login
  -> frontend stores token + user_id
  -> intake form submits user_id + intake
  -> backend validates intake and stores IntakeSubmission
  -> frontend requests generation from intake_id
  -> engine generates deterministic 4-week program
  -> backend stores GeneratedProgram.program_json
  -> frontend displays program and session details
```

Session logging flow:

```text
Frontend submits completion/RPE data
  -> backend stores SessionLog
  -> autoregulation may update ProgressionState
```

Glucose flow:

```text
Frontend/API submits manual glucose reading
  -> backend stores GlucoseReading
  -> future PGIS data loop can correlate sessions and glycemic response
```

## Deployment Shape

Intended deployment:

| Component | Host |
|---|---|
| Backend | Railway |
| Database | Railway PostgreSQL |
| Frontend | Vercel |

Production environment variables:

Backend:

```text
DATABASE_URL
JWT_SECRET
ALLOWED_ORIGINS
ANTHROPIC_API_KEY optional
```

JWT secret behavior:

- Local development can use the fallback secret when no production marker is present.
- Startup fails if `ENVIRONMENT=production`, `APP_ENV=prod`, or `RAILWAY_ENVIRONMENT` is set and `JWT_SECRET` is missing.
- Startup also fails if production is configured with the development fallback secret.

Frontend:

```text
NEXT_PUBLIC_API_URL
```

## Verification Commands

Backend:

```bash
uv sync --extra test
uv run pytest
uv run alembic upgrade head
```

Frontend:

```bash
cd frontend
npm install
npm run lint
npm run build
```

## Current Hardening Priorities

1. Keep dependency and build verification green.
2. Upgrade vulnerable frontend dependencies before public deployment.
3. Enforce JWT authentication on user-specific API routes.
4. Add visible clinical/privacy disclaimers to the user-facing app.
5. Keep clinical norming and contraindication decisions documented in code, tests, and user-facing language.
