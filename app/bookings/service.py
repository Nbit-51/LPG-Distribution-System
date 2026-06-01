from datetime import date
from app.database import execute_query
from app.bookings.schemas import BookingCreate, BookingStatus


def _get_consumer(consumer_id):
    rows = execute_query(
        "SELECT * FROM consumers WHERE consumer_id = %s AND is_active = TRUE", (consumer_id,)
    )
    return rows[0] if rows else None


def _get_agency(agency_id):
    rows = execute_query(
        "SELECT * FROM agencies WHERE agency_id = %s AND is_active = TRUE", (agency_id,)
    )
    return rows[0] if rows else None


def _check_restrictions(consumer_id, consumer_type, cylinders, agency_id):
    restriction = execute_query(
        "SELECT * FROM booking_restrictions WHERE consumer_type = %s", (consumer_type,)
    )
    if not restriction:
        return
    r = restriction[0]

    # Check if this agency has an active crisis
    crisis_active = execute_query(
        "SELECT COUNT(*) AS active FROM crisis_events WHERE is_active = TRUE AND agency_id = %s",
        (agency_id,)
    )
    is_crisis = crisis_active and crisis_active[0]["active"] > 0
    
    # Adjust constraints dynamically if under crisis
    min_gap = r["min_gap_days"] * 2 if is_crisis else r["min_gap_days"]
    max_month = max(1, r["max_cylinders_month"] // 2) if is_crisis else r["max_cylinders_month"]

    # Min gap check
    last = execute_query(
        """SELECT booking_date FROM bookings
           WHERE consumer_id = %s AND status != 'cancelled'
           ORDER BY booking_date DESC LIMIT 1""",
        (consumer_id,),
    )
    if last:
        gap = (date.today() - last[0]["booking_date"]).days
        if gap < min_gap:
            prefix = "EMERGENCY STATE ENFORCED: " if is_crisis else ""
            raise ValueError(
                f"{prefix}Must wait {min_gap} days between bookings under current supply levels. "
                f"Last booking was {gap} day(s) ago."
            )

    # Monthly cap check
    used = execute_query(
        """SELECT COALESCE(SUM(cylinders_requested), 0) AS total FROM bookings
           WHERE consumer_id = %s AND status != 'cancelled'
           AND MONTH(booking_date) = MONTH(CURDATE())
           AND YEAR(booking_date)  = YEAR(CURDATE())""",
        (consumer_id,),
    )[0]["total"]
    if used + cylinders > max_month:
        prefix = "EMERGENCY SUPPLY CAP: " if is_crisis else ""
        raise ValueError(
            f"{prefix}Monthly cap for '{consumer_type}' is restricted to {max_month} cylinders. "
            f"Used: {used}, Requested: {cylinders}."
        )


def create_booking(data: BookingCreate) -> dict:
    consumer = _get_consumer(data.consumer_id)
    if not consumer:
        raise ValueError(f"Consumer {data.consumer_id} not found or inactive.")

    if consumer.get("kyc_status") != "verified":
        raise ValueError("KYC verification is required before placing a booking.")

    agency = _get_agency(data.agency_id)
    if not agency:
        raise ValueError(f"Agency {data.agency_id} not found or inactive.")

    if data.cylinders_requested > consumer["cylinder_quota"]:
        raise ValueError(
            f"Requested {data.cylinders_requested} exceeds consumer quota {consumer['cylinder_quota']}."
        )

    _check_restrictions(data.consumer_id, consumer["consumer_type"], data.cylinders_requested, data.agency_id)


    # No duplicate pending
    dupe = execute_query(
        "SELECT booking_id FROM bookings WHERE consumer_id = %s AND status = 'pending'",
        (data.consumer_id,),
    )
    if dupe:
        raise ValueError("Consumer already has a pending booking.")

    booking_id = execute_query(
        """INSERT INTO bookings (consumer_id, agency_id, cylinders_requested, booking_date, status)
           VALUES (%s, %s, %s, %s, 'pending')""",
        (data.consumer_id, data.agency_id, data.cylinders_requested, data.booking_date),
        fetch=False,
    )

    # Auto-generate tax invoice
    from app.invoices.service import create_invoice
    create_invoice(
        booking_id=booking_id,
        consumer_id=data.consumer_id,
        agency_id=data.agency_id,
        cylinders=data.cylinders_requested
    )

    return get_booking_by_id(booking_id)



def get_booking_by_id(booking_id: int) -> dict | None:
    rows = execute_query(
        """SELECT b.*, c.full_name AS consumer_name, c.consumer_type, a.agency_name
           FROM bookings b
           JOIN consumers c ON b.consumer_id = c.consumer_id
           JOIN agencies  a ON b.agency_id   = a.agency_id
           WHERE b.booking_id = %s""",
        (booking_id,),
    )
    return rows[0] if rows else None


def list_bookings(page=1, page_size=20, consumer_id=None, agency_id=None,
                  status=None, consumer_type=None, booking_date=None) -> dict:
    conditions, params = [], []
    if consumer_id:
        conditions.append("b.consumer_id = %s");  params.append(consumer_id)
    if agency_id:
        conditions.append("b.agency_id = %s");    params.append(agency_id)
    if status:
        conditions.append("b.status = %s");        params.append(status)
    if consumer_type:
        conditions.append("c.consumer_type = %s"); params.append(consumer_type)
    if booking_date:
        conditions.append("b.booking_date = %s");  params.append(booking_date)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total = execute_query(
        f"SELECT COUNT(*) AS t FROM bookings b JOIN consumers c ON b.consumer_id=c.consumer_id {where}",
        tuple(params),
    )[0]["t"]
    offset = (page - 1) * page_size
    rows = execute_query(
        f"""SELECT b.*, c.full_name AS consumer_name, c.consumer_type, a.agency_name
            FROM bookings b
            JOIN consumers c ON b.consumer_id = c.consumer_id
            JOIN agencies  a ON b.agency_id   = a.agency_id
            {where} ORDER BY b.created_at DESC LIMIT %s OFFSET %s""",
        tuple(params) + (page_size, offset),
    )
    return {"total": total, "page": page, "page_size": page_size, "results": rows}


def cancel_booking(booking_id: int, reason: str | None = None) -> dict:
    booking = get_booking_by_id(booking_id)
    if not booking:
        raise ValueError(f"Booking {booking_id} not found.")
    if booking["status"] in ("allocated", "cancelled"):
        raise ValueError(f"Cannot cancel a '{booking['status']}' booking.")
    execute_query(
        "UPDATE bookings SET status = 'cancelled', cancellation_reason = %s WHERE booking_id = %s",
        (reason, booking_id), fetch=False,
    )
    return get_booking_by_id(booking_id)


def update_status(booking_id: int, new_status: BookingStatus) -> dict:
    booking = get_booking_by_id(booking_id)
    if not booking:
        raise ValueError(f"Booking {booking_id} not found.")
    execute_query(
        "UPDATE bookings SET status = %s WHERE booking_id = %s",
        (new_status.value, booking_id), fetch=False,
    )
    return get_booking_by_id(booking_id)


def get_priority_queue(agency_id: int | None = None) -> list:
    where  = "WHERE agency_id = %s" if agency_id else ""
    params = (agency_id,) if agency_id else ()
    return execute_query(f"SELECT * FROM vw_priority_queue {where}", params)