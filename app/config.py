from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost:5432/elwasset"
    secret_key: str = "change-me"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    sendgrid_api_key: Optional[str] = None
    from_email: str = "noreply@elwasset-crm.com"
    disposable_domains_url: str = "https://raw.githubusercontent.com/disposable-email-domains/disposable-email-domains/master/disposable_email_blocklist.conf"
    admin_email: str = "gh221186@gmail.com"
    log_level: str = "INFO"
    environment: str = "development"
    otp_expire_minutes: int = 10
    max_registrations_per_ip: int = 3
    max_login_attempts: int = 5
    login_lockout_minutes: int = 15
    cors_origin: str = "http://localhost:8000"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_rate_limit: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
