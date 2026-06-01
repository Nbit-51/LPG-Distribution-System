from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.agencies.schemas import AgencyCreate, AgencyUpdate, AgencyResponse, AgencyListResponse
from app.agencies import service

router = APIRouter(prefix="/agencies", tags=["Agencies"])

@router.post("/", response_model=AgencyResponse, status_code=201)
def create_agency(body: AgencyCreate):
    try:
        return service.create_agency(body)
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/", response_model=AgencyListResponse)
def list_agencies(
    page:      int            = Query(1,    ge=1),
    page_size: int            = Query(20,   ge=1, le=100),
    region:    Optional[str]  = Query(None),
    is_active: Optional[bool] = Query(None),
):
    return service.list_agencies(page, page_size, region, is_active)

@router.get("/stock")
def all_agency_stock():
    return service.get_all_agency_stock()

@router.get("/{agency_id}", response_model=AgencyResponse)
def get_agency(agency_id: int):
    record = service.get_agency_by_id(agency_id)
    if not record:
        raise HTTPException(404, f"Agency {agency_id} not found.")
    return record

@router.get("/{agency_id}/stock")
def agency_stock(agency_id: int):
    record = service.get_agency_stock_summary(agency_id)
    if not record:
        raise HTTPException(404, "Agency not found.")
    return record

@router.patch("/{agency_id}", response_model=AgencyResponse)
def update_agency(agency_id: int, body: AgencyUpdate):
    try:
        return service.update_agency(agency_id, body)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.delete("/{agency_id}")
def deactivate_agency(agency_id: int):
    try:
        service.deactivate_agency(agency_id)
        return {"message": f"Agency {agency_id} deactivated."}
    except ValueError as e:
        raise HTTPException(400, str(e))
