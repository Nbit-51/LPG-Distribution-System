import sys
import os

# Add the project root to sys.path to enable app imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.database import execute_query

def check_table_count(table_name):
    try:
        res = execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
        return res[0]['count'], "OK"
    except Exception as e:
        return None, f"Error: {e}"

def verify_database_state():
    print("=" * 60)
    print("            LPG SYSTEM DATABASE VERIFICATION ROUTINE            ")
    print("=" * 60)
    
    tables = [
        "admins",
        "agencies",
        "consumers",
        "bookings",
        "delivery_agents",
        "qr_codes",
        "qr_scan_logs",
        "support_tickets"
    ]
    
    all_ok = True
    for t in tables:
        count, status = check_table_count(t)
        if count is not None:
            print(f"Table: {t:<20} | Status: {status:<8} | Rows: {count}")
        else:
            print(f"Table: {t:<20} | Status: {status}")
            all_ok = False
            
    print("-" * 60)
    if all_ok:
        print("Success: All tables exist, are accessible, and connected successfully!")
    else:
        print("Warning: Some tables are missing or returned connection errors.")
    print("=" * 60)

if __name__ == "__main__":
    verify_database_state()
