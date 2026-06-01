from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.supply.schemas import SupplyCreate, SupplyResponse, SupplyListResponse
from app.supply import service

router = APIRouter(prefix="/supply", tags=["Supply"])


@router.post("/", response_model=SupplyResponse, status_code=201)
def add_stock(body: SupplyCreate):
    """Record new cylinder stock received by an agency."""
    try:
        return service.add_stock(body)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/", response_model=SupplyListResponse)
def list_stock(
    page:      int          = Query(1,  ge=1),
    page_size: int          = Query(20, ge=1, le=100),
    agency_id: Optional[int] = Query(None),
):
    return service.list_stock(page, page_size, agency_id)


@router.get("/summary")
def stock_summary(agency_id: Optional[int] = Query(None)):
    """Current available vs allocated summary per agency."""
    return service.get_agency_summary(agency_id)


@router.get("/low-stock")
def low_stock(threshold: int = Query(50, description="Alert if available <= this value")):
    """Agencies with stock at or below the threshold."""
    return service.get_low_stock_agencies(threshold)


@router.get("/{stock_id}", response_model=SupplyResponse)
def get_stock(stock_id: int):
    record = service.get_stock_by_id(stock_id)
    if not record:
        raise HTTPException(404, f"Stock {stock_id} not found.")
    return record