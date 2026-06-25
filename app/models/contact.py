from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON
from datetime import datetime
from app.models.base import BaseModel


class Contact(BaseModel):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brokerage_id: Mapped[int] = mapped_column(ForeignKey("brokerages.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phones: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Array of phones: ["010..., "012..."]
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    contact_type: Mapped[str] = mapped_column(String(50), default="buyer")  # buyer, seller, agent, other
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=True)  # facebook, whatsapp, referral, website
    activity_log: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    brokerage = relationship("Brokerage", back_populates="contacts")

    def __repr__(self):
        return f"<Contact {self.id}: {self.name} ({self.contact_type})>"
