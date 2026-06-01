import sys
import os

# Add the current directory to sys.path to enable app imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.database import execute_query

create_table_query = """
CREATE TABLE IF NOT EXISTS support_tickets (
  ticket_id   INT AUTO_INCREMENT PRIMARY KEY,
  ticket_number VARCHAR(20) NOT NULL UNIQUE,
  consumer_id INT NOT NULL,
  booking_id  INT NULL,
  category    VARCHAR(50) NOT NULL,
  subject     VARCHAR(200) NOT NULL,
  description TEXT NOT NULL,
  priority    VARCHAR(20) NOT NULL,
  status      VARCHAR(20) NOT NULL DEFAULT 'open',
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (consumer_id) REFERENCES consumers(consumer_id) ON DELETE CASCADE,
  FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE SET NULL
);
"""

if __name__ == "__main__":
    print("Running support ticket database setup...")
    try:
        execute_query(create_table_query, fetch=False)
        print("Success: support_tickets table is verified and created!")
    except Exception as e:
        print(f"Error running database DDL: {e}")
        sys.exit(1)
