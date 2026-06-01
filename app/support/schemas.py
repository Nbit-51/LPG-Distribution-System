from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class TicketCategory(str, Enum):
    delivery_not_received = "delivery_not_received"
    damaged_cylinder = "damaged_cylinder"
    booking_issue = "booking_issue"
    billing = "billing"
    delayed_delivery = "delayed_delivery"
    other = "other"

class TicketPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"

class TicketCreate(BaseModel):
    category: TicketCategory
    booking_id: Optional[int] = None
    subject: str = Field(..., max_length=200)
    description: str
    priority: TicketPriority

class TicketResponse(BaseModel):
    ticket_id: int
    ticket_number: str
    consumer_id: int
    booking_id: Optional[int] = None
    category: TicketCategory
    subject: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
