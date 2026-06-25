from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_current_user, get_admin_user
from app.database import get_db
from app.models.user import User
from app.models.log import Log
from app.models.audit_log import AuditLog
from app.services.hermes_service import hermes_service
from app.services.discovery_service import discovery_service
from app.services.gemini_service import gemini_service
from sqlalchemy import select

router = APIRouter(prefix="/api/dev", tags=["dev"])


class FixAction(BaseModel):
    fix_id: int
    action: str  # approve or reject


@router.get("/logs")
async def get_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Log).order_by(Log.created_at.desc()).limit(50)
    )
    logs = result.scalars().all()
    return {
        "logs": [
            {
                "id": l.id,
                "level": l.level,
                "message": l.message,
                "route": l.route,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]
    }


@router.get("/audit-logs")
async def get_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50)
    )
    logs = result.scalars().all()
    return {
        "audit_logs": [
            {
                "id": a.id,
                "action": a.action,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in logs
        ]
    }


@router.get("/hermes")
async def hermes_panel(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recent_errors = await hermes_service.get_recent_errors(db, hours=24)
    pending_fixes = hermes_service.get_pending_fixes()
    approved_fixes = hermes_service.get_approved_fixes()
    return {
        "status": "active",
        "recent_errors": [
            {"id": e.id, "level": e.level, "message": e.message[:200], "route": e.route, "created_at": e.created_at.isoformat() if e.created_at else None}
            for e in recent_errors[:20]
        ],
        "pending_fixes": pending_fixes,
        "approved_fixes": approved_fixes,
        "admin_email": "gh221186@gmail.com",
    }


@router.post("/hermes/fix")
async def hermes_fix_action(
    body: FixAction,
    current_user: User = Depends(get_current_user),
):
    if body.action == "approve":
        if hermes_service.approve_fix(body.fix_id):
            return {"status": "approved", "fix_id": body.fix_id}
    elif body.action == "reject":
        if hermes_service.reject_fix(body.fix_id):
            return {"status": "rejected", "fix_id": body.fix_id}
    raise HTTPException(status_code=404, detail="Fix not found or already processed")


@router.get("/discovery")
async def discovery_panel(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis = await discovery_service.analyze_chat_patterns(db, current_user.brokerage_id)
    return {
        "status": "active",
        "analysis": analysis,
        "last_report": discovery_service.last_report_date.isoformat() if discovery_service.last_report_date else None,
    }


@router.post("/discovery/analyze")
async def discovery_analyze(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = await discovery_service.generate_weekly_report(db, current_user.brokerage_id)
    return {"status": "report_generated", "report": report}


class CoderRequest(BaseModel):
    question: str


@router.post("/coder")
async def coder_endpoint(
    body: CoderRequest,
    current_user: User = Depends(get_current_user),
):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    prompt = f"Answer this technical question concisely in English. The app is EL-Wasset CRM built with Python FastAPI, SQLAlchemy, Jinja2, JavaScript:\n\n{body.question}"
    response = await gemini_service.chat(prompt)
    return {"response": response}
