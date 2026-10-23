import os
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models._enums import AccountStatus
from models.users import User


def get_current_user(db: Session = Depends(get_db)) -> User:
    user = None
    dev_user_id = os.getenv("DEV_USER_ID")
    if dev_user_id:
        try:
            user = db.get(User, UUID(dev_user_id))
        except ValueError:
            user = None
    if user is None or user.account_status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
