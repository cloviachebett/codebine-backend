import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from auth_dependency import (
    CREDENTIALS_ERROR,
    clear_login_failures,
    create_access_token,
    create_refresh_token,
    generate_email_otp,
    hash_password,
    is_login_blocked,
    record_login_failure,
    verify_email_otp,
)
from models.users import User
from repositories.users import user_repository
from services.users import authenticate_user


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def login(db, email: str, password: str) -> dict:
    identifier = email.lower().strip()
    if is_login_blocked(identifier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account locked. Try again later.",
        )
    user = authenticate_user(db, identifier, password)
    if user is None:
        record_login_failure(identifier)
        raise CREDENTIALS_ERROR
    clear_login_failures(identifier)
    generate_email_otp(user.email)
    return {"otp_required": True, "message": "OTP sent to email"}


def verify_otp(db, email: str, code: str) -> dict:
    user = user_repository.get_by_email(db, email)
    if user is None or not verify_email_otp(email, code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP"
        )
    role_val = user.role.value if hasattr(user.role, "value") else user.role
    access = create_access_token(str(user.user_id), user.role)
    refresh = create_refresh_token(str(user.user_id))
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "role": role_val,
    }


def forgot_password(db, email: str) -> dict:
    user = user_repository.get_by_email(db, email)
    if user is not None:
        token = secrets.token_urlsafe(32)
        user.reset_token_hash = _hash_token(token)
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        print(f"[RESET TOKEN for {email}]: {token}")
    return {"message": "If that email exists, a reset link has been sent."}


def validate_reset_token(db, token: str) -> bool:
    user = (
        db.query(User)
        .filter(
            User.reset_token_hash == _hash_token(token),
            User.reset_token_expires > datetime.now(timezone.utc),
        )
        .first()
    )
    return user is not None


def reset_password(db, token: str, new_password: str) -> None:
    user = (
        db.query(User)
        .filter(
            User.reset_token_hash == _hash_token(token),
            User.reset_token_expires > datetime.now(timezone.utc),
        )
        .first()
    )
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user.password_hash = hash_password(new_password)
    user.reset_token_hash = None
    user.reset_token_expires = None
    db.commit()


def verify_email(db, token: str) -> None:
    user = (
        db.query(User)
        .filter(
            User.verification_token_hash == _hash_token(token),
            User.verification_token_expires > datetime.now(timezone.utc),
        )
        .first()
    )
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user.is_verified = True
    user.verification_token_hash = None
    user.verification_token_expires = None
    db.commit()


def reset_password_page(db, token: str) -> dict:
    if not validate_reset_token(db, token):
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    return {"valid": True}


def logout(db, access_jti=None, refresh_jti=None) -> dict:
    from auth_dependency import blacklist_token

    if access_jti:
        blacklist_token(access_jti, 300)
    if refresh_jti:
        blacklist_token(refresh_jti, 86400)
    return {"message": "Logged out"}


def get_me(current_user) -> dict:
    role_val = (
        current_user.role.value
        if hasattr(current_user.role, "value")
        else current_user.role
    )
    status_val = (
        current_user.account_status.value
        if hasattr(current_user.account_status, "value")
        else current_user.account_status
    )
    return {
        "user_id": str(current_user.user_id),
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": role_val,
        "account_status": status_val,
        "mfa_enrolled": current_user.mfa_enrolled,
    }
