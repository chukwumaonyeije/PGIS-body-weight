from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pgis_bodyweight.api.routers import auth, coaching, glucose, intake, programs, users
from pgis_bodyweight.models.db import DATABASE_URL, create_tables

_ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if DATABASE_URL.startswith("postgresql"):
        from alembic import command
        from alembic.config import Config as AlembicConfig
        alembic_cfg = AlembicConfig("alembic.ini")
        command.upgrade(alembic_cfg, "head")
    else:
        create_tables()
    yield


app = FastAPI(
    title="PGIS Body Weight",
    description="Glucose-aware bodyweight training engine.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(intake.router)
app.include_router(programs.router)
app.include_router(coaching.router)
app.include_router(glucose.router)


@app.get("/health", include_in_schema=False)
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
