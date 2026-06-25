from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON
from datetime import datetime
from app.models.base import BaseModel


class Property(BaseModel):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brokerage_id: Mapped[int] = mapped_column(ForeignKey("brokerages.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="available")  # available, pending, sold, rented
    property_type: Mapped[str] = mapped_column(String(50), default="apartment")  # apartment, villa, land, commercial
    bedrooms: Mapped[int] = mapped_column(default=0)
    bathrooms: Mapped[int] = mapped_column(default=0)
    area: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    images: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=list)  # Array of image URLs
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    developer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    installment_plan: Mapped[str | None] = mapped_column(Text, nullable=True)  # Egypt-specific: 7-10 year payment plans
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    brokerage = relationship("Brokerage", back_populates="properties")

    def __repr__(self):
        return f"<Property {self.id}: {self.title} ({self.status})>"
