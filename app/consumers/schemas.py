from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ConsumerType(str, Enum):
    domestic = "domestic"
    essential = "essential"
    commercial = "commercial"

class ConsumerCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    address: str
    consumer_type: ConsumerType
    agency_id: int

class ConsumerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    consumer_type: Optional[ConsumerType] = None
    is_active: Optional[bool] = None

class ConsumerResponse(BaseModel):
    id: int = Field(alias="consumer_id")
    name: str = Field(alias="full_name")
    email: Optional[str] = None
    phone: str
    address: str
    consumer_type: ConsumerType
    agency_id: int
    is_active: bool
    created_at: datetime
    kyc_status: Optional[str] = "unverified"
    kyc_doc_type: Optional[str] = None
    kyc_doc_num: Optional[str] = None
    kyc_submitted_at: Optional[datetime] = None

    model_config = {"from_attributes": True, "populate_by_name": True}

class ConsumerListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[ConsumerResponse]

class MessageResponse(BaseModel):
    message: str
    consumer_id: int

class KYCSubmit(BaseModel):
    doc_type: str
    doc_num: str

class KYCUpdate(BaseModel):
    status: str

class WalletAddFunds(BaseModel):
    amount: float

class AutoRefillToggle(BaseModel):
    enabled: bool

class WalletVerifyPayment(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    amount: float

