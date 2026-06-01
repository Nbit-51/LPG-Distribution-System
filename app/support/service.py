import random
import string
from app.database import execute_query

def generate_ticket_number() -> str:
    """Generates a unique 6-digit ticket tracking number conforming to complaint-handling standards."""
    while True:
        num = "".join(random.choices(string.digits, k=6))
        t_num = f"TIC-{num}"
        existing = execute_query("SELECT ticket_id FROM support_tickets WHERE ticket_number = %s", (t_num,))
        if not existing:
            return t_num

def get_ticket_by_id(ticket_id: int) -> dict:
    """Retrieves a support ticket by its internal database ID."""
    rows = execute_query("SELECT * FROM support_tickets WHERE ticket_id = %s", (ticket_id,))
    return rows[0] if rows else None

def create_ticket(consumer_id: int, data) -> dict:
    """Creates a new support ticket in the database linked to the consumer and optional booking."""
    ticket_num = generate_ticket_number()
    category_val = data.category if isinstance(data.category, str) else data.category.value
    priority_val = data.priority if isinstance(data.priority, str) else data.priority.value
    
    ticket_id = execute_query(
        "INSERT INTO support_tickets (ticket_number, consumer_id, booking_id, category, subject, description, priority, status) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, 'open')",
        (ticket_num, consumer_id, data.booking_id, category_val, data.subject, data.description, priority_val),
        fetch=False
    )
    return get_ticket_by_id(ticket_id)

def list_tickets_for_consumer(consumer_id: int) -> list:
    """Lists all support tickets submitted by a specific consumer, ordered by newest first."""
    return execute_query(
        "SELECT * FROM support_tickets WHERE consumer_id = %s ORDER BY created_at DESC", 
        (consumer_id,)
    )
