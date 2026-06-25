from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.models.base import BaseModel


class Brokerage(BaseModel):
    __tablename__ = "brokerages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="brokerage", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="brokerage", cascade="all, delete-orphan")
    properties = relationship("Property", back_populates="brokerage", cascade="all, delete-orphan")
    deals = relationship("Deal", back_populates="brokerage", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="brokerage", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="brokerage", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="brokerage", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="brokerage", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="brokerage", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="brokerage", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Brokerage {self.id}: {self.name}>"
