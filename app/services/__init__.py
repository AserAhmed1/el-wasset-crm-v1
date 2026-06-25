from app.services.disposable_email import DisposableEmailChecker
from app.services.otp_service import OTPService
from app.services.auth_service import AuthService
from app.services.rate_limiter import RateLimiter
from app.services.audit_service import AuditService

disposable_checker = DisposableEmailChecker()
otp_service = OTPService()
auth_service = AuthService()
rate_limiter = RateLimiter()
audit_service = AuditService()

__all__ = [
    "disposable_checker",
    "otp_service",
    "auth_service",
    "rate_limiter",
    "audit_service",
]
