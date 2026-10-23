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


user_repository = UserRepository()
