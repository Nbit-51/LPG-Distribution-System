from app.database import execute_query
from app.auth.service import hash_password, verify_password

def get_agent_by_id(agent_id: int) -> dict | None:
    rows = execute_query(
        "SELECT agent_id, full_name, phone, agency_id, is_active, created_at FROM delivery_agents WHERE agent_id = %s",
        (agent_id,)
    )
    return rows[0] if rows else None

def get_agent_by_phone(phone: str) -> dict | None:
    rows = execute_query(
        "SELECT * FROM delivery_agents WHERE phone = %s AND is_active = TRUE",
        (phone,)
    )
    return rows[0] if rows else None

def authenticate_agent(phone: str, password: str) -> dict:
    from fastapi import HTTPException, status
    agent = get_agent_by_phone(phone)
    if not agent:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Delivery agent phone number not registered.")
    if not agent.get("password_hash") or not verify_password(password, agent["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect password.")
    return agent

def create_delivery_agent(full_name: str, phone: str, agency_id: int, password: str) -> dict:
    existing = get_agent_by_phone(phone)
    if existing:
        raise ValueError(f"Delivery agent with phone {phone} already exists.")
    pwd_hash = hash_password(password)
    agent_id = execute_query(
        "INSERT INTO delivery_agents (full_name, phone, agency_id, password_hash, is_active) VALUES (%s, %s, %s, %s, TRUE)",
        (full_name, phone, agency_id, pwd_hash),
        fetch=False
    )
    return get_agent_by_id(agent_id)

def list_delivery_agents(agency_id: int = None) -> list:
    if agency_id:
        return execute_query(
            "SELECT agent_id, full_name, phone, agency_id, is_active, created_at FROM delivery_agents WHERE agency_id = %s",
            (agency_id,)
        )
    return execute_query(
        "SELECT agent_id, full_name, phone, agency_id, is_active, created_at FROM delivery_agents"
    )

def deactivate_delivery_agent(agent_id: int):
    execute_query("UPDATE delivery_agents SET is_active = FALSE WHERE agent_id = %s", (agent_id,), fetch=False)

def list_agent_bookings(agent_id: int) -> list:
    # Returns bookings assigned to this agent
    return execute_query(
        """SELECT b.*, c.full_name AS consumer_name, c.phone AS consumer_phone, c.address AS consumer_address, a.agency_name
           FROM bookings b
           JOIN consumers c ON b.consumer_id = c.consumer_id
           JOIN agencies  a ON b.agency_id   = a.agency_id
           WHERE b.agent_id = %s
           ORDER BY b.updated_at DESC""",
        (agent_id,)
    )

def get_agent_booking_detail(booking_id: int, agent_id: int) -> dict | None:
    rows = execute_query(
        """SELECT b.*, c.full_name AS consumer_name, c.phone AS consumer_phone, c.address AS consumer_address, a.agency_name
           FROM bookings b
           JOIN consumers c ON b.consumer_id = c.consumer_id
           JOIN agencies  a ON b.agency_id   = a.agency_id
           WHERE b.booking_id = %s AND b.agent_id = %s""",
        (booking_id, agent_id)
    )
    return rows[0] if rows else None

def get_booking_detail_for_consumer(booking_id: int, consumer_id: int) -> dict | None:
    rows = execute_query(
        """SELECT b.*, c.full_name AS consumer_name, c.phone AS consumer_phone, c.address AS consumer_address, a.agency_name,
                  da.full_name AS agent_name, da.phone AS agent_phone
           FROM bookings b
           JOIN consumers c ON b.consumer_id = c.consumer_id
           JOIN agencies  a ON b.agency_id   = a.agency_id
           LEFT JOIN delivery_agents da ON b.agent_id = da.agent_id
           WHERE b.booking_id = %s AND b.consumer_id = %s""",
        (booking_id, consumer_id)
    )
    return rows[0] if rows else None

def assign_agent_to_booking(booking_id: int, agent_id: int | None):
    # Check booking exists
    rows = execute_query("SELECT booking_id FROM bookings WHERE booking_id = %s", (booking_id,))
    if not rows:
        raise ValueError(f"Booking {booking_id} not found.")
    
    if agent_id:
        agent = get_agent_by_id(agent_id)
        if not agent:
            raise ValueError(f"Delivery agent {agent_id} not found.")
        
    execute_query("UPDATE bookings SET agent_id = %s WHERE booking_id = %s", (agent_id, booking_id), fetch=False)

def update_delivery_status(booking_id: int, status: str):
    # Update both status (main status) and delivery_status columns
    # In LPG, if status is marked delivered or cancelled, we update appropriately.
    # Standard states: pending, approved, allocated, cancelled
    # Custom logistics states: out_for_delivery, delayed, customer_not_home, delivered
    
    main_status = "allocated"
    delivered_clause = ""
    
    if status == "delivered":
        main_status = "delivered"
        delivered_clause = ", delivered_at = NOW()"
    elif status == "cancelled":
        main_status = "cancelled"

    execute_query(
        f"UPDATE bookings SET status = %s, delivery_status = %s {delivered_clause} WHERE booking_id = %s",
        (main_status, status, booking_id),
        fetch=False
    )

def update_delivery_instructions(booking_id: int, consumer_id: int, instructions: str):
    execute_query(
        "UPDATE bookings SET delivery_instructions = %s WHERE booking_id = %s AND consumer_id = %s",
        (instructions, booking_id, consumer_id),
        fetch=False
    )

# ── Chat ──
def get_chat_history(booking_id: int) -> list:
    return execute_query(
        "SELECT * FROM delivery_chats WHERE booking_id = %s ORDER BY created_at ASC",
        (booking_id,)
    )

def post_chat_message(booking_id: int, sender_type: str, sender_name: str, message: str) -> dict:
    chat_id = execute_query(
        "INSERT INTO delivery_chats (booking_id, sender_type, sender_name, message) VALUES (%s, %s, %s, %s)",
        (booking_id, sender_type, sender_name, message),
        fetch=False
    )
    rows = execute_query("SELECT * FROM delivery_chats WHERE chat_id = %s", (chat_id,))
    return rows[0]

def _extract_cluster(address: str) -> str:
    # Attempt to extract neighborhood cluster keyword (e.g. Koramangala, Indiranagar, Kuvempunagar)
    known_localities = [
        "Indiranagar", "Jayanagar", "Koramangala", "Whitefield", "HSR Layout", 
        "Malleshwaram", "Rajajinagar", "Banashankari", "Hebbal", "BTM Layout", 
        "JP Nagar", "Marathahalli", "Bellandur", "Yelahanka", "Kengeri", 
        "Yeshwanthpur", "Basavanagudi", "Ulsoor", "Richmond Town", "Frazer Town", 
        "Sadashivanagar", "Kalyan Nagar", "Electronic City", "Vasanth Nagar", 
        "Domlur", "CV Raman Nagar", "Kanakapura Road", "Bannerghatta Road", 
        "Vijayanagar", "RT Nagar", "Peenya", "HAL Road", "Cox Town", 
        "New BEL Road", "Mathikere", "Gokulam", "Kuvempunagar", "Vidyaranyapuram", 
        "Saraswathipuram", "Jayalakshmipuram", "Chamundipuram", "Siddhartha Layout", 
        "Yadavagiri", "Bannimantap", "Metagalli", "Devaraja Mohalla", "Nazarbad"
    ]
    address_lower = address.lower()
    for loc in known_localities:
        if loc.lower() in address_lower:
            return f"{loc} Route Cluster"
    
    # Fallback: split by comma and take the second to last part
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if len(parts) >= 2:
        return f"{parts[-2]} Cluster"
    return "General Route Cluster"

def list_available_bookings(agency_id: int) -> list:
    rows = execute_query(
        """SELECT b.*, c.full_name AS consumer_name, c.phone AS consumer_phone, c.address AS consumer_address, a.agency_name
           FROM bookings b
           JOIN consumers c ON b.consumer_id = c.consumer_id
           JOIN agencies  a ON b.agency_id   = a.agency_id
           WHERE b.agency_id = %s AND b.agent_id IS NULL AND b.status = 'allocated'
           ORDER BY b.created_at ASC""",
        (agency_id,)
    )
    
    # 2. Geographical Route Clustering: group allocated delivery jobs dynamically
    bookings_list = [dict(r) for r in rows]
    for b in bookings_list:
        address = b.get("consumer_address", "")
        b["route_cluster"] = _extract_cluster(address)
    return bookings_list

def claim_cluster_for_agent(agency_id: int, cluster_name: str, agent_id: int) -> dict:
    available = list_available_bookings(agency_id)
    target_booking_ids = [b["booking_id"] for b in available if b["route_cluster"] == cluster_name]
    
    if not target_booking_ids:
        raise ValueError(f"No active bookings available in {cluster_name}.")
        
    for booking_id in target_booking_ids:
        claim_booking_for_agent(booking_id, agent_id)
        
    return {"message": f"Successfully claimed {len(target_booking_ids)} bookings in {cluster_name}.", "claimed_ids": target_booking_ids}

def claim_booking_for_agent(booking_id: int, agent_id: int):
    # Check agent
    agent = get_agent_by_id(agent_id)
    if not agent:
        raise ValueError("Agent not found.")
        
    # Check booking is unassigned and at the agent's agency
    booking = execute_query(
        "SELECT booking_id, agency_id, agent_id, status FROM bookings WHERE booking_id = %s",
        (booking_id,)
    )
    if not booking:
        raise ValueError("Booking not found.")
        
    b = booking[0]
    if b["agent_id"] is not None:
        raise ValueError("Booking is already assigned to another agent.")
    if b["agency_id"] != agent["agency_id"]:
        raise ValueError("Booking is from a different agency.")
    if b["status"] != "allocated":
        raise ValueError("Booking is not in allocated state for delivery.")
        
    # Update assignment
    execute_query(
        "UPDATE bookings SET agent_id = %s, delivery_status = 'allocated' WHERE booking_id = %s",
        (agent_id, booking_id),
        fetch=False
    )

def get_agent_earnings(agent_id: int) -> dict:
    # Query delivered jobs counts & sum payouts from invoices
    payout_data = execute_query(
        """SELECT COUNT(*) AS total_delivered, COALESCE(SUM(i.delivery_fee), 0.0) AS total_earnings
           FROM bookings b
           JOIN invoices i ON b.booking_id = i.booking_id
           WHERE b.agent_id = %s AND b.delivery_status = 'delivered'""",
        (agent_id,)
    )
    
    # List completed orders detail
    completed_orders = execute_query(
        """SELECT b.booking_id, b.delivered_at, i.delivery_fee AS payout, c.full_name AS consumer_name
           FROM bookings b
           JOIN invoices i ON b.booking_id = i.booking_id
           JOIN consumers c ON b.consumer_id = c.consumer_id
           WHERE b.agent_id = %s AND b.delivery_status = 'delivered'
           ORDER BY b.delivered_at DESC""",
        (agent_id,)
    )
    
    res = payout_data[0] if payout_data else {"total_delivered": 0, "total_earnings": 0.0}
    return {
        "agent_id": agent_id,
        "total_delivered": res["total_delivered"],
        "total_earnings": float(res["total_earnings"]),
        "history": completed_orders
    }

