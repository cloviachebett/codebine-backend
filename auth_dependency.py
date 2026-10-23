import random
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import InvalidTokenError as JWTError
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from database import get_db
from models._enums import UserRole, AccountStatus
from models.users import User

pwd_hasher = PasswordHash.recommended()

ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES_ADMIN = int(os.getenv("ADMIN_TOKEN_EXPIRE_MINUTES", "5"))
ACCESS_TOKEN_EXPIRE_MINUTES_ANALYST = int(
    os.getenv("ANALYST_TOKEN_EXPIRE_MINUTES", "5")
)
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60
LOGIN_BLOCK_SECONDS = 900
API_QUOTA_PER_HOUR = 1000


def _load_pem(path_env: str, default: str) -> str:
    path = os.getenv(path_env, default)
    if not os.path.exists(path):
        path = default
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), default)
    with open(path, "r") as f:
        return f.read()


def load_private_key() -> str:
    return _load_pem("JWT_PRIVATE_KEY_PATH", "credentials/private.pem")


def load_public_key() -> str:
    return _load_pem("JWT_PUBLIC_KEY_PATH", "credentials/public.pem")


def hash_password(password: str) -> str:
    return pwd_hasher.hash(password)


def verify_password(plain: str, hashed: Optional[str]) -> bool:
    if not hashed:
        return False
    try:
        return pwd_hasher.verify(plain, hashed)
    except Exception:
        return False


# In-memory rate limiting / lockout state
_login_failures: dict[str, list[float]] = {}
_login_blocks: dict[str, float] = {}
_api_quota: dict[str, tuple[int, float]] = {}


def is_login_blocked(identifier: str) -> bool:
    until = _login_blocks.get(identifier)
    if until and until > time.time():
        return True
    if until:
        del _login_blocks[identifier]
    return False


def record_login_failure(identifier: str) -> None:
    now = time.time()
    attempts = [
        t for t in _login_failures.get(identifier, []) if now - t < LOGIN_WINDOW_SECONDS
    ]
    attempts.append(now)
    _login_failures[identifier] = attempts
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        _login_blocks[identifier] = now + LOGIN_BLOCK_SECONDS
        _login_failures.pop(identifier, None)


def clear_login_failures(identifier: str) -> None:
    _login_failures.pop(identifier, None)
    _login_blocks.pop(identifier, None)


def check_api_quota(user_id: str) -> bool:
    now = time.time()
    count, reset = _api_quota.get(user_id, (0, now + 3600))
    if now > reset:
        count, reset = 0, now + 3600
    if count >= API_QUOTA_PER_HOUR:
        _api_quota[user_id] = (count, reset)
        return False
    _api_quota[user_id] = (count + 1, reset)
    return True


def _token_expiry_minutes(role: UserRole) -> int:
    if role == UserRole.ADMIN:
        return ACCESS_TOKEN_EXPIRE_MINUTES_ADMIN
    return ACCESS_TOKEN_EXPIRE_MINUTES_ANALYST


def create_access_token(user_id: str, role: UserRole) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=_token_expiry_minutes(role))
    jti = secrets.token_urlsafe(16)
    to_encode = {
        "sub": str(user_id),
        "role": role.value,
        "exp": expire,
        "iat": now,
        "type": "access",
        "jti": jti,
    }
    return jwt.encode(to_encode, load_private_key(), algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = secrets.token_urlsafe(16)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "jti": jti,
    }
    token = jwt.encode(to_encode, load_private_key(), algorithm=ALGORITHM)
    # store jti validity in memory (simple)
    _refresh_tokens.add(jti)
    return token


_refresh_tokens: set[str] = set()
_blacklisted: dict[str, float] = {}


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, load_public_key(), algorithms=[ALGORITHM])
    except JWTError:
        return None


def is_token_blacklisted(jti: str) -> bool:
    if jti in _blacklisted:
        if _blacklisted[jti] > time.time():
            return True
        del _blacklisted[jti]
    return False


def blacklist_token(jti: str, expires_in: int) -> None:
    _blacklisted[jti] = time.time() + expires_in


def rotate_refresh_token(old_refresh_token: str) -> dict:
    payload = decode_token(old_refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    jti = payload.get("jti")
    if not jti or jti not in _refresh_tokens or is_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked"
        )
    _refresh_tokens.discard(jti)
    ttl = int(payload.get("exp", 0) - datetime.now(timezone.utc).timestamp())
    if ttl > 0:
        blacklist_token(jti, ttl)
    user_id = payload.get("sub")
    # role unknown here; default analyst
    new_access = create_access_token(user_id, UserRole.ANALYST)
    new_refresh = create_refresh_token(user_id)
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


security = HTTPBearer(auto_error=False)
CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect email or password",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jti = payload.get("jti")
    if jti and is_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked"
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject"
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    if user.account_status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive"
        )
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account locked"
        )
    # api quota
    if not check_api_quota(str(user.user_id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="API quota exceeded"
        )
    return user


def require_role(required: UserRole):
    async def checker(current_user: User = Depends(get_current_user)):
        hierarchy = {UserRole.ADMIN.value: 2, UserRole.ANALYST.value: 1}
        if hierarchy.get(
            current_user.role.value
            if hasattr(current_user.role, "value")
            else current_user.role,
            0,
        ) < hierarchy.get(required.value, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return current_user

    return checker


require_admin = require_role(UserRole.ADMIN)


def require_self_or_admin(user_id: str, current_user: User):
    role_val = (
        current_user.role.value
        if hasattr(current_user.role, "value")
        else current_user.role
    )
    if role_val == UserRole.ADMIN.value:
        return current_user
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    return current_user


# Email OTP (in-memory, for testing; replace with email service in prod)

_otp_store: dict[str, tuple[str, float]] = {}


def generate_email_otp(email: str) -> str:
    code = f"{random.randint(0, 999999):06d}"
    _otp_store[email.lower()] = (code, __import__("time").time() + 300)
    from services.email import send_otp_email

    send_otp_email(email, code)
    return code


def verify_email_otp(email: str, code: str) -> bool:
    entry = _otp_store.get(email.lower())
    if not entry:
        return False
    stored, expires = entry
    if __import__("time").time() > expires:
        _otp_store.pop(email.lower(), None)
        return False
    if stored != str(code).strip():
        return False
    _otp_store.pop(email.lower(), None)
    return True
