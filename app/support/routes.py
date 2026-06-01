from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.auth.service import get_current_consumer
from app.support.schemas import TicketCreate, TicketResponse
from app.support import service

router = APIRouter(prefix="/support", tags=["Support"])

@router.post("/tickets", response_model=TicketResponse, status_code=201)
def create_ticket(body: TicketCreate, current_consumer: dict = Depends(get_current_consumer)):
    """
    Submits a new customer support ticket. Conforms to quality handling practices.
    Ensures any linked booking belongs to the authenticated consumer.
    """
    try:
        if body.booking_id:
            from app.bookings import service as booking_service
            booking = booking_service.get_booking_by_id(body.booking_id)
            if not booking or booking["consumer_id"] != current_consumer["consumer_id"]:
                raise HTTPException(
                    status_code=400, 
                    detail="The linked booking number does not exist or does not belong to your account."
                )
        
        ticket = service.create_ticket(current_consumer["consumer_id"], body)
        return ticket
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error while saving ticket: {e}")

@router.get("/tickets", response_model=List[TicketResponse])
def get_tickets(current_consumer: dict = Depends(get_current_consumer)):
    """
    Lists support tickets submitted by the currently logged-in consumer.
    """
    try:
        tickets = service.list_tickets_for_consumer(current_consumer["consumer_id"])
        return tickets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error while fetching tickets: {e}")
