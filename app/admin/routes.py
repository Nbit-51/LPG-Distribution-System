from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from app.database import execute_query
from app.auth.service import get_current_admin
from app.consumers.schemas import KYCUpdate


router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


# ---------------------------------------------------------------------------
# Dashboard overview
# ---------------------------------------------------------------------------

@router.get("/overview")
def dashboard_overview(_=Depends(get_current_admin)):
    """
    Single endpoint that returns everything the admin dashboard needs:
    - total consumers, bookings, agencies
    - stock summary
    - active crises
    - unresolved shortages
    - recent bookings
    """
    consumers = execute_query("SELECT COUNT(*) AS t FROM consumers WHERE is_active = TRUE")[0]["t"]
    agencies  = execute_query("SELECT COUNT(*) AS t FROM agencies  WHERE is_active = TRUE")[0]["t"]

    booking_stats = execute_query(
        """SELECT status, COUNT(*) AS count
           FROM bookings GROUP BY status"""
    )

    stock_summary = execute_query("SELECT * FROM vw_agency_stock")

    active_crises = execute_query(
        """SELECT ce.*, a.agency_name FROM crisis_events ce
           JOIN agencies a ON ce.agency_id = a.agency_id
           WHERE ce.is_active = TRUE"""
    )

    shortages = execute_query(
        """SELECT sa.*, a.agency_name FROM shortage_alerts sa
           JOIN agencies a ON sa.agency_id = a.agency_id
           WHERE sa.is_resolved = FALSE ORDER BY sa.shortage_amount DESC LIMIT 10"""
    )

    recent_bookings = execute_query(
        """SELECT b.booking_id, b.booking_date, b.status, b.cylinders_requested,
                  c.full_name, c.consumer_type, a.agency_name
           FROM bookings b
           JOIN consumers c ON b.consumer_id = c.consumer_id
           JOIN agencies  a ON b.agency_id   = a.agency_id
           ORDER BY b.created_at DESC LIMIT 10"""
    )

    return {
        "totals": {
            "consumers": consumers,
            "agencies":  agencies,
            "bookings":  {r["status"]: r["count"] for r in booking_stats},
        },
        "stock_summary":    stock_summary,
        "active_crises":    active_crises,
        "shortages":        shortages,
        "recent_bookings":  recent_bookings,
    }


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@router.get("/reports/demand-supply")
def report_demand_supply(_=Depends(get_current_admin)):
    """Demand vs supply by consumer type per agency."""
    return execute_query("SELECT * FROM vw_demand_supply_report")


@router.get("/reports/allocations")
def report_allocations(
    agency_id: Optional[int] = Query(None),
    _=Depends(get_current_admin),
):
    """Allocation summary: how many cylinders went to each consumer type."""
    where  = "AND b.agency_id = %s" if agency_id else ""
    params = (agency_id,) if agency_id else ()
    return execute_query(
        f"""SELECT c.consumer_type,
               COUNT(DISTINCT al.booking_id)    AS bookings_allocated,
               SUM(al.cylinders_allocated)       AS cylinders_allocated
            FROM allocations al
            JOIN bookings  b ON al.booking_id = b.booking_id
            JOIN consumers c ON b.consumer_id = c.consumer_id
            WHERE 1=1 {where}
            GROUP BY c.consumer_type
            ORDER BY MIN(al.priority_score)""",
        params,
    )


@router.get("/reports/crisis-history")
def report_crisis(_=Depends(get_current_admin)):
    return execute_query(
        """SELECT ce.*, a.agency_name FROM crisis_events ce
           JOIN agencies a ON ce.agency_id = a.agency_id
           ORDER BY ce.triggered_at DESC"""
    )


@router.get("/reports/shortage-history")
def report_shortages(_=Depends(get_current_admin)):
    return execute_query(
        """SELECT sa.*, a.agency_name FROM shortage_alerts sa
           JOIN agencies a ON sa.agency_id = a.agency_id
           ORDER BY sa.alert_date DESC"""
    )


@router.get("/reports/consumer-summary")
def report_consumers(_=Depends(get_current_admin)):
    """Consumer counts and cylinder totals by type."""
    return execute_query(
        """SELECT consumer_type,
               COUNT(*)                                    AS total_consumers,
               SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active,
               SUM(cylinder_quota)                         AS total_quota
           FROM consumers
           GROUP BY consumer_type"""
    )


# ---------------------------------------------------------------------------
# Priority policy management
# ---------------------------------------------------------------------------

@router.get("/policies")
def get_policies(_=Depends(get_current_admin)):
    """View current priority and quota policies."""
    return execute_query("SELECT * FROM priority_policies ORDER BY priority_rank")


class PolicyUpdate(BaseModel):
    max_cylinders: Optional[int] = None
    crisis_max:    Optional[int] = None
    priority_rank: Optional[int] = None


@router.patch("/policies/{consumer_type}")
def update_policy(consumer_type: str, body: PolicyUpdate,
                  _=Depends(get_current_admin)):
    """Update allocation policy for a consumer type."""
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(400, "No fields to update.")
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    execute_query(
        f"UPDATE priority_policies SET {set_clause} WHERE consumer_type = %s",
        tuple(fields.values()) + (consumer_type,), fetch=False,
    )
    rows = execute_query(
        "SELECT * FROM priority_policies WHERE consumer_type = %s", (consumer_type,)
    )
    return rows[0] if rows else {}


# ---------------------------------------------------------------------------
# Booking restrictions management
# ---------------------------------------------------------------------------

@router.get("/restrictions")
def get_restrictions(_=Depends(get_current_admin)):
    return execute_query("SELECT * FROM booking_restrictions")


class RestrictionUpdate(BaseModel):
    min_gap_days:        Optional[int] = None
    max_cylinders_month: Optional[int] = None


@router.patch("/restrictions/{consumer_type}")
def update_restriction(consumer_type: str, body: RestrictionUpdate,
                       _=Depends(get_current_admin)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(400, "No fields to update.")
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    execute_query(
        f"UPDATE booking_restrictions SET {set_clause} WHERE consumer_type = %s",
        tuple(fields.values()) + (consumer_type,), fetch=False,
    )
    rows = execute_query(
        "SELECT * FROM booking_restrictions WHERE consumer_type = %s", (consumer_type,)
    )
    return rows[0] if rows else {}


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

@router.get("/audit-log")
def audit_log(
    page:      int           = Query(1,  ge=1),
    page_size: int           = Query(20, ge=1, le=100),
    _=Depends(get_current_admin),
):
    total  = execute_query("SELECT COUNT(*) AS t FROM audit_log")[0]["t"]
    offset = (page - 1) * page_size
    rows   = execute_query(
        """SELECT al.*, adm.username FROM audit_log al
           LEFT JOIN admins adm ON al.admin_id = adm.admin_id
           ORDER BY al.logged_at DESC LIMIT %s OFFSET %s""",
        (page_size, offset),
    )
    return {"total": total, "page": page, "page_size": page_size, "results": rows}

@router.patch("/consumers/{consumer_id}/kyc")
def admin_update_kyc(consumer_id: int, body: KYCUpdate, _=Depends(get_current_admin)):
    try:
        from app.consumers.service import update_kyc_status
        record = update_kyc_status(consumer_id, body.status)
        if not record:
            raise HTTPException(404, "Consumer not found.")
        return record
    except Exception as e:
        raise HTTPException(500, f"Database error: {e}")