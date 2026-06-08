from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from pgis_bodyweight.api.schemas import UserResponse
from pgis_bodyweight.models.db import get_db
from pgis_bodyweight.models.tables import User

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
def create_user(db: Session = Depends(get_db)) -> UserResponse:
    """Create a new user record. Returns the user_id for subsequent requests."""
    user = User()
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(user_id=user.id)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: str, db: Session = Depends(get_db)) -> None:
    """Delete a user and all associated data (intake, programs, logs)."""
    user = db.get(User, user_id)
    if user:
        db.delete(user)
        db.commit()
