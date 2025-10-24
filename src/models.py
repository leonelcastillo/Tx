from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.sql import func
import enum
from .database import Base


"""Database models for transactions (auth models removed for MVP)."""


class StatusEnum(str, enum.Enum):
    pending = "pending"
    collected = "collected"
    cancelled = "cancelled"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    wallet = Column(String, nullable=True)
    weight_kg = Column(Float, nullable=True)
    address = Column(String, nullable=True)
    photo = Column(String, nullable=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(StatusEnum), default=StatusEnum.pending, nullable=False)
    collected_weight_kg = Column(Float, nullable=True)
    collected_photo = Column(String, nullable=True)
    collected_at = Column(DateTime(timezone=True), nullable=True)
    # user_id removed - identification for MVP uses the 'wallet' field
