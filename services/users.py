import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from auth_dependency import hash_password, require_self_or_admin, verify_password
from models._enums import UserRole, AccountStatus
from models.users import User
from repositories.users import user_repository as user_repo
from schemas.users import UserCreate, UserUpdate


def authenticate_user(db, email: str, password: str):
    user = user_repo.get_by_email(db, email)
    if user is None:
        return None
    if user.account_status != AccountStatus.ACTIVE:
        return None
    if user.is_locked:
        return None
    if not verify_password(password, user.password_hash):
        return None
    user_repo.update_last_login(db, user)
    return user


def create_user(db, payload: UserCreate, creator):
    if user_repo.get_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    role = UserRole.ANALYST
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=role,
        phone=payload.phone,
        mfa_enrolled=True,
        account_status=AccountStatus.ACTIVE,
    )
    return user_repo.create(db, user)


def get_user(db, user_id, current_user=None):
    if current_user is not None:
        require_self_or_admin(str(user_id), current_user)
    user = user_repo.get(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def list_users(db):
    return user_repo.get_all(db)


def update_user(db, user_id, payload: UserUpdate, current_user):
    require_self_or_admin(str(user_id), current_user)
    user = user_repo.get(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.account_status is not None:
        from models._enums import AccountStatus

        user.account_status = AccountStatus(payload.account_status)
    return user_repo.update_fields(db, user)


def delete_user(db, user_id):
    deleted = user_repo.delete(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return True


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def request_password_reset(db, email: str) -> None:
    user = user_repo.get_by_email(db, email)
    if user is not None:
        token = secrets.token_urlsafe(32)
        user_repo.set_reset_token(
            db,
            user,
            _hash_token(token),
            datetime.now(timezone.utc) + timedelta(hours=1),
        )
        print(f"[RESET TOKEN for {email}]: {token}")


def reset_user_password(db, token: str, new_password: str) -> bool:
    user = user_repo.get_by_reset_token(db, _hash_token(token))
    if (
        user is None
        or user.reset_token_expires is None
        or user.reset_token_expires <= datetime.now(timezone.utc)
    ):
        return False
    user_repo.set_password(db, user, hash_password(new_password))
    user_repo.clear_reset_token(db, user)
    return True


def verify_user_email(db, token: str) -> bool:
    user = user_repo.get_by_verification_token(db, _hash_token(token))
    if (
        user is None
        or user.verification_token_expires is None
        or user.verification_token_expires <= datetime.now(timezone.utc)
    ):
        return False
    user_repo.set_verified(db, user)
    return True


def validate_reset_token(db, token: str) -> bool:
    user = user_repo.get_by_reset_token(db, _hash_token(token))
    if user is None:
        return False
    return (
        user.reset_token_expires is not None
        and user.reset_token_expires > datetime.now(timezone.utc)
    )
