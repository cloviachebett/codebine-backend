import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from auth_dependency import hash_password
from models._enums import UserRole, AccountStatus
from models.users import User
from repositories.users import user_repository

email = os.getenv("ADMIN_EMAIL")
password = os.getenv("ADMIN_PASSWORD")
full_name = os.getenv("ADMIN_NAME", "System Administrator")

if not email or not password:
    raise SystemExit("ADMIN_EMAIL and ADMIN_PASSWORD must be set in .env")

db = SessionLocal()
try:
    existing = user_repository.get_by_email(db, email)
    if existing and "--reset-password" in sys.argv:
        user_repository.set_password(db, existing, hash_password(password))
        print(f"Password reset for: {email}")
    elif existing:
        print(f"Admin already exists: {email}")
    else:
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            account_status=AccountStatus.ACTIVE,
            is_verified=True,
        )
        user_repository.create(db, user)
        print(f"Created admin: {email}")
finally:
    db.close()
