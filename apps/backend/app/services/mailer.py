from typing import Optional
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


def send_email(to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASS:
        # In dev without SMTP, skip sending.
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())


def render_otp_email(otp: str, purpose: str) -> tuple[str, str]:
    subject = f"Your {purpose.replace('_', ' ').title()} code"
    text = f"Your OTP is {otp}. It will expire soon."
    html = f"""
    <html>
      <body>
        <p>Your OTP is <strong>{otp}</strong>.</p>
        <p>It will expire soon.</p>
      </body>
    </html>
    """
    return subject, html if html else text
