from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List
from app.invoices.schemas import InvoiceResponse, InvoiceListResponse
from app.invoices import service
from app.auth.service import get_current_consumer, get_current_admin

router = APIRouter(prefix="/invoices", tags=["Invoices"])

@router.get("/my", response_model=List[InvoiceResponse])
def get_my_invoices(current_consumer=Depends(get_current_consumer)):
    try:
        return service.get_invoices_by_consumer(current_consumer["consumer_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/consumer/{consumer_id}", response_model=List[InvoiceResponse])
def get_consumer_invoices(consumer_id: int, _=Depends(get_current_admin)):
    try:
        return service.get_invoices_by_consumer(consumer_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin", response_model=InvoiceListResponse)
def get_all_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _=Depends(get_current_admin)
):
    try:
        return service.get_all_invoices(page, page_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice_detail(invoice_id: int):
    record = service.get_invoice_by_id(invoice_id)
    if not record:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return record
