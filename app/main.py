from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_db
from app.routes import (auth_router, dev_router, pages_router, contacts_api_router,
                         properties_api_router, deals_api_router, tasks_api_router,
                         i18n_api_router, calendar_api_router, documents_api_router,
                         reports_api_router, chat_api_router, settings_api_router)
from app.services.hermes_service import hermes_service


import os
from pathlib import Path

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    (static_dir / "css").mkdir(exist_ok=True)
    (static_dir / "js").mkdir(exist_ok=True)
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(exist_ok=True)
    uploads_dir = Path(__file__).parent / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    icons_dir = static_dir / "icons"
    icons_dir.mkdir(exist_ok=True)
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="EL-Wasset CRM",
    description="Arabic real estate broker CRM system",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dev_router)
app.include_router(pages_router)
app.include_router(contacts_api_router)
app.include_router(properties_api_router)
app.include_router(deals_api_router)
app.include_router(tasks_api_router)
app.include_router(i18n_api_router)
app.include_router(calendar_api_router)
app.include_router(documents_api_router)
app.include_router(reports_api_router)
app.include_router(chat_api_router)
app.include_router(settings_api_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    try:
        await hermes_service.capture_error(
            db=None,
            message=f"{type(exc).__name__}: {str(exc)[:500]}",
            level="critical",
            route=str(request.url),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception:
        pass
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error" if settings.environment == "production" else str(exc)},
    )
