from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Enum
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from .db import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime,default=datetime.utcnow,nullable=False)


# class Plan(Base):
#     __tablename__ = "plan"
