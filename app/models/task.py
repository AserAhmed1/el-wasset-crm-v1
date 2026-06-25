from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.models.base import BaseModel


class Task(BaseModel):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brokerage_id: Mapped[int] = mapped_column(ForeignKey("brokerages.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, completed
    priority: Mapped[str] = mapped_column(String(50), default="medium")  # low, medium, high, urgent
    task_type: Mapped[str] = mapped_column(String(50), default="follow_up")  # call, follow_up, meeting, showing, reminder
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("deals.id", ondelete="SET NULL"), nullable=True)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_conditional: Mapped[bool] = mapped_column(Boolean, default=False)
    condition_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # if_no_reply, if_after_days
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    brokerage = relationship("Brokerage", back_populates="tasks")

    def __repr__(self):
        return f"<Task {self.id}: {self.title}>"
