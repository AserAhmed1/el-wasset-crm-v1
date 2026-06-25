from fastapi import APIRouter, Depends, HTTPException, Request, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
import aiofiles
import os
from pathlib import Path
from datetime import datetime, timezone
from app.database import get_db
from app.models.document import Document
from app.models.user import User
from app.deps import get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/documents", tags=["documents"])
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"


@router.get("")
async def list_documents(
    file_type: Optional[str] = Query(None),
    deal_id: Optional[int] = Query(None),
    contact_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Document).where(Document.brokerage_id == current_user.brokerage_id, Document.is_active == True)
    if file_type: query = query.where(Document.file_type == file_type)
    if deal_id: query = query.where(Document.deal_id == deal_id)
    if contact_id: query = query.where(Document.contact_id == contact_id)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(Document.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    docs = result.scalars().all()
    return {
        "items": [
            {
                "id": d.id,
                "title": d.title,
                "filename": d.filename,
                "file_type": d.file_type or "",
                "file_size": d.file_size,
                "deal_id": d.deal_id,
                "contact_id": d.contact_id,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ],
        "total": total,
    }


@router.post("/upload", status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(""),
    file_type: str = Form("other"),
    deal_id: Optional[int] = Form(None),
    contact_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    UPLOAD_DIR.mkdir(exist_ok=True)
    safe_name = f"{datetime.now(timezone.utc).timestamp()}_{file.filename}"
    filepath = UPLOAD_DIR / safe_name
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)
    doc = Document(
        brokerage_id=current_user.brokerage_id,
        title=title or file.filename or "Untitled",
        filename=file.filename or safe_name,
        filepath=str(filepath),
        file_type=file_type,
        mime_type=file.content_type,
        file_size=len(content),
        deal_id=deal_id,
        contact_id=contact_id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return {"id": doc.id, "title": doc.title, "filename": doc.filename}


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.brokerage_id == current_user.brokerage_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    filepath = Path(doc.filepath)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(path=str(filepath), filename=doc.filename, media_type=doc.mime_type or "application/octet-stream")


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.brokerage_id == current_user.brokerage_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.is_active = False
    await db.commit()
    filepath = Path(doc.filepath)
    if filepath.exists():
        filepath.unlink()
    return {"message": "Document deleted"}
