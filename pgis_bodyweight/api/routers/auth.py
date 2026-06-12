"""
Authentication endpoints: register and login.

JWTs are signed with HS256. The secret is read from JWT_SECRET env var — Railway
must have this set. Never log credentials or tokens.
"""
from __future__ import annotations

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from pgis_bodyweight.api.security import make_token
from pgis_bodyweight.models.db import get_db
from pgis_bodyweight.models.tables import User

router = APIRouter(prefix="/v1/auth", tags=["auth"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user_id: str
    token: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="email already registered")
    user = User(email=body.email, password_hash=bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode())
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(user_id=user.id, token=make_token(user.id))


@router.post("/login", response_model=AuthResponse)
def login(body: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.password_hash or not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return AuthResponse(user_id=user.id, token=make_token(user.id))
