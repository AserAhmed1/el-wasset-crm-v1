from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, func
from datetime import datetime
from app.database import Base


class BaseModel(Base):
    __abstract__ = True
