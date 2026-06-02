import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.database import execute_query

def migrate():
    print("Starting database migration for Agent Ratings and Priority Delivery...")
    
    # Check current columns in bookings
    cols = execute_query("DESCRIBE bookings")
    existing_cols = {c['Field'] for c in cols}
    
    # 1. Add delivery_tier
    if 'delivery_tier' not in existing_cols:
        print("Adding column 'delivery_tier' to bookings table...")
        execute_query("ALTER TABLE bookings ADD COLUMN delivery_tier ENUM('standard', 'express') DEFAULT 'standard'", fetch=False)
        print("Column 'delivery_tier' added.")
    else:
        print("Column 'delivery_tier' already exists.")
        
    # 2. Add priority_delivery_fee
    if 'priority_delivery_fee' not in existing_cols:
        print("Adding column 'priority_delivery_fee' to bookings table...")
        execute_query("ALTER TABLE bookings ADD COLUMN priority_delivery_fee DECIMAL(10, 2) DEFAULT 0.00", fetch=False)
        print("Column 'priority_delivery_fee' added.")
    else:
        print("Column 'priority_delivery_fee' already exists.")
        
    # 3. Add delivery_agent_rating
    if 'delivery_agent_rating' not in existing_cols:
        print("Adding column 'delivery_agent_rating' to bookings table...")
        execute_query("ALTER TABLE bookings ADD COLUMN delivery_agent_rating INT DEFAULT NULL", fetch=False)
        print("Column 'delivery_agent_rating' added.")
    else:
        print("Column 'delivery_agent_rating' already exists.")
        
    # 4. Add delivery_agent_feedback
    if 'delivery_agent_feedback' not in existing_cols:
        print("Adding column 'delivery_agent_feedback' to bookings table...")
        execute_query("ALTER TABLE bookings ADD COLUMN delivery_agent_feedback VARCHAR(255) DEFAULT NULL", fetch=False)
        print("Column 'delivery_agent_feedback' added.")
    else:
        print("Column 'delivery_agent_feedback' already exists.")
        
    print("Database migration for Agent Ratings and Priority Delivery complete!")

if __name__ == "__main__":
    migrate()
