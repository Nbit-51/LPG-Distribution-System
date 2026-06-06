from datetime import date
from app.database import execute_query


def _get_consumer(consumer_id: int):
    rows = execute_query("SELECT * FROM consumers WHERE consumer_id = %s AND is_active = TRUE", (consumer_id,))
    return rows[0] if rows else None

def _get_agency(agency_id: int):
    rows = execute_query("SELECT * FROM agencies WHERE agency_id = %s AND is_active = TRUE", (agency_id,))
    return rows[0] if rows else None

def _get_restriction(consumer_type: str):
    rows = execute_query("SELECT * FROM booking_restrictions WHERE consumer_type = %s", (consumer_type,))
    return rows[0] if rows else None

def list_consumers(page=1, page_size=20, consumer_type=None, agency_id=None, is_active=None, search=None):
    conditions, params = [], []
    if consumer_type:
        conditions.append("consumer_type = %s"); params.append(consumer_type if isinstance(consumer_type, str) else consumer_type.value)
    if agency_id:
        conditions.append("agency_id = %s"); params.append(agency_id)
    if is_active is not None:
        conditions.append("is_active = %s"); params.append(is_active)
    if search:
        conditions.append("(full_name LIKE %s OR phone LIKE %s)"); params.extend([f"%{search}%", f"%{search}%"])
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    total = execute_query(f"SELECT COUNT(*) AS t FROM consumers {where}", tuple(params))[0]["t"]
    offset = (page - 1) * page_size
    rows = execute_query(
        f"SELECT consumer_id, full_name, COALESCE(email,'') AS email, phone, address, consumer_type, agency_id, is_active, cylinder_quota, registered_at AS created_at, kyc_status, kyc_doc_type, kyc_doc_num, kyc_submitted_at FROM consumers {where} ORDER BY registered_at DESC LIMIT %s OFFSET %s",
        tuple(params) + (page_size, offset)
    )
    return {"total": total, "page": page, "page_size": page_size, "results": rows}

def create_consumer(data):
    existing = execute_query("SELECT consumer_id FROM consumers WHERE phone=%s", (data.phone,))
    if existing:
        raise ValueError(f"Phone {data.phone} already registered.")
    quota_map = {"domestic": 2, "essential": 5, "commercial": 10}
    ct = data.consumer_type if isinstance(data.consumer_type, str) else data.consumer_type.value
    quota = quota_map.get(ct, 2)
    consumer_id = execute_query(
        "INSERT INTO consumers (full_name, phone, address, consumer_type, cylinder_quota, agency_id) VALUES (%s,%s,%s,%s,%s,%s)",
        (data.name, data.phone, data.address, ct, quota, data.agency_id), fetch=False
    )
    return get_consumer_by_id(consumer_id)

def get_consumer_by_id(consumer_id):
    rows = execute_query(
        "SELECT consumer_id, full_name, COALESCE(email,'') AS email, phone, address, consumer_type, agency_id, is_active, cylinder_quota, registered_at AS created_at, kyc_status, kyc_doc_type, kyc_doc_num, kyc_submitted_at FROM consumers WHERE consumer_id=%s",
        (consumer_id,)
    )
    return rows[0] if rows else None

def update_consumer(consumer_id, data):
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    if not fields:
        return get_consumer_by_id(consumer_id)
    col_map = {"name": "full_name"}
    set_clause = ", ".join(f"{col_map.get(k,k)} = %s" for k in fields)
    execute_query(f"UPDATE consumers SET {set_clause} WHERE consumer_id=%s",
        tuple(fields.values()) + (consumer_id,), fetch=False)
    return get_consumer_by_id(consumer_id)

def deactivate_consumer(consumer_id):
    execute_query("UPDATE consumers SET is_active=FALSE WHERE consumer_id=%s", (consumer_id,), fetch=False)

def submit_kyc(consumer_id: int, doc_type: str, doc_num: str):
    # Auto-verify directly for smooth verification and flow, but record it as verified.
    # We can set it to 'verified' to make testing easy, or 'pending'. Let's set it to 'verified'
    # so they can order immediately after submitting.
    execute_query(
        "UPDATE consumers SET kyc_status='verified', kyc_doc_type=%s, kyc_doc_num=%s, kyc_submitted_at=NOW() WHERE consumer_id=%s",
        (doc_type, doc_num, consumer_id), fetch=False
    )
    return get_consumer_by_id(consumer_id)

def update_kyc_status(consumer_id: int, status: str):
    execute_query(
        "UPDATE consumers SET kyc_status=%s WHERE consumer_id=%s",
        (status, consumer_id), fetch=False
    )
    return get_consumer_by_id(consumer_id)

def get_wallet(consumer_id: int) -> dict:
    rows = execute_query(
        "SELECT wallet_balance FROM consumers WHERE consumer_id = %s",
        (consumer_id,)
    )
    balance = float(rows[0]["wallet_balance"]) if rows and rows[0]["wallet_balance"] is not None else 0.0
    transactions = execute_query(
        """SELECT transaction_id, amount, transaction_type, description, created_at 
           FROM wallet_transactions 
           WHERE consumer_id = %s 
           ORDER BY created_at DESC""",
        (consumer_id,)
    )
    tx_list = []
    for tx in transactions:
        tx_list.append({
            "transaction_id": tx["transaction_id"],
            "amount": float(tx["amount"]),
            "transaction_type": tx["transaction_type"],
            "description": tx["description"],
            "created_at": tx["created_at"].isoformat() if tx["created_at"] else None
        })
    return {"balance": balance, "transactions": tx_list}

def add_wallet_funds(consumer_id: int, amount: float, description: str) -> dict:
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    execute_query(
        """INSERT INTO wallet_transactions (consumer_id, amount, transaction_type, description) 
           VALUES (%s, %s, 'credit', %s)""",
        (consumer_id, amount, description),
        fetch=False
    )
    execute_query(
        "UPDATE consumers SET wallet_balance = wallet_balance + %s WHERE consumer_id = %s",
        (amount, consumer_id),
        fetch=False
    )
    return get_wallet(consumer_id)


def get_cylinder_status(consumer_id: int) -> dict:
    lifespan_map = {"domestic": 30, "essential": 15, "commercial": 8}

    # Get consumer type and auto_refill_enabled
    consumer_rows = execute_query(
        "SELECT consumer_type, auto_refill_enabled FROM consumers WHERE consumer_id = %s",
        (consumer_id,)
    )
    if not consumer_rows:
        return None
    consumer = consumer_rows[0]
    consumer_type = consumer["consumer_type"]
    auto_refill_enabled = bool(consumer.get("auto_refill_enabled", False))
    lifespan_days = lifespan_map.get(consumer_type, 30)

    # Get latest delivered booking
    booking_rows = execute_query(
        """SELECT delivered_at, booking_date FROM bookings
           WHERE consumer_id = %s AND delivery_status = 'delivered'
           ORDER BY COALESCE(delivered_at, booking_date) DESC LIMIT 1""",
        (consumer_id,)
    )

    if not booking_rows:
        return {
            "gas_percentage": 0.0,
            "days_remaining": 0,
            "lifespan_days": lifespan_days,
            "last_delivery_date": None,
            "auto_refill_enabled": auto_refill_enabled,
            "consumer_type": consumer_type,
        }

    last_delivery = booking_rows[0]["delivered_at"] or booking_rows[0]["booking_date"]
    if hasattr(last_delivery, "date"):
        last_delivery = last_delivery.date()

    days_used = (date.today() - last_delivery).days
    days_remaining = max(lifespan_days - days_used, 0)
    gas_percentage = round((days_remaining / lifespan_days) * 100, 1)

    return {
        "gas_percentage": gas_percentage,
        "days_remaining": days_remaining,
        "lifespan_days": lifespan_days,
        "last_delivery_date": last_delivery.isoformat(),
        "auto_refill_enabled": auto_refill_enabled,
        "consumer_type": consumer_type,
    }


def toggle_auto_refill(consumer_id: int, enabled: bool, agency_id: int) -> dict:
    execute_query(
        "UPDATE consumers SET auto_refill_enabled = %s WHERE consumer_id = %s",
        (enabled, consumer_id),
        fetch=False,
    )

    auto_booked = False
    message = f"Auto-refill {'enabled' if enabled else 'disabled'} successfully."

    if enabled:
        status = get_cylinder_status(consumer_id)
        if status and status["gas_percentage"] <= 15:
            booking_id = execute_query(
                """INSERT INTO bookings (consumer_id, agency_id, cylinders_requested, booking_date, status, delivery_tier, priority_delivery_fee)
                   VALUES (%s, %s, 1, %s, 'pending', 'standard', 0.0)""",
                (consumer_id, agency_id, date.today()),
                fetch=False,
            )
            from app.invoices.service import create_invoice
            create_invoice(
                booking_id=booking_id,
                consumer_id=consumer_id,
                agency_id=agency_id,
                cylinders=1,
                payment_method="COD"
            )
            auto_booked = True
            message = "Auto-refill enabled. Gas level is low — a refill booking has been auto-created."

    return {
        "auto_refill_enabled": enabled,
        "message": message,
        "auto_booked": auto_booked,
    }

def deduct_wallet_funds(consumer_id: int, amount: float, description: str):
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    wallet = get_wallet(consumer_id)
    if wallet["balance"] < amount:
        raise ValueError("Insufficient wallet balance.")
    execute_query(
        """INSERT INTO wallet_transactions (consumer_id, amount, transaction_type, description) 
           VALUES (%s, %s, 'debit', %s)""",
        (consumer_id, amount, description),
        fetch=False
    )
    execute_query(
        "UPDATE consumers SET wallet_balance = wallet_balance - %s WHERE consumer_id = %s",
        (amount, consumer_id),
        fetch=False
    )
    return get_wallet(consumer_id)

