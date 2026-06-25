from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.models.event import Event
from app.models.user import User
from app.deps import get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

EVENT_TYPES = {"showing": "معاينة", "open_house": "يوم مفتوح", "meeting": "اجتماع", "closing": "إغلاق", "site_visit": "زيارة موقع"}


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    event_type: str = "showing"
    deal_id: Optional[int] = None
    contact_id: Optional[int] = None
    location: Optional[str] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    event_type: Optional[str] = None
    deal_id: Optional[int] = None
    contact_id: Optional[int] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


def parse_dt(s: str | None):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except:
        return None


@router.get("")
async def list_events(
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    event_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Event).where(Event.brokerage_id == current_user.brokerage_id, Event.is_active == True)
    if event_type:
        query = query.where(Event.event_type == event_type)
    now = datetime.now(timezone.utc)
    m = month or now.month
    y = year or now.year
    start = datetime(y, m, 1, tzinfo=timezone.utc)
    if m == 12:
        end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(y, m + 1, 1, tzinfo=timezone.utc)
    query = query.where(Event.start_time >= start, Event.start_time < end)
    query = query.order_by(Event.start_time.asc())
    result = await db.execute(query)
    events = result.scalars().all()
    return {
        "items": [
            {
                "id": e.id,
                "title": e.title,
                "description": e.description or "",
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat() if e.end_time else None,
                "event_type": e.event_type,
                "event_type_label": EVENT_TYPES.get(e.event_type, e.event_type),
                "deal_id": e.deal_id,
                "contact_id": e.contact_id,
                "location": e.location or "",
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
        "month": m,
        "year": y,
    }


@router.post("", status_code=201)
async def create_event(
    body: EventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = Event(
        brokerage_id=current_user.brokerage_id,
        title=body.title,
        description=body.description,
        start_time=parse_dt(body.start_time) or datetime.now(timezone.utc),
        end_time=parse_dt(body.end_time),
        event_type=body.event_type,
        deal_id=body.deal_id,
        contact_id=body.contact_id,
        location=body.location,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {"id": event.id, "title": event.title, "event_type": event.event_type}


@router.put("/{event_id}")
async def update_event(
    event_id: int,
    body: EventUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Event).where(Event.id == event_id, Event.brokerage_id == current_user.brokerage_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if body.title is not None: event.title = body.title
    if body.description is not None: event.description = body.description
    if body.start_time is not None: event.start_time = parse_dt(body.start_time)
    if body.end_time is not None: event.end_time = parse_dt(body.end_time)
    if body.event_type is not None: event.event_type = body.event_type
    if body.deal_id is not None: event.deal_id = body.deal_id
    if body.contact_id is not None: event.contact_id = body.contact_id
    if body.location is not None: event.location = body.location
    if body.is_active is not None: event.is_active = body.is_active
    await db.commit()
    return {"id": event.id, "title": event.title}


@router.delete("/{event_id}")
async def delete_event(
    event_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Event).where(Event.id == event_id, Event.brokerage_id == current_user.brokerage_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.is_active = False
    await db.commit()
    return {"message": "Event deleted"}
