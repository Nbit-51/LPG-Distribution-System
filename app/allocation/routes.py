from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.allocation import service

router = APIRouter(prefix="/allocation", tags=["Allocation & Crisis"])


class CrisisActivate(BaseModel):
    threshold_cylinders: int
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Allocation
# ---------------------------------------------------------------------------

@router.post("/run/{agency_id}")
def run_allocation(agency_id: int, admin_id: Optional[int] = Query(None)):
    """
    Run priority-based allocation for an agency.
    Distributes available stock to pending bookings:
    domestic first → essential → commercial.
    In crisis mode: commercial capped at crisis_max cylinders.
    """
    try:
        return service.run_allocation(agency_id, admin_id)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/history")
def allocation_history(
    agency_id: Optional[int] = Query(None),
    page:      int           = Query(1,  ge=1),
    page_size: int           = Query(20, ge=1, le=100),
):
    """Full allocation history with consumer and agency details."""
    return service.get_allocation_history(agency_id, page, page_size)


# ---------------------------------------------------------------------------
# Crisis mode
# ---------------------------------------------------------------------------

@router.post("/crisis/{agency_id}/activate")
def activate_crisis(agency_id: int, body: CrisisActivate):
    """
    Activate crisis mode for an agency.
    Once active, commercial bookings are restricted to crisis_max cylinders.
    """
    try:
        return service.activate_crisis(agency_id, body.threshold_cylinders, body.notes)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/crisis/{agency_id}/resolve")
def resolve_crisis(agency_id: int):
    """Resolve (deactivate) crisis mode for an agency."""
    try:
        return service.resolve_crisis(agency_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/crisis/{agency_id}/status")
def crisis_status(agency_id: int):
    """Check whether crisis mode is currently active for an agency."""
    return service.get_crisis_status(agency_id)


# ---------------------------------------------------------------------------
# Shortage detection
# ---------------------------------------------------------------------------

@router.get("/shortage/{agency_id}")
def detect_shortage(agency_id: int):
    """Compare pending demand vs available stock. Logs alert if shortage detected."""
    return service.detect_shortage(agency_id)


@router.get("/shortages")
def all_shortages():
    """All unresolved shortage alerts across all agencies."""
    return service.get_all_shortages()


@router.get("/report/demand-supply")
def demand_supply_report():
    """Demand vs supply breakdown by consumer type per agency."""
    return service.get_demand_supply_report()


from typing import List

class MockBooking(BaseModel):
    booking_id: int
    consumer_name: str
    consumer_type: str  # 'domestic', 'essential', 'commercial'
    cylinders_requested: int = Field(ge=1)
    booking_date: str  # YYYY-MM-DD
    waiting_days: int = Field(ge=0)

class SimulationInput(BaseModel):
    available_stock: int = Field(ge=0)
    crisis_mode: bool
    bookings: List[MockBooking]

@router.post("/simulate")
def simulate_allocation(body: SimulationInput):
    """
    Simulates FCFS vs. Smart Priority Allocation side-by-side on mock input bookings.
    """
    bookings_data = [b.dict() for b in body.bookings]
    
    # ----------------------------------------------------
    # 1. FCFS Simulation (First-Come, First-Served)
    # ----------------------------------------------------
    # FCFS sorts strictly by booking_date (oldest booking date first)
    fcfs_sorted = sorted(bookings_data, key=lambda x: x["booking_date"])
    
    fcfs_allocated = []
    fcfs_skipped = []
    fcfs_order = []
    fcfs_remaining_stock = body.available_stock
    
    for b in fcfs_sorted:
        fcfs_order.append(b["booking_id"])
        requested = b["cylinders_requested"]
        if requested <= fcfs_remaining_stock:
            fcfs_remaining_stock -= requested
            fcfs_allocated.append({
                "booking_id": b["booking_id"],
                "consumer_name": b["consumer_name"],
                "consumer_type": b["consumer_type"],
                "booking_date": b["booking_date"],
                "requested_qty": requested,
                "allocated_qty": requested,
                "reason": "Successfully allocated"
            })
        else:
            # FCFS does All-Or-Nothing and does NOT do pro-rata splitting
            fcfs_skipped.append({
                "booking_id": b["booking_id"],
                "consumer_name": b["consumer_name"],
                "consumer_type": b["consumer_type"],
                "booking_date": b["booking_date"],
                "requested_qty": requested,
                "reason": "Skipped due to partial stock limit (All-or-Nothing block)" if fcfs_remaining_stock > 0 else "Insufficient supply stock"
            })
            
    # ----------------------------------------------------
    # 2. Our Smart Priority Allocation Simulation
    # ----------------------------------------------------
    # Priority ranks: Domestic = 1, Essential = 2, Commercial = 3
    priority_ranks = {"domestic": 1, "essential": 2, "commercial": 3}
    
    smart_list = []
    for b in bookings_data:
        # Calculate dynamic priority score using age-based anti-starvation (0.02 escalation coefficient)
        base_rank = priority_ranks.get(b["consumer_type"].lower(), 3)
        effective_score = base_rank - (0.02 * max(0, b["waiting_days"]))
        
        b_copy = dict(b)
        b_copy["effective_priority_score"] = effective_score
        smart_list.append(b_copy)
        
    # Sort strictly by effective_priority_score (lowest score is highest priority), then booking_date ASC
    smart_sorted = sorted(smart_list, key=lambda x: (x["effective_priority_score"], x["booking_date"]))
    
    smart_allocated = []
    smart_skipped = []
    smart_order = []
    smart_remaining_stock = body.available_stock
    
    for b in smart_sorted:
        smart_order.append(b["booking_id"])
        if smart_remaining_stock <= 0:
            smart_skipped.append({
                "booking_id": b["booking_id"],
                "consumer_name": b["consumer_name"],
                "consumer_type": b["consumer_type"],
                "booking_date": b["booking_date"],
                "requested_qty": b["cylinders_requested"],
                "reason": "Stock depleted"
            })
            continue
            
        requested = b["cylinders_requested"]
        is_crisis_capped = False
        crisis_split_qty = 0
        
        # Apply crisis limit scaling
        if body.crisis_mode:
            # Domestic/Essential capped to 2, Commercial capped to 0 (freeze)
            crisis_max = 2 if b["consumer_type"].lower() in ("domestic", "essential") else 0
            if requested > crisis_max:
                is_crisis_capped = True
                crisis_split_qty = requested - crisis_max
                requested = crisis_max
                
        if requested == 0:
            smart_skipped.append({
                "booking_id": b["booking_id"],
                "consumer_name": b["consumer_name"],
                "consumer_type": b["consumer_type"],
                "booking_date": b["booking_date"],
                "requested_qty": b["cylinders_requested"],
                "reason": "Capped to 0 under active crisis rules"
            })
            continue
            
        is_shortage_split = False
        shortage_split_qty = 0
        allocated_qty = requested
        
        # Apply pro-rata splitting
        if requested > smart_remaining_stock:
            is_shortage_split = True
            shortage_split_qty = requested - smart_remaining_stock
            allocated_qty = smart_remaining_stock
            
        smart_remaining_stock -= allocated_qty
        
        # Determine status reason description
        notes = []
        if is_crisis_capped:
            notes.append(f"Capped to {allocated_qty} under crisis (split backorder: {crisis_split_qty})")
        if is_shortage_split:
            notes.append(f"Shortage split (allocated: {allocated_qty}, backordered: {shortage_split_qty})")
            
        smart_allocated.append({
            "booking_id": b["booking_id"],
            "consumer_name": b["consumer_name"],
            "consumer_type": b["consumer_type"],
            "booking_date": b["booking_date"],
            "requested_qty": b["cylinders_requested"],
            "allocated_qty": allocated_qty,
            "is_crisis_capped": is_crisis_capped,
            "crisis_split_qty": crisis_split_qty,
            "is_shortage_split": is_shortage_split,
            "shortage_split_qty": shortage_split_qty,
            "reason": ", ".join(notes) if notes else "Allocated in full"
        })
        
    fcfs_allocated_qty = sum(item["allocated_qty"] for item in fcfs_allocated)
    smart_allocated_qty = sum(item["allocated_qty"] for item in smart_allocated)
    total_requested_qty = sum(item["cylinders_requested"] for item in bookings_data)
    fcfs_unserved_qty = total_requested_qty - fcfs_allocated_qty
    smart_unserved_qty = total_requested_qty - smart_allocated_qty
    fcfs_domestic_qty = sum(item["allocated_qty"] for item in fcfs_allocated if item["consumer_type"].lower() == "domestic")
    smart_domestic_qty = sum(item["allocated_qty"] for item in smart_allocated if item["consumer_type"].lower() == "domestic")
    fcfs_commercial_qty = sum(item["allocated_qty"] for item in fcfs_allocated if item["consumer_type"].lower() == "commercial")
    smart_commercial_qty = sum(item["allocated_qty"] for item in smart_allocated if item["consumer_type"].lower() == "commercial")

    summary = {
        "available_stock": body.available_stock,
        "total_requested_qty": total_requested_qty,
        "fcfs_allocated_qty": fcfs_allocated_qty,
        "smart_allocated_qty": smart_allocated_qty,
        "fcfs_unserved_qty": fcfs_unserved_qty,
        "smart_unserved_qty": smart_unserved_qty,
        "fcfs_idle_stock": fcfs_remaining_stock,
        "smart_idle_stock": smart_remaining_stock,
        "fcfs_domestic_qty": fcfs_domestic_qty,
        "smart_domestic_qty": smart_domestic_qty,
        "fcfs_commercial_qty": fcfs_commercial_qty,
        "smart_commercial_qty": smart_commercial_qty,
        "smart_extra_allocated_qty": smart_allocated_qty - fcfs_allocated_qty,
        "smart_extra_domestic_qty": smart_domestic_qty - fcfs_domestic_qty,
        "smart_idle_saved_qty": fcfs_remaining_stock - smart_remaining_stock,
    }

    return {
        "summary": summary,
        "fcfs": {
            "allocated": fcfs_allocated,
            "skipped": fcfs_skipped,
            "remaining_stock": fcfs_remaining_stock,
            "allocation_order": fcfs_order,
            "allocated_qty": fcfs_allocated_qty,
            "unserved_qty": fcfs_unserved_qty
        },
        "smart": {
            "allocated": smart_allocated,
            "skipped": smart_skipped,
            "remaining_stock": smart_remaining_stock,
            "allocation_order": smart_order,
            "allocated_qty": smart_allocated_qty,
            "unserved_qty": smart_unserved_qty
        }
    }
