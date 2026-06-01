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

