import sys
import os

# Add the project root to sys.path to enable app imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.database import execute_query

def migrate():
    print("Starting database migration...")
    
    # 1. Add password_hash to delivery_agents if not exists
    columns_agents = execute_query("DESCRIBE delivery_agents")
    has_pwd = any(c['Field'] == 'password_hash' for c in columns_agents)
    if not has_pwd:
        print("Adding column 'password_hash' to 'delivery_agents'...")
        execute_query("ALTER TABLE delivery_agents ADD COLUMN password_hash VARCHAR(255) NULL", fetch=False)
        print("Column 'password_hash' added successfully.")
    else:
        print("Column 'password_hash' already exists in 'delivery_agents'.")

    # 2. Add agent_id to bookings if not exists
    columns_bookings = execute_query("DESCRIBE bookings")
    has_agent_id = any(c['Field'] == 'agent_id' for c in columns_bookings)
    if not has_agent_id:
        print("Adding column 'agent_id' to 'bookings'...")
        execute_query("ALTER TABLE bookings ADD COLUMN agent_id INT NULL", fetch=False)
        print("Adding foreign key constraint for 'agent_id' in 'bookings'...")
        execute_query("ALTER TABLE bookings ADD CONSTRAINT fk_bookings_delivery_agent FOREIGN KEY (agent_id) REFERENCES delivery_agents(agent_id) ON DELETE SET NULL", fetch=False)
        print("Column 'agent_id' and constraint added successfully.")
    else:
        print("Column 'agent_id' already exists in 'bookings'.")

    # 3. Add delivery_instructions to bookings if not exists
    has_instructions = any(c['Field'] == 'delivery_instructions' for c in columns_bookings)
    if not has_instructions:
        print("Adding column 'delivery_instructions' to 'bookings'...")
        execute_query("ALTER TABLE bookings ADD COLUMN delivery_instructions TEXT NULL", fetch=False)
        print("Column 'delivery_instructions' added successfully.")
    else:
        print("Column 'delivery_instructions' already exists in 'bookings'.")

    # 4. Create delivery_chats table
    print("Creating 'delivery_chats' table if not exists...")
    execute_query("""
    CREATE TABLE IF NOT EXISTS delivery_chats (
        chat_id INT AUTO_INCREMENT PRIMARY KEY,
        booking_id INT NOT NULL,
        sender_type ENUM('consumer', 'agent') NOT NULL,
        sender_name VARCHAR(100) NOT NULL,
        message TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
    )
    """, fetch=False)
    print("'delivery_chats' table verified.")
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
