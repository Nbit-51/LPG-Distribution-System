from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class DeliveryStatus(str, Enum):
    pending = "pending"
    allocated = "allocated"
    out_for_delivery = "out_for_delivery"
    delayed = "delayed"
    customer_not_home = "customer_not_home"
    delivered = "delivered"
    cancelled = "cancelled"

class DeliveryAgentCreate(BaseModel):
    full_name: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=15)
    agency_id: int
    password: str

class DeliveryAgentResponse(BaseModel):
    agent_id: int
    full_name: str
    phone: str
    agency_id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class AgentLogin(BaseModel):
    phone: str
    password: str

class DeliveryStatusUpdate(BaseModel):
    status: DeliveryStatus

class DeliveryInstructionsUpdate(BaseModel):
    delivery_instructions: str

class ChatMessageCreate(BaseModel):
    message: str

class ChatMessageResponse(BaseModel):
    chat_id: int
    booking_id: int
    sender_type: str
    sender_name: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}

class BookingDeliveryDetail(BaseModel):
    booking_id: int
    consumer_id: int
    agency_id: int
    cylinders_requested: int
    booking_date: datetime
    status: str
    delivery_status: Optional[str] = None
    delivery_instructions: Optional[str] = None
    consumer_name: str
    consumer_phone: str
    consumer_address: str
    agency_name: str
    route_cluster: Optional[str] = None

    model_config = {"from_attributes": True}
