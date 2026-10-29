import os
import smtplib
from email.message import EmailMessage


def send_otp_email(to_email: str, code: str) -> None:
    _send(
        to_email,
        "TerraWatch login code",
        f"Your TerraWatch login code is: {code}\nIt expires in 5 minutes.",
        f"[OTP for {to_email}]: {code}",
    )


def send_password_reset_email(to_email: str, token: str) -> None:
    _send(
        to_email,
        "TerraWatch password reset",
        "Use this reset code to set a new TerraWatch password:\n\n"
        f"{token}\n\nIt expires in 1 hour. If you did not ask for this, ignore "
        "this email.",
        f"[RESET TOKEN for {to_email}]: {token}",
    )


def _send(to_email: str, subject: str, body: str, local_message: str) -> None:
    host = os.getenv("EMAIL_HOST", "")
    port = int(os.getenv("EMAIL_PORT", "587"))
    user = os.getenv("EMAIL_USERNAME", "")
    password = os.getenv("EMAIL_PASSWORD", "")
    sender = os.getenv("EMAIL_FROM", "")
    use_tls = os.getenv("EMAIL_USE_TLS", "true").lower() in ("1", "true", "yes")

    if not host or not user or not password or not sender:
        print(local_message)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(host, port) as server:
        if use_tls:
            server.starttls()
        if user:
            server.login(user, password)
        server.send_message(msg)
