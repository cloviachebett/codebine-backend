import os
import smtplib
from email.message import EmailMessage


def send_otp_email(to_email: str, code: str) -> None:
    host = os.getenv("EMAIL_HOST", "")
    port = int(os.getenv("EMAIL_PORT", "587"))
    user = os.getenv("EMAIL_USERNAME", "")
    password = os.getenv("EMAIL_PASSWORD", "")
    sender = os.getenv("EMAIL_FROM", "")
    use_tls = os.getenv("EMAIL_USE_TLS", "true").lower() in ("1", "true", "yes")

    if not host or not user or not password or not sender:
        print(f"[OTP for {to_email}]: {code}")
        return

    msg = EmailMessage()
    msg["Subject"] = "TerraWatch login code"
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(f"Your TerraWatch login code is: {code}\nIt expires in 5 minutes.")

    with smtplib.SMTP(host, port) as server:
        if use_tls:
            server.starttls()
        if user:
            server.login(user, password)
        server.send_message(msg)
