from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models.task import Task
from app.models.user import User
from app.deps import get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "medium"
    task_type: str = "follow_up"
    contact_id: Optional[int] = None
    deal_id: Optional[int] = None
    assigned_to: Optional[int] = None
    is_conditional: bool = False
    condition_type: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    task_type: Optional[str] = None
    contact_id: Optional[int] = None
    deal_id: Optional[int] = None
    assigned_to: Optional[int] = None
    is_conditional: Optional[bool] = None
    condition_type: Optional[str] = None


def parse_dt(s: str | None):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


@router.get("")
async def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Task).where(Task.brokerage_id == current_user.brokerage_id)
    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
    if task_type:
        query = query.where(Task.task_type == task_type)
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    tasks = result.scalars().all()
    return {
        "items": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description or "",
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "status": t.status,
                "priority": t.priority,
                "task_type": t.task_type,
                "contact_id": t.contact_id,
                "deal_id": t.deal_id,
                "assigned_to": t.assigned_to,
                "is_conditional": t.is_conditional,
                "condition_type": t.condition_type,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total else 0,
    }


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.brokerage_id == current_user.brokerage_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description or "",
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "status": task.status,
        "priority": task.priority,
        "task_type": task.task_type,
        "contact_id": task.contact_id,
        "deal_id": task.deal_id,
        "assigned_to": task.assigned_to,
        "is_conditional": task.is_conditional,
        "condition_type": task.condition_type,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.post("", status_code=201)
async def create_task(
    body: TaskCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = Task(
        brokerage_id=current_user.brokerage_id,
        title=body.title,
        description=body.description,
        due_date=parse_dt(body.due_date),
        priority=body.priority,
        task_type=body.task_type,
        contact_id=body.contact_id,
        deal_id=body.deal_id,
        assigned_to=body.assigned_to or current_user.id,
        is_conditional=body.is_conditional,
        condition_type=body.condition_type,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    ip = request.client.host if request.client else "unknown"
    await AuditService.log(db, current_user.brokerage_id, current_user.id, "create", "task", task.id, ip_address=ip)
    return {"id": task.id, "title": task.title, "status": task.status, "priority": task.priority}


@router.put("/{task_id}")
async def update_task(
    task_id: int,
    body: TaskUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.brokerage_id == current_user.brokerage_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.due_date is not None:
        task.due_date = parse_dt(body.due_date)
    if body.status is not None:
        task.status = body.status
        if body.status == "completed":
            task.completed_at = datetime.now(timezone.utc)
        else:
            task.completed_at = None
    if body.priority is not None:
        task.priority = body.priority
    if body.task_type is not None:
        task.task_type = body.task_type
    if body.contact_id is not None:
        task.contact_id = body.contact_id
    if body.deal_id is not None:
        task.deal_id = body.deal_id
    if body.assigned_to is not None:
        task.assigned_to = body.assigned_to
    if body.is_conditional is not None:
        task.is_conditional = body.is_conditional
    if body.condition_type is not None:
        task.condition_type = body.condition_type
    await db.commit()
    await db.refresh(task)
    ip = request.client.host if request.client else "unknown"
    await AuditService.log(db, current_user.brokerage_id, current_user.id, "update", "task", task.id, ip_address=ip)
    return {"id": task.id, "title": task.title, "status": task.status}


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.brokerage_id == current_user.brokerage_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()
    ip = request.client.host if request.client else "unknown"
    await AuditService.log(db, current_user.brokerage_id, current_user.id, "delete", "task", task_id, ip_address=ip)
    return {"message": "Task deleted"}
