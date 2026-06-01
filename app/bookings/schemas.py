from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime
from enum import Enum


class BookingStatus(str, Enum):
    pending   = "pending"
    approved  = "approved"
    allocated = "allocated"
    cancelled = "cancelled"


class DeliveryStatus(str, Enum):
    pending          = "pending"
    out_for_delivery = "out_for_delivery"
    delivered        = "delivered"
    failed           = "failed"


class BookingCreate(BaseModel):
    consumer_id:         int
    agency_id:           int
    cylinders_requested: int
    booking_date:        date

    @field_validator("cylinders_requested")
    @classmethod
    def at_least_one(cls, v: int) -> int:
        if v < 1:
            raise ValueError("cylinders_requested must be at least 1.")
        return v


class BookingCancel(BaseModel):
    cancellation_reason: Optional[str] = None


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class BookingResponse(BaseModel):
    booking_id:          int
    consumer_id:         int
    consumer_name:       Optional[str] = None
    consumer_type:       Optional[str] = None
    agency_id:           int
    agency_name:         Optional[str] = None
    cylinders_requested: int
    booking_date:        date
    status:              BookingStatus
    delivery_status:     Optional[str] = None
    delivered_at:        Optional[datetime] = None
    cancellation_reason: Optional[str]      = None
    created_at:          datetime

    model_config = {"from_attributes": True}


class BookingListResponse(BaseModel):
    total:     int
    page:      int
    page_size: int
    results:   list[BookingResponse]