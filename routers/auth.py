from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth_dependency import (
    get_current_user,
    create_access_token,
    create_refresh_token,
    rotate_refresh_token,
    blacklist_token,
    is_login_blocked,
    record_login_failure,
    clear_login_failures,
    CREDENTIALS_ERROR,
    generate_email_otp,
)
from database import get_db
from models.users import User
from schemas.users import (
    LoginRequest,
    TokenResponse,
    RefreshPayload,
    VerifyOtpRequest,
    ForgotPasswordRequest,
    ResetPasswordPayload,
)
from services import users as user_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    identifier = payload.email.lower().strip()
    if is_login_blocked(identifier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account locked. Try again later.",
        )
    user = user_service.authenticate_user(db, identifier, payload.password)
    if user is None:
        record_login_failure(identifier)
        raise CREDENTIALS_ERROR
    clear_login_failures(identifier)
    generate_email_otp(user.email)
    return {"otp_required": True, "message": "OTP sent to email"}


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshPayload):
    result = rotate_refresh_token(payload.refresh_token)
    return TokenResponse(**result, role="ANALYST")


@router.post("/logout")
def logout(payload: dict, current_user: User = Depends(get_current_user)):
    access_jti = payload.get("access_jti")
    refresh_jti = payload.get("refresh_jti")
    if access_jti:
        blacklist_token(access_jti, 300)
    if refresh_jti:
        blacklist_token(refresh_jti, 86400)
    return {"message": "Logged out"}


@router.post("/verify-otp")
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    from auth_dependency import (
        verify_email_otp,
    )
    from repositories.users import user_repository

    email = payload.email
    code = payload.code
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


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
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


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):

    user_service.request_password_reset(db, payload.email)
    return {"message": "If that email exists, a reset link has been sent."}


@router.get("/reset-password")
def reset_password_page(token: str = Query(...), db: Session = Depends(get_db)):
    if not user_service.validate_reset_token(db, token):
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    return {"valid": True}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordPayload, db: Session = Depends(get_db)):

    if not user_service.reset_user_password(db, payload.token, payload.new_password):
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    return {"message": "Password updated successfully"}


@router.get("/verify-email")
def verify_email(token: str = Query(...), db: Session = Depends(get_db)):
    if not user_service.verify_user_email(db, token):
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    return {"message": "Email verified"}
