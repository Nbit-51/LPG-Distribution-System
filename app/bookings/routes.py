from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.bookings.schemas import (
    BookingCreate, BookingCancel, BookingStatusUpdate,
    BookingResponse, BookingListResponse, BookingStatus,
)
from app.bookings import service

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=BookingResponse, status_code=201)
def create_booking(body: BookingCreate):
    """Place a new booking. Enforces quota, gap, and monthly cap rules."""
    try:
        return service.create_booking(body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/", response_model=BookingListResponse)
def list_bookings(
    page:          int                    = Query(1,    ge=1),
    page_size:     int                    = Query(20,   ge=1, le=100),
    consumer_id:   Optional[int]          = Query(None),
    agency_id:     Optional[int]          = Query(None),
    status:        Optional[BookingStatus] = Query(None),
    consumer_type: Optional[str]          = Query(None),
    booking_date:  Optional[str]          = Query(None),
):
    return service.list_bookings(
        page, page_size, consumer_id, agency_id,
        status.value if status else None, consumer_type, booking_date,
    )


@router.get("/priority-queue")
def priority_queue(agency_id: Optional[int] = Query(None)):
    """Pending bookings ordered by priority: domestic → essential → commercial."""
    return {"results": service.get_priority_queue(agency_id)}


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int):
    record = service.get_booking_by_id(booking_id)
    if not record:
        raise HTTPException(404, f"Booking {booking_id} not found.")
    return record


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(booking_id: int, body: BookingCancel):
    try:
        return service.cancel_booking(booking_id, body.cancellation_reason)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.patch("/{booking_id}/status", response_model=BookingResponse)
def update_status(booking_id: int, body: BookingStatusUpdate):
    try:
        return service.update_status(booking_id, body.status)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/consumer/{consumer_id}/history", response_model=BookingListResponse)
def consumer_history(
    consumer_id: int,
    page:      int = Query(1,  ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return service.list_bookings(page=page, page_size=page_size, consumer_id=consumer_id)