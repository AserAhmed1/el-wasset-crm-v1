import random
import string
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models.otp import OTP

logger = logging.getLogger(__name__)


async def send_otp_email(email: str, code: str, purpose: str = "registration"):
    """Send OTP code via email. Falls back to console logging."""
    subject = f"Your EL-Wasset OTP Code: {code}"
    body = f"""
Your EL-Wasset verification code is:

    {code}

This code expires in {settings.otp_expire_minutes} minutes.

If you did not request this code, please ignore this email.
"""

    if settings.sendgrid_api_key:
        from email.message import EmailMessage
        try:
            msg = EmailMessage()
            msg.set_content(body)
            msg["Subject"] = subject
            msg["From"] = settings.from_email
            msg["To"] = email
            await send_email_via_sendgrid(msg)
            logger.info(f"OTP email sent to {email}")
            return True
        except Exception as e:
            logger.warning(f"Failed to send OTP email: {e}")
    else:
        logger.info(f"OTP for {email}: {code} (email not sent — set SENDGRID_API_KEY in .env)")
    return False


async def send_email_via_sendgrid(msg):
    import aiosmtplib
    await aiosmtplib.send(
        msg,
        hostname="smtp.sendgrid.net",
        port=587,
        start_tls=True,
        username="apikey",
        password=settings.sendgrid_api_key,
        timeout=30,
    )


class OTPService:
    @staticmethod
    def generate_code() -> str:
        return "".join(random.choices(string.digits, k=6))

    @staticmethod
    async def create_otp(db: AsyncSession, email: str, purpose: str = "registration") -> OTP:
        code = OTPService.generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)
        otp = OTP(email=email, code=code, purpose=purpose, expires_at=expires_at)
        db.add(otp)
        await db.commit()
        await db.refresh(otp)
        # Try to send email (async, non-blocking)
        await send_otp_email(email, code, purpose)
        return otp

    @staticmethod
    async def verify_otp(db: AsyncSession, email: str, code: str, purpose: str = "registration") -> bool:
        result = await db.execute(
            select(OTP).where(
                OTP.email == email,
                OTP.code == code,
                OTP.purpose == purpose,
                OTP.is_used == False,
                OTP.expires_at > datetime.now(timezone.utc),
            ).order_by(OTP.created_at.desc()).limit(1)
        )
        otp = result.scalar_one_or_none()
        if not otp:
            return False
        otp.is_used = True
        await db.commit()
        return True

    @staticmethod
    async def clean_expired(db: AsyncSession):
        await db.execute(
            delete(OTP).where(OTP.expires_at <= datetime.now(timezone.utc))
        )
        await db.commit()
