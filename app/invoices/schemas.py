from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class InvoiceResponse(BaseModel):
    invoice_id: int
    invoice_number: str
    booking_id: int
    consumer_id: int
    agency_id: int
    amount: float
    cgst: float
    sgst: float
    delivery_fee: float
    total_amount: float
    payment_method: str
    payment_status: str
    issued_at: datetime
    consumer_name: Optional[str] = None
    agency_name: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class InvoiceListResponse(BaseModel):
    total: int
    results: List[InvoiceResponse]
