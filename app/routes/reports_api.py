from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.contact import Contact
from app.models.property import Property
from app.models.deal import Deal
from app.models.task import Task
from app.models.event import Event
from app.models.user import User
from app.deps import get_current_user

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/dashboard")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bid = current_user.brokerage_id
    c = await db.execute(select(func.count()).select_from(select(Contact).where(Contact.brokerage_id == bid, Contact.is_active == True).subquery()))
    contacts_count = c.scalar()
    p = await db.execute(select(func.count()).select_from(select(Property).where(Property.brokerage_id == bid, Property.is_active == True).subquery()))
    props_count = p.scalar()
    d = await db.execute(select(func.count()).select_from(select(Deal).where(Deal.brokerage_id == bid, Deal.is_active == True, Deal.stage.in_(["lead", "qualified", "site_visit", "reservation", "contract", "handover"])).subquery()))
    deals_active = d.scalar()
    t = await db.execute(select(func.count()).select_from(select(Task).where(Task.brokerage_id == bid, Task.status == "pending").subquery()))
    tasks_pending = t.scalar()
    e = await db.execute(select(func.count()).select_from(select(Event).where(Event.brokerage_id == bid, Event.is_active == True).subquery()))
    events_count = e.scalar()
    return {
        "contacts_count": contacts_count or 0,
        "properties_count": props_count or 0,
        "active_deals_count": deals_active or 0,
        "pending_tasks_count": tasks_pending or 0,
        "events_count": events_count or 0,
    }


@router.get("/deals-summary")
async def deals_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bid = current_user.brokerage_id
    stages = ["lead", "qualified", "site_visit", "reservation", "contract", "handover", "closed", "lost", "dead"]
    result = {}
    for s in stages:
        c = await db.execute(select(func.count()).select_from(select(Deal).where(Deal.brokerage_id == bid, Deal.stage == s, Deal.is_active == True).subquery()))
        result[s] = c.scalar() or 0
    return {"stages": result}


@router.get("/contacts-summary")
async def contacts_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bid = current_user.brokerage_id
    types = ["buyer", "seller", "agent", "other"]
    result = {}
    for t in types:
        c = await db.execute(select(func.count()).select_from(select(Contact).where(Contact.brokerage_id == bid, Contact.contact_type == t, Contact.is_active == True).subquery()))
        result[t] = c.scalar() or 0
    return {"types": result}
