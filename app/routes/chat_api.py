from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.chat_message import ChatMessage
from app.services.gemini_service import gemini_service
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    # Save user message
    user_msg = ChatMessage(
        brokerage_id=current_user.brokerage_id,
        user_id=current_user.id,
        role="user",
        content=body.message.strip(),
        message_type="text",
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # Get recent history
    result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.brokerage_id == current_user.brokerage_id,
            ChatMessage.user_id == current_user.id,
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    history_messages = result.scalars().all()
    history = [
        {"role": "user" if m.role == "user" else "model", "content": m.content}
        for m in reversed(history_messages)
    ]

    # Get AI response
    ai_response = await gemini_service.chat(body.message.strip(), history=history)

    # Save AI response
    assistant_msg = ChatMessage(
        brokerage_id=current_user.brokerage_id,
        user_id=current_user.id,
        role="assistant",
        content=ai_response,
        message_type="text",
    )
    db.add(assistant_msg)
    await db.commit()

    await AuditService.log(
        db,
        current_user.brokerage_id,
        current_user.id,
        "chat",
        "chat_message",
        user_msg.id,
        ip_address="",
    )

    return ChatResponse(response=ai_response)


class ImageAnalysisRequest(BaseModel):
    prompt: str = "Describe this image"


@router.post("/chat/analyze-image")
async def analyze_image_endpoint(
    file: __import__("fastapi").UploadFile = __import__("fastapi").File(...),
    prompt: str = __import__("fastapi").Form("Describe this image"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file or not file.file:
        raise HTTPException(status_code=400, detail="No image provided")
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    ext = (file.filename or "").lower()
    if ext.endswith((".jpg", ".jpeg")):
        mime_type = "image/jpeg"
    elif ext.endswith(".png"):
        mime_type = "image/png"
    elif ext.endswith(".gif"):
        mime_type = "image/gif"
    elif ext.endswith(".webp"):
        mime_type = "image/webp"
    else:
        mime_type = "image/png"

    ai_response = await gemini_service.analyze_image(contents, mime_type, prompt)

    user_msg = ChatMessage(
        brokerage_id=current_user.brokerage_id,
        user_id=current_user.id,
        role="user",
        content=f"[Image analysis: {prompt}]",
        message_type="image",
    )
    db.add(user_msg)
    assistant_msg = ChatMessage(
        brokerage_id=current_user.brokerage_id,
        user_id=current_user.id,
        role="assistant",
        content=ai_response,
        message_type="image_analysis",
    )
    db.add(assistant_msg)
    await db.commit()

    return {"response": ai_response}
