from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date, datetime


class SupplyCreate(BaseModel):
    agency_id:          int
    cylinders_received: int
    supply_date:        date
    supplier_name:      Optional[str] = None
    notes:              Optional[str] = None

    @field_validator("cylinders_received")
    @classmethod
    def positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("cylinders_received must be at least 1.")
        return v


class SupplyResponse(BaseModel):
    stock_id:            int
    agency_id:           int
    agency_name:         Optional[str] = None
    cylinders_received:  int
    cylinders_available: int
    cylinders_allocated: int
    supply_date:         date
    supplier_name:       Optional[str]
    notes:               Optional[str]
    created_at:          datetime

    model_config = {"from_attributes": True}


class SupplyListResponse(BaseModel):
    total:     int
    page:      int
    page_size: int
    results:   list[SupplyResponse]