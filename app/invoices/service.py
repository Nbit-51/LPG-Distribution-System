from app.database import execute_query

def create_invoice(booking_id: int, consumer_id: int, agency_id: int, cylinders: int, payment_method: str = "COD") -> int:
    # Fetch priority surcharge from the booking
    booking_rows = execute_query(
        "SELECT priority_delivery_fee FROM bookings WHERE booking_id = %s", (booking_id,)
    )
    priority_delivery_fee = 0.00
    if booking_rows and booking_rows[0]["priority_delivery_fee"]:
        priority_delivery_fee = float(booking_rows[0]["priority_delivery_fee"])

    base_rate = 850.00
    amount = base_rate * cylinders
    cgst = amount * 0.09
    sgst = amount * 0.09
    delivery_fee = 50.00 + priority_delivery_fee
    total_amount = amount + cgst + sgst + delivery_fee
    
    # Insert temporarily to get invoice_id
    invoice_id = execute_query(
        """INSERT INTO invoices (invoice_number, booking_id, consumer_id, agency_id, amount, cgst, sgst, delivery_fee, total_amount, payment_method, payment_status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')""",
        ("TEMP", booking_id, consumer_id, agency_id, amount, cgst, sgst, delivery_fee, total_amount, payment_method),
        fetch=False
    )
    
    # Generate the unique invoice number using the generated invoice_id
    invoice_num = f"INV-2026-{invoice_id:05d}"
    execute_query(
        "UPDATE invoices SET invoice_number = %s WHERE invoice_id = %s",
        (invoice_num, invoice_id),
        fetch=False
    )
    return invoice_id

def get_invoice_by_id(invoice_id: int):
    rows = execute_query(
        """SELECT i.*, c.full_name AS consumer_name, a.agency_name
           FROM invoices i
           JOIN consumers c ON i.consumer_id = c.consumer_id
           JOIN agencies a ON i.agency_id = a.agency_id
           WHERE i.invoice_id = %s""",
        (invoice_id,)
    )
    return rows[0] if rows else None

def get_invoices_by_consumer(consumer_id: int):
    return execute_query(
        """SELECT i.*, c.full_name AS consumer_name, a.agency_name
           FROM invoices i
           JOIN consumers c ON i.consumer_id = c.consumer_id
           JOIN agencies a ON i.agency_id = a.agency_id
           WHERE i.consumer_id = %s
           ORDER BY i.issued_at DESC""",
        (consumer_id,)
    )

def get_all_invoices(page: int = 1, page_size: int = 20):
    total = execute_query("SELECT COUNT(*) AS t FROM invoices")[0]["t"]
    offset = (page - 1) * page_size
    rows = execute_query(
        f"""SELECT i.*, c.full_name AS consumer_name, a.agency_name
           FROM invoices i
           JOIN consumers c ON i.consumer_id = c.consumer_id
           JOIN agencies a ON i.agency_id = a.agency_id
           ORDER BY i.issued_at DESC LIMIT %s OFFSET %s""",
        (page_size, offset)
    )
    return {"total": total, "results": rows}
