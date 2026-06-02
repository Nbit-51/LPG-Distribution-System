from fastapi import APIRouter, HTTPException, Depends, Request, Query
from typing import List, Optional
from app.delivery_agents import service, schemas
from app.auth.service import get_current_agent, get_current_consumer, get_current_admin
from jose import jwt, JWTError
from app.config import settings

router = APIRouter(prefix="", tags=["Delivery Agent & Chat"])

# Helper dependency to authenticate either a Consumer or a Delivery Agent (for chat/instructions)
def get_chat_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header.")
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.secret_key] if False else ["HS256"])
        sub = payload.get("sub", "")
        if sub.startswith("consumer:"):
            consumer_id = int(sub.split(":")[1])
            from app.auth.service import get_consumer_by_id_auth
            consumer = get_consumer_by_id_auth(consumer_id)
            if consumer:
                return {"type": "consumer", "id": consumer_id, "name": consumer["full_name"]}
        elif sub.startswith("agent:"):
            agent_id = int(sub.split(":")[1])
            agent = service.get_agent_by_id(agent_id)
            if agent:
                return {"type": "agent", "id": agent_id, "name": agent["full_name"]}
    except (JWTError, ValueError) as e:
        pass
    raise HTTPException(401, "Could not validate credentials.")

# ── Agent Endpoints ──

@router.get("/agent/bookings", response_model=List[schemas.BookingDeliveryDetail])
def get_agent_bookings(current_agent: dict = Depends(get_current_agent)):
    """Fetch bookings assigned to the currently authenticated delivery agent."""
    try:
        return service.list_agent_bookings(current_agent["agent_id"])
    except Exception as e:
        raise HTTPException(500, f"Error fetching agent bookings: {e}")

@router.get("/agent/bookings/{booking_id}/details", response_model=schemas.BookingDeliveryDetail)
def get_agent_booking_details(booking_id: int, current_agent: dict = Depends(get_current_agent)):
    """Get complete booking and customer details for an assigned booking."""
    booking = service.get_agent_booking_detail(booking_id, current_agent["agent_id"])
    if not booking:
        raise HTTPException(404, f"Assigned booking {booking_id} not found.")
    return booking

@router.patch("/agent/bookings/{booking_id}/status")
def update_booking_delivery_status(
    booking_id: int, 
    body: schemas.DeliveryStatusUpdate, 
    current_agent: dict = Depends(get_current_agent)
):
    """Updates the delivery status of a booking assigned to this agent."""
    booking = service.get_agent_booking_detail(booking_id, current_agent["agent_id"])
    if not booking:
        raise HTTPException(404, "Assigned booking not found.")
    try:
        service.update_delivery_status(booking_id, body.status.value)
        return {"message": "Delivery status updated successfully.", "status": body.status.value}
    except Exception as e:
        raise HTTPException(500, f"Error updating status: {e}")

# ── Consumer Endpoints for Delivery & Instructions ──

@router.get("/consumer/bookings/{booking_id}/delivery")
def get_consumer_booking_delivery(booking_id: int, current_consumer: dict = Depends(get_current_consumer)):
    """Retrieve details of the assigned delivery agent and customer instructions for a booking."""
    booking = service.get_booking_detail_for_consumer(booking_id, current_consumer["consumer_id"])
    if not booking:
        raise HTTPException(404, f"Booking {booking_id} not found for this consumer.")
    return booking

@router.patch("/consumer/bookings/{booking_id}/instructions")
def update_consumer_delivery_instructions(
    booking_id: int, 
    body: schemas.DeliveryInstructionsUpdate, 
    current_consumer: dict = Depends(get_current_consumer)
):
    """Update special delivery instructions (e.g. leave with neighbor, gate codes)."""
    booking = service.get_booking_detail_for_consumer(booking_id, current_consumer["consumer_id"])
    if not booking:
        raise HTTPException(404, "Booking not found.")
    try:
        service.update_delivery_instructions(booking_id, current_consumer["consumer_id"], body.delivery_instructions)
        return {"message": "Delivery instructions updated successfully."}
    except Exception as e:
        raise HTTPException(500, f"Error updating instructions: {e}")

# ── Dynamic Chat Endpoints (shared by Consumer and Agent) ──

@router.get("/bookings/{booking_id}/chat", response_model=List[schemas.ChatMessageResponse])
def get_chat(booking_id: int, user: dict = Depends(get_chat_user)):
    """Retrieve all chat messages for a specific booking. Restricted to booking owner and assigned agent."""
    # Check permissions: user must be consumer who owns booking, or agent assigned to it
    if user["type"] == "consumer":
        booking = service.get_booking_detail_for_consumer(booking_id, user["id"])
    else:
        booking = service.get_agent_booking_detail(booking_id, user["id"])
        
    if not booking:
        raise HTTPException(403, "Access denied: you are not authorized to view this booking's chat.")
        
    try:
        return service.get_chat_history(booking_id)
    except Exception as e:
        raise HTTPException(500, f"Error fetching chat history: {e}")

@router.post("/bookings/{booking_id}/chat", response_model=schemas.ChatMessageResponse)
def post_message(booking_id: int, body: schemas.ChatMessageCreate, user: dict = Depends(get_chat_user)):
    """Send a message to the delivery chat. Restricted to booking owner and assigned agent."""
    # Check permissions
    if user["type"] == "consumer":
        booking = service.get_booking_detail_for_consumer(booking_id, user["id"])
    else:
        booking = service.get_agent_booking_detail(booking_id, user["id"])
        
    if not booking:
        raise HTTPException(403, "Access denied: you are not authorized to send messages for this booking.")
        
    try:
        return service.post_chat_message(booking_id, user["type"], user["name"], body.message)
    except Exception as e:
        raise HTTPException(500, f"Error sending message: {e}")

# ── Admin Endpoints ──

@router.post("/admin/delivery-agents", response_model=schemas.DeliveryAgentResponse, status_code=201)
def admin_create_agent(body: schemas.DeliveryAgentCreate, current_admin: dict = Depends(get_current_admin)):
    """Admin-only: Registers a new delivery agent with login credentials."""
    try:
        return service.create_delivery_agent(body.full_name, body.phone, body.agency_id, body.password)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Database error creating agent: {e}")

@router.get("/admin/delivery-agents", response_model=List[schemas.DeliveryAgentResponse])
def admin_list_agents(agency_id: Optional[int] = None, current_admin: dict = Depends(get_current_admin)):
    """Admin-only: List all delivery agents, optionally filtered by agency."""
    try:
        return service.list_delivery_agents(agency_id)
    except Exception as e:
        raise HTTPException(500, f"Database error listing agents: {e}")


@router.get("/admin/delivery-agents/metrics")
def admin_delivery_agents_metrics(agency_id: Optional[int] = None, current_admin: dict = Depends(get_current_admin)):
    """Admin-only: Get performance and real-time active tracking metrics for delivery agents."""
    try:
        return service.get_delivery_agents_metrics(agency_id)
    except Exception as e:
        raise HTTPException(500, f"Database error fetching agent metrics: {e}")

@router.delete("/admin/delivery-agents/{agent_id}")
def admin_deactivate_agent(agent_id: int, current_admin: dict = Depends(get_current_admin)):
    """Admin-only: Deactivate a delivery agent's account."""
    try:
        service.deactivate_delivery_agent(agent_id)
        return {"message": f"Delivery agent {agent_id} deactivated."}
    except Exception as e:
        raise HTTPException(500, f"Database error deactivating agent: {e}")

@router.post("/admin/bookings/{booking_id}/assign")
def admin_assign_agent(booking_id: int, agent_id: Optional[int] = None, current_admin: dict = Depends(get_current_admin)):
    """Admin-only: Assign a delivery agent to a booking."""
    try:
        service.assign_agent_to_booking(booking_id, agent_id)
        return {"message": f"Agent {agent_id} assigned to booking {booking_id} successfully."}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Database error assigning agent: {e}")

# ── Gig Agent Pool & Claiming & Earnings ──

@router.get("/agent/bookings/available", response_model=List[schemas.BookingDeliveryDetail])
def get_available_bookings(current_agent: dict = Depends(get_current_agent)):
    """Gig Pool: Retrieve all unclaimed bookings at this agent's agency."""
    try:
        return service.list_available_bookings(current_agent["agency_id"])
    except Exception as e:
        raise HTTPException(500, f"Error fetching available bookings pool: {e}")

@router.post("/agent/bookings/{booking_id}/claim")
def claim_booking(booking_id: int, current_agent: dict = Depends(get_current_agent)):
    """Gig Claim: Claim an unassigned booking at the agent's agency."""
    try:
        service.claim_booking_for_agent(booking_id, current_agent["agent_id"])
        return {"message": "Booking claimed successfully."}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Database error claiming booking: {e}")

@router.get("/agent/earnings")
def get_earnings_ledger(current_agent: dict = Depends(get_current_agent)):
    """Gig Earnings: Get total earnings and completed jobs list."""
    try:
        return service.get_agent_earnings(current_agent["agent_id"])
    except Exception as e:
        raise HTTPException(500, f"Error fetching earnings details: {e}")

@router.get("/consumer/bookings/{booking_id}/tracking")
def get_consumer_booking_tracking(
    booking_id: int, 
    lat: float = Query(...), 
    lng: float = Query(...), 
    current_consumer: dict = Depends(get_current_consumer)
):
    """
    Retrieve real-time tracking position of the delivery agent assigned to a consumer's active booking.
    Accepts customer current coordinates to calculate linear path projection.
    """
    from app.database import execute_query
    from datetime import datetime
    import math

    # Check booking belongs to the authenticated consumer and fetch agency / agent details
    rows = execute_query(
        """SELECT b.booking_id, b.status, b.delivery_status, b.updated_at, b.agent_id,
                  a.latitude AS agency_lat, a.longitude AS agency_lng,
                  da.full_name AS agent_name, da.phone AS agent_phone
           FROM bookings b
           JOIN agencies a ON b.agency_id = a.agency_id
           LEFT JOIN delivery_agents da ON b.agent_id = da.agent_id
           WHERE b.booking_id = %s AND b.consumer_id = %s""",
        (booking_id, current_consumer["consumer_id"])
    )
    if not rows:
        raise HTTPException(404, f"Active booking {booking_id} not found.")
    
    b = rows[0]
    if not b["agent_id"]:
        return {
            "active": False,
            "message": "Delivery agent has not been assigned to this booking yet."
        }

    # Tracking is only active for allocated / out_for_delivery / pending states
    # If cancelled or delivered, tracking is inactive.
    if b["delivery_status"] not in ("allocated", "out_for_delivery", "pending", "delayed"):
        return {
            "active": False,
            "message": f"Tracking is inactive for booking status: {b['delivery_status'] or b['status']}."
        }

    # Simulate dynamic position between agency and customer coords
    agency_lat = float(b["agency_lat"]) if b["agency_lat"] is not None else 12.9716
    agency_lng = float(b["agency_lng"]) if b["agency_lng"] is not None else 77.5946
    
    # Calculate time progress (ratio)
    updated_at = b["updated_at"]
    if not updated_at:
        updated_at = datetime.now()
        
    seconds_elapsed = (datetime.now() - updated_at).total_seconds()
    # 5 minute simulated delivery trip (300 seconds)
    total_trip_seconds = 300.0
    ratio = min(1.0, max(0.0, seconds_elapsed / total_trip_seconds))
    
    # Linear interpolation
    agent_lat = agency_lat + (lat - agency_lat) * ratio
    agent_lng = agency_lng + (lng - agency_lng) * ratio
    
    # Add a slight road navigation wave pattern
    if ratio > 0.0 and ratio < 1.0:
        wiggle = 0.0003 * math.sin(ratio * math.pi * 6)
        agent_lat += wiggle
        agent_lng += wiggle
        
    return {
        "active": True,
        "booking_id": booking_id,
        "delivery_status": b["delivery_status"] or b["status"],
        "agent": {
            "name": b["agent_name"] or "Delivery Partner",
            "phone": b["agent_phone"] or "--"
        },
        "origin": {"lat": agency_lat, "lng": agency_lng},
        "destination": {"lat": lat, "lng": lng},
        "agent_location": {"lat": agent_lat, "lng": agent_lng},
        "progress": ratio * 100.0
    }

