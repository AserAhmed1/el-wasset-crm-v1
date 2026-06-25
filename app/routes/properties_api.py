from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.property import Property
from app.models.user import User
from app.deps import get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/properties", tags=["properties"])


class PropertyCreate(BaseModel):
    title: str
    address: Optional[str] = None
    price: float
    status: str = "available"
    property_type: str = "apartment"
    bedrooms: int = 0
    bathrooms: int = 0
    area: Optional[float] = None
    description: Optional[str] = None
    images: Optional[list[str]] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    project_name: Optional[str] = None
    developer_name: Optional[str] = None
    installment_plan: Optional[str] = None


class PropertyUpdate(BaseModel):
    title: Optional[str] = None
    address: Optional[str] = None
    price: Optional[float] = None
    status: Optional[str] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area: Optional[float] = None
    description: Optional[str] = None
    images: Optional[list[str]] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    project_name: Optional[str] = None
    developer_name: Optional[str] = None
    installment_plan: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_properties(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_area: Optional[float] = Query(None),
    max_area: Optional[float] = Query(None),
    bedrooms: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Property).where(
        Property.brokerage_id == current_user.brokerage_id,
        Property.is_active == True,
    )
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Property.title.ilike(search_term),
                Property.address.ilike(search_term),
                Property.project_name.ilike(search_term),
                Property.developer_name.ilike(search_term),
                Property.description.ilike(search_term),
            )
        )
    if status:
        query = query.where(Property.status == status)
    if property_type:
        query = query.where(Property.property_type == property_type)
    if min_price is not None:
        query = query.where(Property.price >= min_price)
    if max_price is not None:
        query = query.where(Property.price <= max_price)
    if min_area is not None:
        query = query.where(Property.area >= min_area)
    if max_area is not None:
        query = query.where(Property.area <= max_area)
    if bedrooms is not None:
        query = query.where(Property.bedrooms == bedrooms)
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Property.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    properties = result.scalars().all()
    return {
        "items": [
            {
                "id": p.id,
                "title": p.title,
                "address": p.address or "",
                "price": p.price,
                "status": p.status,
                "property_type": p.property_type,
                "bedrooms": p.bedrooms,
                "bathrooms": p.bathrooms,
                "area": p.area,
                "images": p.images or [],
                "lat": p.lat,
                "lng": p.lng,
                "project_name": p.project_name or "",
                "developer_name": p.developer_name or "",
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in properties
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total else 0,
    }


@router.get("/{property_id}")
async def get_property(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.brokerage_id == current_user.brokerage_id,
        )
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return {
        "id": prop.id,
        "title": prop.title,
        "address": prop.address or "",
        "price": prop.price,
        "status": prop.status,
        "property_type": prop.property_type,
        "bedrooms": prop.bedrooms,
        "bathrooms": prop.bathrooms,
        "area": prop.area,
        "description": prop.description or "",
        "images": prop.images or [],
        "lat": prop.lat,
        "lng": prop.lng,
        "project_name": prop.project_name or "",
        "developer_name": prop.developer_name or "",
        "installment_plan": prop.installment_plan or "",
        "created_at": prop.created_at.isoformat() if prop.created_at else None,
        "updated_at": prop.updated_at.isoformat() if prop.updated_at else None,
    }


@router.post("", status_code=201)
async def create_property(
    body: PropertyCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prop = Property(
        brokerage_id=current_user.brokerage_id,
        title=body.title,
        address=body.address,
        price=body.price,
        status=body.status,
        property_type=body.property_type,
        bedrooms=body.bedrooms,
        bathrooms=body.bathrooms,
        area=body.area,
        description=body.description,
        images=body.images or [],
        lat=body.lat,
        lng=body.lng,
        project_name=body.project_name,
        developer_name=body.developer_name,
        installment_plan=body.installment_plan,
    )
    db.add(prop)
    await db.commit()
    await db.refresh(prop)
    ip = request.client.host if request.client else "unknown"
    await AuditService.log(db, current_user.brokerage_id, current_user.id, "create", "property", prop.id, ip_address=ip)
    return {
        "id": prop.id,
        "title": prop.title,
        "price": prop.price,
        "status": prop.status,
        "property_type": prop.property_type,
        "created_at": prop.created_at.isoformat() if prop.created_at else None,
    }


@router.put("/{property_id}")
async def update_property(
    property_id: int,
    body: PropertyUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.brokerage_id == current_user.brokerage_id,
        )
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    old_data = {"title": prop.title, "price": prop.price, "status": prop.status}
    if body.title is not None:
        prop.title = body.title
    if body.address is not None:
        prop.address = body.address
    if body.price is not None:
        prop.price = body.price
    if body.status is not None:
        prop.status = body.status
    if body.property_type is not None:
        prop.property_type = body.property_type
    if body.bedrooms is not None:
        prop.bedrooms = body.bedrooms
    if body.bathrooms is not None:
        prop.bathrooms = body.bathrooms
    if body.area is not None:
        prop.area = body.area
    if body.description is not None:
        prop.description = body.description
    if body.images is not None:
        prop.images = body.images
    if body.lat is not None:
        prop.lat = body.lat
    if body.lng is not None:
        prop.lng = body.lng
    if body.project_name is not None:
        prop.project_name = body.project_name
    if body.developer_name is not None:
        prop.developer_name = body.developer_name
    if body.installment_plan is not None:
        prop.installment_plan = body.installment_plan
    if body.is_active is not None:
        prop.is_active = body.is_active
    await db.commit()
    await db.refresh(prop)
    ip = request.client.host if request.client else "unknown"
    new_data = {"title": prop.title, "price": prop.price, "status": prop.status}
    await AuditService.log(db, current_user.brokerage_id, current_user.id, "update", "property", prop.id, old_value=old_data, new_value=new_data, ip_address=ip)
    return {
        "id": prop.id,
        "title": prop.title,
        "price": prop.price,
        "status": prop.status,
        "property_type": prop.property_type,
    }


@router.delete("/{property_id}")
async def delete_property(
    property_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.brokerage_id == current_user.brokerage_id,
        )
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    prop.is_active = False
    await db.commit()
    ip = request.client.host if request.client else "unknown"
    await AuditService.log(db, current_user.brokerage_id, current_user.id, "delete", "property", property_id, ip_address=ip)
    return {"message": "Property deleted"}
