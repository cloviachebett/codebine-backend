from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.users import User


class UserRepository:
    def __init__(self):
        self.model = User

    def get(self, db: Session, user_id):
        from uuid import UUID as _UUID

        try:
            user_id = _UUID(str(user_id))
        except (ValueError, AttributeError):
            pass
        return db.get(self.model, user_id)

    def get_by_email(self, db: Session, email: str):
        return db.query(self.model).filter(self.model.email == email).first()

    def get_all(self, db: Session):
        return db.query(self.model).all()

    def create(self, db: Session, user: User):
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def delete(self, db: Session, user_id) -> bool:
        from uuid import UUID as _UUID

        try:
            user_id = _UUID(str(user_id))
        except (ValueError, AttributeError):
            pass
        user = db.get(self.model, user_id)
        if user is None:
            return False
        db.delete(user)
        db.commit()
        return True

    def get_by_reset_token(self, db: Session, token_hash: str):
        return (
            db.query(self.model)
            .filter(self.model.reset_token_hash == token_hash)
            .first()
        )

    def get_by_verification_token(self, db: Session, token_hash: str):
        return (
            db.query(self.model)
            .filter(self.model.verification_token_hash == token_hash)
            .first()
        )

    def update_last_login(self, db: Session, user: User) -> None:
        user.last_login_at = datetime.now(timezone.utc)
        user.failed_login_attempts = 0
        db.commit()

    def update_fields(self, db: Session, user: User) -> User:
        db.commit()
        db.refresh(user)
        return user

    def set_reset_token(
        self, db: Session, user: User, token_hash: str, expires
    ) -> None:
        user.reset_token_hash = token_hash
        user.reset_token_expires = expires
        db.commit()

    def clear_reset_token(self, db: Session, user: User) -> None:
        user.reset_token_hash = None
        user.reset_token_expires = None
        db.commit()

    def set_password(self, db: Session, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        db.commit()

    def set_verified(self, db: Session, user: User) -> None:
        user.is_verified = True
        user.verification_token_hash = None
        user.verification_token_expires = None
        db.commit()

    def set_verification_token(
        self, db: Session, user: User, token_hash: str, expires
    ) -> None:
        user.verification_token_hash = token_hash
        user.verification_token_expires = expires
        db.commit()


user_repository = UserRepository()
