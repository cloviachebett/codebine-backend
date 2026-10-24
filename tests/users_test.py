import io
import os
import re
from contextlib import redirect_stdout

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from auth_dependency import hash_password
from database import Base, get_db
from main import app
from models._enums import AccountStatus, UserRole
from models.users import User

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _fk(dbapi_connection, _record):
    c = dbapi_connection.cursor()
    c.execute("PRAGMA foreign_keys=ON")
    c.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    def override():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_user(
    db, email="admin@test.rw", password="AdminPass12345!", role=UserRole.ADMIN
):
    u = User(
        full_name="Admin",
        email=email,
        password_hash=hash_password(password),
        role=role,
        account_status=AccountStatus.ACTIVE,
    )
    db.add(u)
    db.commit()
    return u


def _login(client, email, password):
    buf = io.StringIO()
    with redirect_stdout(buf):
        r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    m = re.search(r"\[OTP for .*?\]: (\d+)", buf.getvalue())
    assert m, buf.getvalue()
    code = m.group(1)
    r2 = client.post("/auth/verify-otp", json={"email": email, "code": code})
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


def test_login_returns_tokens(client, db_session, monkeypatch):
    _make_user(db_session)
    monkeypatch.setenv("EMAIL_HOST", "")
    token = _login(client, "admin@test.rw", "AdminPass12345!")
    assert token


def test_login_bad_credentials(client, db_session):
    _make_user(db_session)
    r = client.post("/auth/login", json={"email": "admin@test.rw", "password": "wrong"})
    assert r.status_code == 401


def test_register_analyst_requires_admin(client, db_session, monkeypatch):
    monkeypatch.setenv("EMAIL_HOST", "")
    _make_user(
        db_session,
        email="analyst@test.rw",
        role=UserRole.ANALYST,
        password="AnalystPass12345!",
    )
    # analyst login works but cannot register
    token = _login(client, "analyst@test.rw", "AnalystPass12345!")
    r2 = client.post(
        "/users",
        json={"full_name": "New", "email": "new@test.rw", "password": "NewPass12345!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 403


def test_admin_registers_analyst(client, db_session, monkeypatch):
    monkeypatch.setenv("EMAIL_HOST", "")
    _make_user(db_session)
    token = _login(client, "admin@test.rw", "AdminPass12345!")
    r2 = client.post(
        "/users",
        json={
            "full_name": "Analyst One",
            "email": "analyst1@test.rw",
            "password": "AnalystPass12345!",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 201
    assert r2.json()["role"] == "ANALYST"


def test_otp_flow(client, db_session, monkeypatch):
    monkeypatch.setenv("EMAIL_HOST", "")
    _make_user(db_session)
    token = _login(client, "admin@test.rw", "AdminPass12345!")
    assert token


def test_me_endpoint(client, db_session, monkeypatch):
    monkeypatch.setenv("EMAIL_HOST", "")
    _make_user(db_session)
    token = _login(client, "admin@test.rw", "AdminPass12345!")
    r2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["email"] == "admin@test.rw"


def test_forgot_and_reset_password(client, db_session):
    _make_user(db_session)
    r = client.post("/auth/forgot-password", json={"email": "admin@test.rw"})
    assert r.status_code == 200
    assert "message" in r.json()


def test_refresh_token(client, db_session, monkeypatch):
    monkeypatch.setenv("EMAIL_HOST", "")
    _make_user(db_session)
    # need a refresh token: login returns otp_required, verify-otp returns refresh
    buf = io.StringIO()
    with redirect_stdout(buf):
        client.post(
            "/auth/login",
            json={"email": "admin@test.rw", "password": "AdminPass12345!"},
        )
    m = re.search(r"\[OTP for .*?\]: (\d+)", buf.getvalue())
    code = m.group(1)
    r2 = client.post("/auth/verify-otp", json={"email": "admin@test.rw", "code": code})
    refresh = r2.json()["refresh_token"]
    r3 = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r3.status_code == 200
    assert "access_token" in r3.json()


def test_logout(client, db_session, monkeypatch):
    monkeypatch.setenv("EMAIL_HOST", "")
    _make_user(db_session)
    token = _login(client, "admin@test.rw", "AdminPass12345!")
    r2 = client.post(
        "/auth/logout",
        json={"access_jti": "x", "refresh_jti": "y"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200


def test_get_user_self(client, db_session, monkeypatch):
    monkeypatch.setenv("EMAIL_HOST", "")
    u = _make_user(db_session)
    token = _login(client, "admin@test.rw", "AdminPass12345!")
    r2 = client.get(f"/users/{u.user_id}", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200


def test_list_users_admin(client, db_session, monkeypatch):
    monkeypatch.setenv("EMAIL_HOST", "")
    _make_user(db_session)
    token = _login(client, "admin@test.rw", "AdminPass12345!")
    r2 = client.get("/users/", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200


def test_delete_user(client, db_session, monkeypatch):
    monkeypatch.setenv("EMAIL_HOST", "")
    _make_user(db_session)
    token = _login(client, "admin@test.rw", "AdminPass12345!")
    r2 = client.post(
        "/users",
        json={"full_name": "Del", "email": "del@test.rw", "password": "DelPass12345!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    uid = r2.json()["user_id"]
    r3 = client.delete(f"/users/{uid}", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
