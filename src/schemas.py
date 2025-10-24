from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import enum


class StatusEnum(str, enum.Enum):
    pending = "pending"
    collected = "collected"
    cancelled = "cancelled"


class TransactionCreate(BaseModel):
    name: str = Field(..., example="Juan Perez")
    phone: Optional[str]
    wallet: Optional[str]
    # Make weight optional at submission. If provided it must be > 0.
    weight_kg: Optional[float] = Field(None, gt=0, description="Peso en kilogramos, si se proporciona debe ser mayor que 0")
    address: Optional[str]
    photo: Optional[str]


class TransactionUpdateStatus(BaseModel):
    status: StatusEnum


class TransactionOut(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    wallet: Optional[str]
    address: Optional[str]
    weight_kg: Optional[float]
    photo: Optional[str]
    collected_weight_kg: Optional[float]
    collected_photo: Optional[str]
    collected_at: Optional[datetime]
    date: Optional[datetime]
    status: StatusEnum
    # user_id removed for MVP

    class Config:
        orm_mode = True


# Authentication schemas removed for MVP
