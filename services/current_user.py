import os
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from auth_dependency import (
    get_current_user as _jwt_get_current_user,
)
from database import get_db
from models._enums import AccountStatus
from models.users import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    dev_user_id = os.getenv("DEV_USER_ID")
    if dev_user_id:
        try:
            user = db.get(User, UUID(dev_user_id))
        except ValueError:
            user = None
        if (
            user is not None
            and user.account_status == AccountStatus.ACTIVE
            and not user.is_locked
        ):
            return user
        if user is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )
    # delegate to JWT auth
    return await _jwt_get_current_user(credentials, db)
