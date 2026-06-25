from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, field_validator
import re
from app.database import get_db
from app.config import settings
from app.services import disposable_checker, otp_service, auth_service, rate_limiter, audit_service
from app.models.brokerage import Brokerage
from app.models.user import User
from app.deps import get_current_user, get_admin_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    email: str
    phone: str = ""
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class VerifyOTPRequest(BaseModel):
    email: str
    code: str


@router.post("/register")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"

    if not rate_limiter.check_registration(ip):
        raise HTTPException(status_code=429, detail="Too many registrations from this IP")

    email = body.email.strip().lower()
    existing_user = await auth_service.get_user_by_email(db, email)
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    existing_brokerage = await auth_service.get_brokerage_by_email(db, email)
    if existing_brokerage:
        raise HTTPException(status_code=409, detail="Email already registered")

    await disposable_checker.load_blocklist()
    if disposable_checker.is_disposable(email):
        raise HTTPException(status_code=403, detail="Disposable email addresses are not allowed. Please use a real email.")

    brokerage = Brokerage(name=body.name, email=email, phone=body.phone, is_verified=False)
    db.add(brokerage)
    await db.commit()
    await db.refresh(brokerage)

    password_hash = auth_service.hash_password(body.password)
    user = User(
        brokerage_id=brokerage.id,
        name=body.name,
        email=email,
        password_hash=password_hash,
        role="admin",
        is_admin=True,
    )
    db.add(user)
    await db.commit()

    otp = await otp_service.create_otp(db, email, "registration")
    rate_limiter.record_registration(ip)

    if settings.environment == "development":
        # Auto-verify in dev mode and return tokens directly
        valid = await otp_service.verify_otp(db, email, otp.code, "registration")
        if valid:
            brokerage.is_verified = True
            await db.commit()
            access_token = auth_service.create_access_token({"sub": str(user.id), "brokerage_id": str(brokerage.id)})
            refresh_token = auth_service.create_refresh_token({"sub": str(user.id), "brokerage_id": str(brokerage.id)})
            return {"message": "Registration successful", "dev_otp": otp.code, "access_token": access_token, "refresh_token": refresh_token, "brokerage_id": brokerage.id, "user_id": user.id}

    resp = {"message": "Registration successful. Check your email for OTP.", "brokerage_id": brokerage.id, "user_id": user.id}
    if settings.environment == "development":
        resp["dev_otp"] = otp.code
    return resp


@router.post("/verify-otp")
async def verify_otp(body: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    valid = await otp_service.verify_otp(db, email, body.code, "registration")
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    result = await db.execute(
        __import__("sqlalchemy").select(Brokerage).where(Brokerage.email == email)
    )
    brokerage = result.scalar_one_or_none()
    if not brokerage:
        raise HTTPException(status_code=404, detail="Brokerage not found")

    brokerage.is_verified = True
    await db.commit()

    user_result = await db.execute(
        __import__("sqlalchemy").select(User).where(User.email == email)
    )
    user = user_result.scalar_one_or_none()

    access_token = auth_service.create_access_token({"sub": str(user.id), "brokerage_id": str(brokerage.id)})
    refresh_token = auth_service.create_refresh_token({"sub": str(user.id), "brokerage_id": str(brokerage.id)})

    return {"message": "Email verified successfully", "access_token": access_token, "refresh_token": refresh_token}


class RequestOTPRequest(BaseModel):
    email: str


@router.post("/request-otp")
async def request_otp(body: RequestOTPRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    otp = await otp_service.create_otp(db, email, "registration")
    return {"message": "OTP sent to your email", "expires_in_minutes": settings.otp_expire_minutes}


@router.post("/login")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()

    allowed, remaining = rate_limiter.check_login(email)
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    user = await auth_service.authenticate(db, email, body.password)
    if not user:
        rate_limiter.record_login_attempt(email, False)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    rate_limiter.record_login_attempt(email, True)

    result = await db.execute(
        __import__("sqlalchemy").select(Brokerage).where(Brokerage.id == user.brokerage_id)
    )
    brokerage = result.scalar_one_or_none()
    if not brokerage or not brokerage.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Check your OTP.")

    if not brokerage.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    access_token = auth_service.create_access_token({"sub": str(user.id), "brokerage_id": str(brokerage.id)})
    refresh_token = auth_service.create_refresh_token({"sub": str(user.id), "brokerage_id": str(brokerage.id)})

    ip = request.client.host if request.client else "unknown"
    await audit_service.log(db, brokerage.id, user.id, "login", "user", user.id, ip_address=ip)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh")
async def refresh_token(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        body = await request.json()
        token = body.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token required")

    payload = auth_service.decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        __import__("sqlalchemy").select(User).where(User.id == int(user_id), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = auth_service.create_access_token({"sub": str(user.id), "brokerage_id": str(payload.get("brokerage_id"))})
    return {"access_token": access_token}


@router.post("/logout")
async def logout():
    resp = JSONResponse({"message": "Logged out"})
    resp.delete_cookie("access_token")
    resp.delete_cookie("refresh_token")
    return resp


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "is_admin": current_user.is_admin,
        "brokerage_id": current_user.brokerage_id,
    }
