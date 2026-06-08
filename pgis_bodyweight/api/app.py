from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from pgis_bodyweight.api.routers import intake, programs, users
from pgis_bodyweight.models.db import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="PGIS Body Weight",
    description="Glucose-aware bodyweight training engine.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(users.router)
app.include_router(intake.router)
app.include_router(programs.router)
