from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth_dependency import get_current_user, require_admin, require_self_or_admin
from database import get_db
from models.users import User
from schemas.users import UserCreate, UserRead, UserUpdate
from services import users as user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db), current_admin: User = Depends(require_admin)
):
    return user_service.list_users(db)


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self_or_admin(user_id, current_user)
    user = user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=UserRead, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    from repositories.users import user_repository as user_repo

    if user_repo.get_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return user_service.create_user(db, payload, current_admin)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self_or_admin(user_id, current_user)
    user = user_service.update_user(db, user_id, payload, current_user)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    deleted = user_service.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}
