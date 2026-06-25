import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.log import Log
from app.models.audit_log import AuditLog
from app.config import settings
from app.services.gemini_service import gemini_service

logger = logging.getLogger("hermes")


class HermesService:
    def __init__(self):
        self.pending_fixes = []  # {id, error, suggestion, proposed_fix, approved}

    async def capture_error(
        self,
        db: AsyncSession | None,
        message: str,
        level: str = "error",
        route: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Log | None:
        if db:
            log_entry = Log(
                brokerage_id=None,
                user_id=None,
                level=level,
                message=message,
                route=route,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.add(log_entry)
            await db.commit()
            await db.refresh(log_entry)

        if level in ("error", "critical"):
            logger.error(f"Hermes captured {level}: {message}")
            await self._notify_admin(message, level)
            # Auto-suggest fix via Gemini
            fix_suggestion = await gemini_service.chat(
                f"An error occurred in the EL-Wasset CRM app:\n{message}\n\nSuggest a fix in 2-3 sentences."
            )
            if fix_suggestion and not fix_suggestion.startswith("⚠️"):
                await self.suggest_fix(message, fix_suggestion, "")

        return log_entry if db else None

    async def _notify_admin(self, message: str, level: str):
        """Send email alert to admin. Falls back to console logging."""
        subject = f"[Hermes] {level.upper()} - EL-Wasset CRM"
        body = f"Time: {datetime.utcnow()}\nLevel: {level}\nMessage: {message}\n\nThis is an automated alert from Hermes."

        if settings.sendgrid_api_key:
            try:
                # SendGrid email sending via aiosmtplib
                import smtplib
                from email.message import EmailMessage

                msg = EmailMessage()
                msg.set_content(body)
                msg["Subject"] = subject
                msg["From"] = settings.from_email
                msg["To"] = settings.admin_email

                # SendGrid SMTP
                with smtplib.SMTP("smtp.sendgrid.net", 587, timeout=30) as server:
                    server.starttls()
                    server.login("apikey", settings.sendgrid_api_key)
                    server.send_message(msg)
                logger.info(f"Hermes email alert sent to {settings.admin_email}")
            except Exception as e:
                logger.warning(f"Hermes email failed: {e}")
        else:
            logger.info(f"Hermes alert [{level}]: {message}")

    async def suggest_fix(self, error_msg: str, suggestion: str, proposed_code: str) -> dict:
        fix_id = len(self.pending_fixes) + 1
        fix = {
            "id": fix_id,
            "error": error_msg,
            "suggestion": suggestion,
            "proposed_fix": proposed_code,
            "approved": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        self.pending_fixes.append(fix)
        logger.info(f"Hermes suggests fix #{fix_id}: {suggestion}")
        return fix

    def approve_fix(self, fix_id: int) -> bool:
        for fix in self.pending_fixes:
            if fix["id"] == fix_id and fix["approved"] is None:
                fix["approved"] = True
                return True
        return False

    def reject_fix(self, fix_id: int) -> bool:
        for fix in self.pending_fixes:
            if fix["id"] == fix_id and fix["approved"] is None:
                fix["approved"] = False
                return True
        return False

    async def get_recent_errors(self, db: AsyncSession, hours: int = 24) -> list[Log]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        result = await db.execute(
            select(Log).where(
                Log.level.in_(["error", "critical"]),
                Log.created_at >= cutoff,
            ).order_by(Log.created_at.desc()).limit(50)
        )
        return result.scalars().all()

    def get_pending_fixes(self) -> list[dict]:
        return [f for f in self.pending_fixes if f["approved"] is None]

    def get_approved_fixes(self) -> list[dict]:
        return [f for f in self.pending_fixes if f["approved"] is True]


hermes_service = HermesService()
