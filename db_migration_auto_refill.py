import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.database import execute_query

def migrate():
    print("Starting database migration for Consumer Smart Auto-Refill...")
    
    # Check current columns in consumers
    cols = execute_query("DESCRIBE consumers")
    existing_cols = {c['Field'] for c in cols}
    
    # Add auto_refill_enabled
    if 'auto_refill_enabled' not in existing_cols:
        print("Adding column 'auto_refill_enabled' to consumers table...")
        execute_query("ALTER TABLE consumers ADD COLUMN auto_refill_enabled TINYINT(1) DEFAULT 0", fetch=False)
        print("Column 'auto_refill_enabled' added.")
    else:
        print("Column 'auto_refill_enabled' already exists.")
        
    print("Database migration for Auto-Refill complete!")

if __name__ == "__main__":
    migrate()
