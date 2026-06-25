from sqlalchemy import Column, Integer, String, Text
from app.database import Base
from app.models.base import BaseModel


class Setting(BaseModel):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
