from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class AgencyCreate(BaseModel):
    agency_name:    str
    address:        str
    contact_number: Optional[str] = None
    email:          Optional[str] = None
    region:     Optional[str]   = None
    latitude:  Optional[float] = None
    longitude: Optional[float] = None

    @field_validator("agency_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("agency_name cannot be empty.")
        return v.strip()


class AgencyUpdate(BaseModel):
    agency_name:    Optional[str] = None
    address:        Optional[str] = None
    contact_number: Optional[str] = None
    email:          Optional[str] = None
    region:         Optional[str] = None
    latitude:  Optional[float] = None
    longitude: Optional[float] = None
    latitude:  Optional[float] = None
    longitude: Optional[float] = None


class AgencyResponse(BaseModel):
    agency_id:      int
    agency_name:    str
    address:        str
    contact_number: Optional[str]
    email:          Optional[str]
    region:         Optional[str]
    latitude:  Optional[float] = None
    longitude: Optional[float] = None
    latitude:  Optional[float] = None
    longitude: Optional[float] = None
    is_active:      bool
    created_at:     datetime

    model_config = {"from_attributes": True}


class AgencyListResponse(BaseModel):
    total:     int
    page:      int
    page_size: int
    results:   list[AgencyResponse]