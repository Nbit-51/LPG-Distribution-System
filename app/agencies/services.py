from app.database import execute_query
from app.agencies.schemas import AgencyCreate, AgencyUpdate


def create_agency(data: AgencyCreate) -> dict:
    agency_id = execute_query(
        """
        INSERT INTO agencies (agency_name, address, contact_number, email, region)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (data.agency_name, data.address, data.contact_number, data.email, data.region),
        fetch=False,
    )
    return get_agency_by_id(agency_id)


def get_agency_by_id(agency_id: int) -> dict | None:
    rows = execute_query(
        "SELECT * FROM agencies WHERE agency_id = %s", (agency_id,)
    )
    return rows[0] if rows else None


def list_agencies(page: int = 1, page_size: int = 20,
                  region: str | None = None, is_active: bool | None = None) -> dict:
    conditions, params = [], []
    if region:
        conditions.append("region = %s"); params.append(region)
    if is_active is not None:
        conditions.append("is_active = %s"); params.append(is_active)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total  = execute_query(f"SELECT COUNT(*) AS t FROM agencies {where}", tuple(params))[0]["t"]
    offset = (page - 1) * page_size
    rows   = execute_query(
        f"SELECT * FROM agencies {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
        tuple(params) + (page_size, offset),
    )
    return {"total": total, "page": page, "page_size": page_size, "results": rows}


def update_agency(agency_id: int, data: AgencyUpdate) -> dict:
    existing = get_agency_by_id(agency_id)
    if not existing:
        raise ValueError(f"Agency {agency_id} not found.")
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    if not fields:
        return existing
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    execute_query(
        f"UPDATE agencies SET {set_clause} WHERE agency_id = %s",
        tuple(fields.values()) + (agency_id,), fetch=False,
    )
    return get_agency_by_id(agency_id)


def deactivate_agency(agency_id: int) -> dict:
    existing = get_agency_by_id(agency_id)
    if not existing:
        raise ValueError(f"Agency {agency_id} not found.")
    execute_query(
        "UPDATE agencies SET is_active = FALSE WHERE agency_id = %s",
        (agency_id,), fetch=False,
    )
    return get_agency_by_id(agency_id)


def get_agency_stock_summary(agency_id: int) -> dict | None:
    rows = execute_query(
        "SELECT * FROM vw_agency_stock WHERE agency_id = %s", (agency_id,)
    )
    return rows[0] if rows else None


def get_all_agency_stock() -> list:
    return execute_query("SELECT * FROM vw_agency_stock")