from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth_dependency import get_current_user
from database import get_db
from models.users import User
from schemas.users import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshPayload,
    ResetPasswordPayload,
    TokenResponse,
    VerifyOtpRequest,
)
from services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login(db, payload.email, payload.password)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshPayload):
    from auth_dependency import rotate_refresh_token

    result = rotate_refresh_token(payload.refresh_token)
    return TokenResponse(**result, role="ANALYST")


@router.post("/logout")
def logout(payload: dict, current_user: User = Depends(get_current_user)):
    return auth_service.logout(payload.get("access_jti"), payload.get("refresh_jti"))


@router.post("/verify-otp")
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    return auth_service.verify_otp(db, payload.email, payload.code)


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return auth_service.get_me(current_user)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    return auth_service.forgot_password(db, payload.email)


@router.get("/reset-password")
def reset_password_page(token: str = Query(...), db: Session = Depends(get_db)):
    return auth_service.reset_password_page(db, token)


@router.post("/reset-password")
def reset_password(payload: ResetPasswordPayload, db: Session = Depends(get_db)):
    auth_service.reset_password(db, payload.token, payload.new_password)
    return {"message": "Password updated successfully"}


@router.get("/verify-email")
def verify_email(token: str = Query(...), db: Session = Depends(get_db)):
    auth_service.verify_email(db, token)
    return {"message": "Email verified"}
