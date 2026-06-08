from __future__ import annotations

from fastapi import FastAPI

from pgis_bodyweight.api.routers import intake, programs

app = FastAPI(
    title="PGIS Body Weight",
    description="Glucose-aware bodyweight training engine.",
    version="0.1.0",
)

app.include_router(intake.router)
app.include_router(programs.router)
