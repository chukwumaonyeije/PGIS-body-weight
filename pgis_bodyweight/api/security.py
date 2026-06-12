"""JWT creation and request authentication helpers."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt

_DEV_JWT_SECRET = "dev-secret-change-in-prod"
_PRODUCTION_ENV_VALUES = {"production", "prod"}


def _is_production_environment() -> bool:
    environment = os.environ.get("ENVIRONMENT", "").lower()
    app_env = os.environ.get("APP_ENV", "").lower()
    railway_environment = os.environ.get("RAILWAY_ENVIRONMENT", "").lower()
    return (
        environment in _PRODUCTION_ENV_VALUES
        or app_env in _PRODUCTION_ENV_VALUES
        or bool(railway_environment)
    )


def _resolve_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if _is_production_environment():
        if not secret:
            raise RuntimeError("JWT_SECRET must be set in production")
        if secret == _DEV_JWT_SECRET:
            raise RuntimeError("JWT_SECRET must not use the development fallback in production")
        return secret
    return secret or _DEV_JWT_SECRET


_JWT_SECRET = _resolve_jwt_secret()
_ALGORITHM = "HS256"
_TOKEN_EXPIRE_DAYS = 30

_bearer = HTTPBearer(auto_error=False)


def make_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": user_id, "exp": expire}, _JWT_SECRET, algorithm=_ALGORITHM)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )

    try:
        payload = jwt.decode(credentials.credentials, _JWT_SECRET, algorithms=[_ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token expired",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
        )

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token subject",
        )
    return user_id


def require_matching_user(requested_user_id: str, current_user_id: str) -> None:
    if requested_user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user_id does not match token",
        )
