from app.database import execute_query
from app.supply.schemas import SupplyCreate


def add_stock(data: SupplyCreate) -> dict:
    ag = execute_query(
        "SELECT agency_id FROM agencies WHERE agency_id = %s AND is_active = TRUE", (data.agency_id,)
    )
    if not ag:
        raise ValueError(f"Agency {data.agency_id} not found or inactive.")

    stock_id = execute_query(
        """INSERT INTO supply_stock
           (agency_id, cylinders_received, cylinders_available, cylinders_allocated, supply_date, supplier_name, notes)
           VALUES (%s, %s, %s, 0, %s, %s, %s)""",
        (data.agency_id, data.cylinders_received, data.cylinders_received,
         data.supply_date, data.supplier_name, data.notes),
        fetch=False,
    )
    return get_stock_by_id(stock_id)


def get_stock_by_id(stock_id: int) -> dict | None:
    rows = execute_query(
        """SELECT s.*, a.agency_name FROM supply_stock s
           JOIN agencies a ON s.agency_id = a.agency_id
           WHERE s.stock_id = %s""",
        (stock_id,),
    )
    return rows[0] if rows else None


def list_stock(page=1, page_size=20, agency_id=None) -> dict:
    where  = "WHERE s.agency_id = %s" if agency_id else ""
    params = (agency_id,) if agency_id else ()
    total  = execute_query(
        f"SELECT COUNT(*) AS t FROM supply_stock s {where}", params
    )[0]["t"]
    offset = (page - 1) * page_size
    rows = execute_query(
        f"""SELECT s.*, a.agency_name FROM supply_stock s
            JOIN agencies a ON s.agency_id = a.agency_id
            {where} ORDER BY s.supply_date DESC LIMIT %s OFFSET %s""",
        params + (page_size, offset),
    )
    return {"total": total, "page": page, "page_size": page_size, "results": rows}


def get_agency_summary(agency_id: int | None = None) -> list:
    where  = "WHERE agency_id = %s" if agency_id else ""
    params = (agency_id,) if agency_id else ()
    return execute_query(f"SELECT * FROM vw_agency_stock {where}", params)


def deduct_stock(stock_id: int, cylinders: int) -> dict:
    stock = get_stock_by_id(stock_id)
    if not stock:
        raise ValueError(f"Stock {stock_id} not found.")
    if stock["cylinders_available"] < cylinders:
        raise ValueError(
            f"Insufficient stock. Available: {stock['cylinders_available']}, Requested: {cylinders}."
        )
    execute_query(
        """UPDATE supply_stock
           SET cylinders_available = cylinders_available - %s,
               cylinders_allocated = cylinders_allocated + %s
           WHERE stock_id = %s""",
        (cylinders, cylinders, stock_id), fetch=False,
    )
    return get_stock_by_id(stock_id)


def get_low_stock_agencies(threshold: int = 50) -> list:
    return execute_query(
        "SELECT * FROM vw_agency_stock WHERE total_available <= %s", (threshold,)
    )