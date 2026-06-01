from datetime import datetime
from app.database import execute_query


PRIORITY_RANK = {"domestic": 1, "essential": 2, "commercial": 3}


# ---------------------------------------------------------------------------
# Crisis mode helpers
# ---------------------------------------------------------------------------

def is_crisis_active(agency_id: int) -> bool:
    rows = execute_query(
        "SELECT crisis_id FROM crisis_events WHERE agency_id = %s AND is_active = TRUE",
        (agency_id,),
    )
    return bool(rows)


def activate_crisis(agency_id: int, threshold: int, notes: str | None = None) -> dict:
    if is_crisis_active(agency_id):
        raise ValueError(f"Crisis mode already active for agency {agency_id}.")
    execute_query(
        """INSERT INTO crisis_events (agency_id, threshold_cylinders, is_active, notes)
           VALUES (%s, %s, TRUE, %s)""",
        (agency_id, threshold, notes), fetch=False,
    )
    return {"message": f"Crisis mode activated for agency {agency_id}.", "agency_id": agency_id}


def resolve_crisis(agency_id: int) -> dict:
    if not is_crisis_active(agency_id):
        raise ValueError(f"No active crisis for agency {agency_id}.")
    execute_query(
        """UPDATE crisis_events SET is_active = FALSE, resolved_at = NOW()
           WHERE agency_id = %s AND is_active = TRUE""",
        (agency_id,), fetch=False,
    )
    return {"message": f"Crisis mode resolved for agency {agency_id}.", "agency_id": agency_id}


def get_crisis_status(agency_id: int) -> dict:
    rows = execute_query(
        "SELECT * FROM crisis_events WHERE agency_id = %s ORDER BY triggered_at DESC LIMIT 1",
        (agency_id,),
    )
    return rows[0] if rows else {"is_active": False}


# ---------------------------------------------------------------------------
# Core allocation engine
# ---------------------------------------------------------------------------

def run_allocation(agency_id: int, admin_id: int | None = None) -> dict:
    """
    Allocate available stock to pending bookings in priority order:
      1. domestic  → 2. essential  → 3. commercial
    In crisis mode: commercial gets max 2 cylinders per booking.
    Returns a summary of what was allocated.
    """
    crisis = is_crisis_active(agency_id)

    # Get available stock for this agency (oldest batch first)
    stock_rows = execute_query(
        """SELECT stock_id, cylinders_available FROM supply_stock
           WHERE agency_id = %s AND cylinders_available > 0
           ORDER BY supply_date ASC""",
        (agency_id,),
    )
    if not stock_rows:
        return {"allocated": 0, "skipped": 0, "message": "No stock available for allocation."}

    total_available = sum(r["cylinders_available"] for r in stock_rows)

    # Get pending bookings in priority order
    pending = execute_query(
        """SELECT b.booking_id, b.consumer_id, b.cylinders_requested, b.booking_date,
                  c.consumer_type, pp.priority_rank,
                  pp.max_cylinders, pp.crisis_max
           FROM   bookings b
           JOIN   consumers       c  ON b.consumer_id   = c.consumer_id
           JOIN   priority_policies pp ON c.consumer_type = pp.consumer_type
           WHERE  b.agency_id = %s AND b.status = 'pending'""",
        (agency_id,),
    )

    # 1. Starvation Prevention: Calculate Dynamic Priority Score using Ageing (Liveness property)
    from datetime import date
    pending_list = [dict(b) for b in pending]
    for b in pending_list:
        b_date = b["booking_date"]
        if isinstance(b_date, str):
            try:
                b_date = datetime.strptime(b_date, "%Y-%m-%d").date()
            except Exception:
                b_date = date.today()
        elif isinstance(b_date, datetime):
            b_date = b_date.date()
        
        days_elapsed = (date.today() - b_date).days
        # Every 50 waiting days escalates priority rank by 1.0 (anti-starvation policy)
        b["dynamic_priority_score"] = b["priority_rank"] - (0.02 * max(0, days_elapsed))

    # Sort strictly by dynamic_priority_score (lower score is higher priority), and booking_date ASC
    pending_sorted = sorted(pending_list, key=lambda x: (x["dynamic_priority_score"], x["booking_date"]))

    allocated_count = 0
    skipped_count   = 0
    remaining       = total_available
    stock_index     = 0
    stock_available = [dict(r) for r in stock_rows]

    for booking in pending_sorted:
        if remaining <= 0:
            break

        requested = booking["cylinders_requested"]

        # Apply crisis cap for all consumer types dynamically
        if crisis:
            requested = min(requested, booking["crisis_max"])

        if requested <= 0:
            # Skip bookings capped to 0 during crisis (e.g. commercial users with 0 crisis quota)
            skipped_count += 1
            continue

        # If capped to a positive value less than requested, update DB and split balance
        original_requested = booking["cylinders_requested"]
        if requested < original_requested:
            balance = original_requested - requested
            execute_query(
                "UPDATE bookings SET cylinders_requested = %s WHERE booking_id = %s",
                (requested, booking["booking_id"]), fetch=False
            )
            backorder_inst = f"AUTO-RESTRICT SPLIT: Balance of {balance} cylinder(s) from original booking #{booking['booking_id']} due to active crisis limits."
            execute_query(
                """INSERT INTO bookings (consumer_id, agency_id, cylinders_requested, booking_date, status, delivery_instructions)
                   VALUES (%s, %s, %s, %s, 'pending', %s)""",
                (booking["consumer_id"], agency_id, balance, booking["booking_date"], backorder_inst), fetch=False
            )

        # Dynamic Pro-Rata Booking Splitting during shortage
        if requested > remaining:
            take_now = remaining
            balance = requested - take_now
            
            # Update the original booking cylinders requested to what we can allocate now
            execute_query(
                "UPDATE bookings SET cylinders_requested = %s WHERE booking_id = %s",
                (take_now, booking["booking_id"]), fetch=False
            )
            
            # Create a new backorder split booking for the balance
            backorder_inst = f"AUTO-SPLIT BACKORDER: Balance of {balance} cylinder(s) from original booking #{booking['booking_id']} due to supply shortage."
            execute_query(
                """INSERT INTO bookings (consumer_id, agency_id, cylinders_requested, booking_date, status, delivery_instructions)
                   VALUES (%s, %s, %s, CURDATE(), 'pending', %s)""",
                (booking["consumer_id"], agency_id, balance, backorder_inst), fetch=False
            )
            
            requested = take_now

        # Deduct from stock batches (oldest first)
        to_allocate = requested
        while to_allocate > 0 and stock_index < len(stock_available):
            batch = stock_available[stock_index]
            take  = min(to_allocate, batch["cylinders_available"])

            # Deduct from DB
            execute_query(
                """UPDATE supply_stock
                   SET cylinders_available = cylinders_available - %s,
                       cylinders_allocated = cylinders_allocated + %s
                   WHERE stock_id = %s""",
                (take, take, batch["stock_id"]), fetch=False,
            )

            # Record allocation
            execute_query(
                """INSERT INTO allocations
                   (booking_id, stock_id, cylinders_allocated, priority_score, allocated_by_admin)
                   VALUES (%s, %s, %s, %s, %s)""",
                (booking["booking_id"], batch["stock_id"], take,
                 round(booking["dynamic_priority_score"], 4), admin_id),
                fetch=False,
            )

            batch["cylinders_available"] -= take
            to_allocate -= take
            remaining   -= take

            if batch["cylinders_available"] == 0:
                stock_index += 1

        # Mark booking as allocated
        execute_query(
            "UPDATE bookings SET status = 'allocated' WHERE booking_id = %s",
            (booking["booking_id"],), fetch=False,
        )
        allocated_count += 1

    return {
        "agency_id":        agency_id,
        "crisis_mode":      crisis,
        "stock_before":     total_available,
        "stock_remaining":  remaining,
        "bookings_allocated": allocated_count,
        "bookings_skipped":   skipped_count,
        "message": f"Allocated {allocated_count} booking(s). {skipped_count} skipped (insufficient stock).",
    }


# ---------------------------------------------------------------------------
# Shortage detection
# ---------------------------------------------------------------------------

def detect_shortage(agency_id: int) -> dict:
    """Compare total pending demand vs available stock for an agency."""
    demand = execute_query(
        """SELECT COALESCE(SUM(cylinders_requested), 0) AS total
           FROM bookings WHERE agency_id = %s AND status = 'pending'""",
        (agency_id,),
    )[0]["total"]

    supply = execute_query(
        """SELECT COALESCE(SUM(cylinders_available), 0) AS total
           FROM supply_stock WHERE agency_id = %s""",
        (agency_id,),
    )[0]["total"]

    shortage = max(0, demand - supply)

    if shortage > 0:
        # Log shortage alert
        execute_query(
            """INSERT INTO shortage_alerts (agency_id, demand_total, supply_total, alert_date)
               VALUES (%s, %s, %s, CURDATE())
               ON DUPLICATE KEY UPDATE demand_total = %s, supply_total = %s""",
            (agency_id, demand, supply, demand, supply), fetch=False,
        )

    return {
        "agency_id": agency_id,
        "demand":    demand,
        "supply":    supply,
        "shortage":  shortage,
        "is_shortage": shortage > 0,
    }


def get_all_shortages() -> list:
    return execute_query(
        """SELECT sa.*, a.agency_name, a.region
           FROM shortage_alerts sa
           JOIN agencies a ON sa.agency_id = a.agency_id
           WHERE sa.is_resolved = FALSE
           ORDER BY (sa.demand_total - sa.supply_total) DESC"""
    )


def get_demand_supply_report() -> list:
    return execute_query("SELECT * FROM vw_demand_supply_report")


def get_allocation_history(agency_id: int | None = None, page=1, page_size=20) -> dict:
    where  = "WHERE b.agency_id = %s" if agency_id else ""
    params = (agency_id,) if agency_id else ()
    total  = execute_query(
        f"SELECT COUNT(*) AS t FROM allocations al JOIN bookings b ON al.booking_id = b.booking_id {where}",
        params,
    )[0]["t"]
    offset = (page - 1) * page_size
    rows = execute_query(
        f"""SELECT al.*, b.agency_id, c.full_name, c.consumer_type, a.agency_name
            FROM   allocations al
            JOIN   bookings  b ON al.booking_id  = b.booking_id
            JOIN   consumers c ON b.consumer_id  = c.consumer_id
            JOIN   agencies  a ON b.agency_id    = a.agency_id
            {where}
            ORDER  BY al.allocated_at DESC LIMIT %s OFFSET %s""",
        params + (page_size, offset),
    )
    return {"total": total, "page": page, "page_size": page_size, "results": rows}