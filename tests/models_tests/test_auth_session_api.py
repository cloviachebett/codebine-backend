import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import auth_dependency
from auth_dependency import create_refresh_token, decode_token
from models._enums import AccountStatus, UserRole

VERCEL = "https://codebine-dashboard.vercel.app"


@pytest.fixture
def save_user(db_session, make_user):
    def _save(**overrides):
        user = make_user(**overrides)
        db_session.add(user)
        db_session.commit()
        return user

    return _save


@pytest.mark.parametrize("origin", [VERCEL, "http://localhost:3000"])
def test_login_preflight_allows_the_dashboard(client, origin):
    response = client.options(
        "/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_unknown_origin_is_not_allowed(client):
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_simple_request_gets_the_cors_header(client):
    response = client.get("/health", headers={"Origin": VERCEL})
    assert response.headers["access-control-allow-origin"] == VERCEL


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.ANALYST])
def test_refresh_keeps_the_real_role(client, save_user, role):
    user = save_user(role=role, account_status=AccountStatus.ACTIVE)
    response = client.post(
        "/auth/refresh", json={"refresh_token": create_refresh_token(str(user.user_id))}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == role.value
    assert decode_token(data["access_token"])["role"] == role.value


def test_refresh_token_can_be_used_once(client, save_user):
    user = save_user(role=UserRole.ADMIN, account_status=AccountStatus.ACTIVE)
    body = {"refresh_token": create_refresh_token(str(user.user_id))}
    assert client.post("/auth/refresh", json=body).status_code == 200
    assert client.post("/auth/refresh", json=body).status_code == 401


def test_refresh_is_refused_for_a_suspended_user(client, save_user):
    user = save_user(role=UserRole.ANALYST, account_status=AccountStatus.SUSPENDED)
    response = client.post(
        "/auth/refresh", json={"refresh_token": create_refresh_token(str(user.user_id))}
    )
    assert response.status_code == 401


def test_signing_keys_can_come_from_config_vars(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    monkeypatch.setenv("JWT_PRIVATE_KEY_B64", base64.b64encode(private_pem).decode())
    monkeypatch.setenv("JWT_PUBLIC_KEY_B64", base64.b64encode(public_pem).decode())

    assert auth_dependency.load_private_key() == private_pem.decode()
    assert auth_dependency.load_public_key() == public_pem.decode()


def test_otp_is_six_digits(monkeypatch):
    monkeypatch.setattr("services.email.send_otp_email", lambda email, code: None)
    code = auth_dependency.generate_email_otp("someone@example.com")
    assert len(code) == 6 and code.isdigit()
    assert auth_dependency.verify_email_otp("someone@example.com", code)


def _login_as(user):
    from auth_dependency import get_current_user as jwt_user
    from main import app

    app.dependency_overrides[jwt_user] = lambda: user


@pytest.fixture
def captured_emails(monkeypatch):
    sent = {}
    monkeypatch.setattr(
        "services.email.send_otp_email", lambda email, code: sent.update(otp=code)
    )
    monkeypatch.setattr(
        "services.email.send_password_reset_email",
        lambda email, token: sent.update(reset=token),
    )
    return sent


def test_full_login_with_password_and_otp(client, save_user, captured_emails):
    save_user(
        email="admin@terrawatch.rw",
        password_hash=auth_dependency.hash_password("Correct-Pass-2026!"),
        role=UserRole.ADMIN,
        account_status=AccountStatus.ACTIVE,
    )
    login = client.post(
        "/auth/login",
        json={"email": "admin@terrawatch.rw", "password": "Correct-Pass-2026!"},
    )
    assert login.json()["otp_required"] is True
    verified = client.post(
        "/auth/verify-otp",
        json={"email": "admin@terrawatch.rw", "code": captured_emails["otp"]},
    )
    assert verified.status_code == 200
    assert verified.json()["role"] == "ADMIN"
    token = verified.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "admin@terrawatch.rw"


def test_wrong_password_is_refused(client, save_user, captured_emails):
    save_user(
        email="analyst@terrawatch.rw",
        password_hash=auth_dependency.hash_password("Correct-Pass-2026!"),
        account_status=AccountStatus.ACTIVE,
    )
    response = client.post(
        "/auth/login", json={"email": "analyst@terrawatch.rw", "password": "wrong"}
    )
    assert response.status_code == 401
    assert "otp" not in captured_emails


def test_otp_stops_working_after_five_wrong_codes(save_user, captured_emails):
    code = auth_dependency.generate_email_otp("guess@terrawatch.rw")
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert not auth_dependency.verify_email_otp("guess@terrawatch.rw", wrong)
    assert not auth_dependency.verify_email_otp("guess@terrawatch.rw", code)


def test_forgot_and_reset_password(client, save_user, captured_emails):
    save_user(
        email="forgot@terrawatch.rw",
        password_hash=auth_dependency.hash_password("Old-Password-2026!"),
        account_status=AccountStatus.ACTIVE,
    )
    response = client.post(
        "/auth/forgot-password", json={"email": "forgot@terrawatch.rw"}
    )
    assert response.status_code == 200
    token = captured_emails["reset"]

    reset = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "New-Password-2026!"},
    )
    assert reset.status_code == 200
    again = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "Another-Pass-2026!"},
    )
    assert again.status_code == 400

    old = client.post(
        "/auth/login",
        json={"email": "forgot@terrawatch.rw", "password": "Old-Password-2026!"},
    )
    new = client.post(
        "/auth/login",
        json={"email": "forgot@terrawatch.rw", "password": "New-Password-2026!"},
    )
    assert old.status_code == 401
    assert new.status_code == 200


def test_forgot_password_does_not_reveal_unknown_emails(client, captured_emails):
    response = client.post(
        "/auth/forgot-password", json={"email": "nobody@terrawatch.rw"}
    )
    assert response.status_code == 200
    assert "reset" not in captured_emails


def test_analyst_cannot_change_account_status(client, save_user):
    analyst = save_user(role=UserRole.ANALYST, account_status=AccountStatus.ACTIVE)
    _login_as(analyst)
    response = client.patch(
        f"/users/{analyst.user_id}", json={"account_status": "SUSPENDED"}
    )
    assert response.status_code == 403


def test_admin_suspends_an_analyst_but_not_themself(client, save_user):
    admin = save_user(role=UserRole.ADMIN, account_status=AccountStatus.ACTIVE)
    analyst = save_user(role=UserRole.ANALYST, account_status=AccountStatus.ACTIVE)
    _login_as(admin)
    suspended = client.patch(
        f"/users/{analyst.user_id}", json={"account_status": "SUSPENDED"}
    )
    assert suspended.json()["account_status"] == "SUSPENDED"
    assert (
        client.patch(
            f"/users/{admin.user_id}", json={"account_status": "SUSPENDED"}
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"/users/{analyst.user_id}", json={"account_status": "BANNED"}
        ).status_code
        == 422
    )


def test_admin_cannot_delete_themself(client, save_user):
    admin = save_user(role=UserRole.ADMIN, account_status=AccountStatus.ACTIVE)
    _login_as(admin)
    assert client.delete(f"/users/{admin.user_id}").status_code == 400
