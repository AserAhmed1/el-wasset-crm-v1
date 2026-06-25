from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models.deal import Deal
from app.models.user import User
from app.deps import get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/deals", tags=["deals"])

DEAL_STAGES = ["lead", "qualified", "site_visit", "reservation", "contract", "handover", "closed", "lost", "dead"]
STAGE_LABELS = {
    "lead": "عميل محتمل",
    "qualified": "مؤهل",
    "site_visit": "معاينة",
    "reservation": "حجز",
    "contract": "عقد",
    "handover": "تسليم",
    "closed": "مُغلَق",
    "lost": "خاسر",
    "dead": "منتهي",
}


class DealCreate(BaseModel):
    title: str
    property_id: Optional[int] = None
    buyer_id: Optional[int] = None
    seller_id: Optional[int] = None
    agent_id: Optional[int] = None
    stage: str = "lead"
    commission_amount: Optional[float] = None
    commission_percentage: Optional[float] = None
    notes: Optional[str] = None


class DealUpdate(BaseModel):
    title: Optional[str] = None
    property_id: Optional[int] = None
    buyer_id: Optional[int] = None
    seller_id: Optional[int] = None
    agent_id: Optional[int] = None
    stage: Optional[str] = None
    commission_amount: Optional[float] = None
    commission_percentage: Optional[float] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_deals(
    search: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Deal).where(
        Deal.brokerage_id == current_user.brokerage_id,
        Deal.is_active == True,
    )
    if search:
        term = f"%{search}%"
        query = query.where(or_(Deal.title.ilike(term), Deal.notes.ilike(term)))
    if stage:
        query = query.where(Deal.stage == stage)
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Deal.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    deals = result.scalars().all()
    return {
        "items": [
            {
                "id": d.id,
                "title": d.title,
                "property_id": d.property_id,
                "buyer_id": d.buyer_id,
                "seller_id": d.seller_id,
                "agent_id": d.agent_id,
                "stage": d.stage,
                "stage_label": STAGE_LABELS.get(d.stage, d.stage),
                "commission_amount": d.commission_amount,
                "commission_percentage": d.commission_percentage,
                "notes": d.notes or "",
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "closed_at": d.closed_at.isoformat() if d.closed_at else None,
            }
            for d in deals
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total else 0,
    }


@router.get("/pipeline")
async def get_pipeline(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal).where(
            Deal.brokerage_id == current_user.brokerage_id,
            Deal.is_active == True,
            Deal.stage.in_(["lead", "qualified", "site_visit", "reservation", "contract", "handover"]),
        ).order_by(Deal.updated_at.desc())
    )
    deals = result.scalars().all()
    pipeline = {s: [] for s in ["lead", "qualified", "site_visit", "reservation", "contract", "handover"]}
    for d in deals:
        if d.stage in pipeline:
            pipeline[d.stage].append({
                "id": d.id,
                "title": d.title,
                "stage_label": STAGE_LABELS.get(d.stage, d.stage),
                "commission_amount": d.commission_amount,
                "notes": d.notes or "",
                "created_at": d.created_at.isoformat() if d.created_at else None,
            })
    return {
        "stages": [
            {"key": s, "label": STAGE_LABELS[s], "deals": pipeline[s]}
            for s in ["lead", "qualified", "site_visit", "reservation", "contract", "handover"]
        ]
    }


@router.get("/{deal_id}")
async def get_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal).where(Deal.id == deal_id, Deal.brokerage_id == current_user.brokerage_id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return {
        "id": deal.id,
        "title": deal.title,
        "property_id": deal.property_id,
        "buyer_id": deal.buyer_id,
        "seller_id": deal.seller_id,
        "agent_id": deal.agent_id,
        "stage": deal.stage,
        "stage_label": STAGE_LABELS.get(deal.stage, deal.stage),
        "commission_amount": deal.commission_amount,
        "commission_percentage": deal.commission_percentage,
        "notes": deal.notes or "",
        "created_at": deal.created_at.isoformat() if deal.created_at else None,
        "closed_at": deal.closed_at.isoformat() if deal.closed_at else None,
    }


@router.post("", status_code=201)
async def create_deal(
    body: DealCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.stage not in DEAL_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {', '.join(DEAL_STAGES)}")
    deal = Deal(
        brokerage_id=current_user.brokerage_id,
        title=body.title,
        property_id=body.property_id,
        buyer_id=body.buyer_id,
        seller_id=body.seller_id,
        agent_id=body.agent_id,
        stage=body.stage,
        commission_amount=body.commission_amount,
        commission_percentage=body.commission_percentage,
        notes=body.notes,
    )
    db.add(deal)
    await db.commit()
    await db.refresh(deal)
    ip = request.client.host if request.client else "unknown"
    await AuditService.log(db, current_user.brokerage_id, current_user.id, "create", "deal", deal.id, ip_address=ip)
    return {
        "id": deal.id,
        "title": deal.title,
        "stage": deal.stage,
        "stage_label": STAGE_LABELS.get(deal.stage),
    }


@router.put("/{deal_id}")
async def update_deal(
    deal_id: int,
    body: DealUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal).where(Deal.id == deal_id, Deal.brokerage_id == current_user.brokerage_id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    old_stage = deal.stage
    if body.stage is not None:
        if body.stage not in DEAL_STAGES:
            raise HTTPException(status_code=400, detail=f"Invalid stage")
        deal.stage = body.stage
        if body.stage in ("closed", "lost", "dead"):
            deal.closed_at = datetime.now(timezone.utc)
    if body.title is not None:
        deal.title = body.title
    if body.property_id is not None:
        deal.property_id = body.property_id
    if body.buyer_id is not None:
        deal.buyer_id = body.buyer_id
    if body.seller_id is not None:
        deal.seller_id = body.seller_id
    if body.agent_id is not None:
        deal.agent_id = body.agent_id
    if body.commission_amount is not None:
        deal.commission_amount = body.commission_amount
    if body.commission_percentage is not None:
        deal.commission_percentage = body.commission_percentage
    if body.notes is not None:
        deal.notes = body.notes
    if body.is_active is not None:
        deal.is_active = body.is_active
    await db.commit()
    await db.refresh(deal)
    ip = request.client.host if request.client else "unknown"
    await AuditService.log(db, current_user.brokerage_id, current_user.id, "update", "deal", deal.id,
                           old_value={"stage": old_stage}, new_value={"stage": deal.stage}, ip_address=ip)
    return {"id": deal.id, "title": deal.title, "stage": deal.stage, "stage_label": STAGE_LABELS.get(deal.stage)}


@router.delete("/{deal_id}")
async def delete_deal(
    deal_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal).where(Deal.id == deal_id, Deal.brokerage_id == current_user.brokerage_id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    deal.is_active = False
    await db.commit()
    ip = request.client.host if request.client else "unknown"
    await AuditService.log(db, current_user.brokerage_id, current_user.id, "delete", "deal", deal_id, ip_address=ip)
    return {"message": "Deal deleted"}
