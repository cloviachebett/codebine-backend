from datetime import datetime, timezone

from sqlalchemy.orm import Session

from auth_dependency import hash_password, verify_password
from models._enums import UserRole, AccountStatus
from models.users import User
from repositories.users import user_repository as user_repo
from schemas.users import UserCreate, UserUpdate


def authenticate_user(db: Session, email: str, password: str):
    user = user_repo.get_by_email(db, email)
    if user is None:
        return None
    if user.account_status != AccountStatus.ACTIVE:
        return None
    if user.is_locked:
        return None
    if not verify_password(password, user.password_hash):
        return None
    user.last_login_at = datetime.now(timezone.utc)
    user.failed_login_attempts = 0
    db.commit()
    return user


def create_user(db: Session, payload: UserCreate, creator):
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


def get_user(db: Session, user_id):
    return user_repo.get(db, user_id)


def list_users(db: Session):
    return user_repo.get_all(db)


def update_user(db: Session, user_id, payload: UserUpdate, current_user):
    user = user_repo.get(db, user_id)
    if user is None:
        return None
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.account_status is not None:
        user.account_status = AccountStatus(payload.account_status)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id):
    return user_repo.delete(db, user_id)


def enable_mfa(db: Session, user: User, code: str) -> bool:
    from auth_dependency import verify_totp

    if not user.mfa_secret if hasattr(user, "mfa_secret") else True:
        return False
    return verify_totp(getattr(user, "mfa_secret", ""), code)
