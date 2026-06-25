from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.contact import Contact
from app.models.user import User
from app.deps import get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


class ContactCreate(BaseModel):
    name: str
    phones: Optional[list[str]] = None
    email: Optional[str] = None
    contact_type: str = "buyer"
    notes: Optional[str] = None
    source: Optional[str] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    phones: Optional[list[str]] = None
    email: Optional[str] = None
    contact_type: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_contacts(
    request: Request,
    search: Optional[str] = Query(None),
    contact_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Contact).where(
        Contact.brokerage_id == current_user.brokerage_id,
        Contact.is_active == True,
    )
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Contact.name.ilike(search_term),
                Contact.phones.cast(str).ilike(search_term),
                Contact.email.ilike(search_term),
                Contact.notes.ilike(search_term),
            )
        )
    if contact_type:
        query = query.where(Contact.contact_type == contact_type)
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Contact.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    contacts = result.scalars().all()
    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "phones": c.phones or [],
                "email": c.email or "",
                "contact_type": c.contact_type,
                "notes": c.notes or "",
                "source": c.source or "",
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in contacts
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total else 0,
    }


@router.get("/{contact_id}")
async def get_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.brokerage_id == current_user.brokerage_id,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {
        "id": contact.id,
        "name": contact.name,
        "phones": contact.phones or [],
        "email": contact.email or "",
        "contact_type": contact.contact_type,
        "notes": contact.notes or "",
        "source": contact.source or "",
        "activity_log": contact.activity_log or [],
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
        "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
    }


@router.post("", status_code=201)
async def create_contact(
    body: ContactCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = Contact(
        brokerage_id=current_user.brokerage_id,
        name=body.name,
        phones=body.phones or [],
        email=body.email,
        contact_type=body.contact_type,
        notes=body.notes,
        source=body.source,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    ip = request.client.host if request.client else "unknown"
    await AuditService.log(db, current_user.brokerage_id, current_user.id, "create", "contact", contact.id, ip_address=ip)
    return {
        "id": contact.id,
        "name": contact.name,
        "phones": contact.phones or [],
        "email": contact.email or "",
        "contact_type": contact.contact_type,
        "notes": contact.notes or "",
        "source": contact.source or "",
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
    }


@router.put("/{contact_id}")
async def update_contact(
    contact_id: int,
    body: ContactUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.brokerage_id == current_user.brokerage_id,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    old_data = {"name": contact.name, "phones": contact.phones, "email": contact.email, "contact_type": contact.contact_type}
    if body.name is not None:
        contact.name = body.name
    if body.phones is not None:
        contact.phones = body.phones
    if body.email is not None:
        contact.email = body.email
    if body.contact_type is not None:
        contact.contact_type = body.contact_type
    if body.notes is not None:
        contact.notes = body.notes
    if body.source is not None:
        contact.source = body.source
    if body.is_active is not None:
        contact.is_active = body.is_active
    await db.commit()
    await db.refresh(contact)
    ip = request.client.host if request.client else "unknown"
    new_data = {"name": contact.name, "phones": contact.phones, "email": contact.email, "contact_type": contact.contact_type}
    await AuditService.log(db, current_user.brokerage_id, current_user.id, "update", "contact", contact.id, old_value=old_data, new_value=new_data, ip_address=ip)
    return {
        "id": contact.id,
        "name": contact.name,
        "phones": contact.phones or [],
        "email": contact.email or "",
        "contact_type": contact.contact_type,
        "notes": contact.notes or "",
        "source": contact.source or "",
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
    }


@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.brokerage_id == current_user.brokerage_id,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    contact.is_active = False
    await db.commit()
    ip = request.client.host if request.client else "unknown"
    await AuditService.log(db, current_user.brokerage_id, current_user.id, "delete", "contact", contact_id, ip_address=ip)
    return {"message": "Contact deleted"}
