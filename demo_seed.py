"""
LPG Distribution System — Allocation Engine Demo
Usage:
    python demo_seed.py          # seed demo data and show queue
    python demo_seed.py --run    # run allocation and show results  
    python demo_seed.py --clean  # remove all demo data
"""

import sys
import mysql.connector
from datetime import date, timedelta

DB = dict(host="localhost", port=3306, database="lpg_distribution",
          user="root", password="11362", autocommit=False)

ALPHA = 0.02  # ageing coefficient: 1 tier per 50 days

def q(sql, params=(), fetch=True):
    c = mysql.connector.connect(**DB)
    try:
        cur = c.cursor(dictionary=True)
        cur.execute(sql, params)
        if fetch:
            return cur.fetchall()
        c.commit()
        return cur.lastrowid
    except Exception:
        c.rollback()
        raise
    finally:
        cur.close()
        c.close()

def p_eff(p_base, days):
    return round(p_base - ALPHA * days, 4)

def separator(char="─", width=72):
    print(char * width)

# ── Clean ────────────────────────────────────────────────────────────────────

def clean():
    q("DELETE FROM allocations WHERE booking_id IN "
      "(SELECT booking_id FROM bookings WHERE delivery_instructions LIKE %s)",
      ("%DEMO%",), fetch=False)
    q("DELETE FROM bookings WHERE delivery_instructions LIKE %s",   ("%DEMO%",), fetch=False)
    q("DELETE FROM supply_stock WHERE notes LIKE %s",               ("%DEMO%",), fetch=False)
    q("DELETE FROM consumers WHERE address LIKE %s",                ("%DEMO%",), fetch=False)
    q("DELETE FROM agencies WHERE agency_name = %s", ("Bengaluru Central LPG Agency",), fetch=False)

# ── Seed ─────────────────────────────────────────────────────────────────────

def seed():
    today = date.today()

    agency_id = q(
        """INSERT INTO agencies (agency_name, address, contact_number, region, is_active)
           VALUES (%s, %s, %s, %s, 1)""",
        ("Bengaluru Central LPG Agency", "12 MG Road, Bengaluru [DEMO]", "9876543210", "Bengaluru"),
        fetch=False
    )

    # (name, type, quota, days_ago)
    consumers = [
        ("Meena Devi",             "domestic",   2,  55),
        ("Spice Garden Restaurant","commercial",  6,  70),
        ("City Hospital",          "essential",   4,  10),
        ("Ravi Kumar",             "domestic",    2,   2),
        ("Green Hotel",            "commercial",  5,   5),
    ]

    booking_ids = []
    for name, ctype, quota, days_ago in consumers:
        cid = q(
            """INSERT INTO consumers
               (full_name, address, phone, consumer_type, cylinder_quota,
                agency_id, is_active, kyc_status, kyc_doc_type, kyc_doc_num)
               VALUES (%s,%s,%s,%s,%s,%s,1,'verified','Aadhaar','DEMO000000')""",
            (name, "DEMO", f"9800000000", ctype, quota, agency_id),
            fetch=False
        )
        bdate = today - timedelta(days=days_ago)
        bid = q(
            """INSERT INTO bookings
               (consumer_id, agency_id, cylinders_requested, booking_date,
                status, delivery_instructions)
               VALUES (%s,%s,%s,%s,'pending','DEMO')""",
            (cid, agency_id, quota, bdate),
            fetch=False
        )
        booking_ids.append(bid)

    q(
        """INSERT INTO supply_stock
           (agency_id, cylinders_received, cylinders_available,
            cylinders_allocated, supply_date, supplier_name, notes)
           VALUES (%s,10,10,0,%s,'IOCL Depot Bengaluru','DEMO')""",
        (agency_id, today),
        fetch=False
    )

    return agency_id

# ── Display queue ─────────────────────────────────────────────────────────────

def show_queue(agency_id):
    rows = q(
        """SELECT b.booking_id, c.full_name, c.consumer_type,
                  pp.priority_rank, b.cylinders_requested, b.booking_date,
                  DATEDIFF(CURDATE(), b.booking_date) AS days_waited
           FROM bookings b
           JOIN consumers c ON b.consumer_id = c.consumer_id
           JOIN priority_policies pp ON c.consumer_type = pp.consumer_type
           WHERE b.agency_id = %s AND b.status = 'pending'
             AND b.delivery_instructions = 'DEMO'""",
        (agency_id,)
    )

    # sort by p_eff ascending
    rows = sorted(rows, key=lambda r: p_eff(r["priority_rank"], r["days_waited"]))

    total_demand = sum(r["cylinders_requested"] for r in rows)

    print()
    separator()
    print(f"  PENDING BOOKINGS — Sorted by Effective Priority Score (P_eff ASC)")
    print(f"  Formula: P_eff = P_base - {ALPHA} x days_waiting")
    separator()
    print(f"  {'ID':<6} {'Consumer':<26} {'Type':<12} {'P_base':<8} "
          f"{'Days':<6} {'P_eff':<8} {'Cylinders'}")
    separator("─")
    for r in rows:
        score = p_eff(r["priority_rank"], r["days_waited"])
        print(f"  #{r['booking_id']:<5} {r['full_name']:<26} {r['consumer_type']:<12} "
              f"{r['priority_rank']:<8} {r['days_waited']:<6} {score:<8} {r['cylinders_requested']}")
    separator("─")
    print(f"  Total demand: {total_demand} cylinders    |    Stock available: 10 cylinders"
          f"    |    Shortage: {total_demand - 10} cylinders")
    separator()
    print()

# ── Run allocation ────────────────────────────────────────────────────────────

def run_allocation(agency_id):
    sys.path.insert(0, ".")
    from app.allocation.service import run_allocation as engine
    result = engine(agency_id=agency_id)

    print()
    separator()
    print("  ALLOCATION RESULT")
    separator()
    print(f"  Bookings allocated : {result['bookings_allocated']}")
    print(f"  Bookings skipped   : {result['bookings_skipped']}")
    print(f"  Stock before       : {result['stock_before']} cylinders")
    print(f"  Stock remaining    : {result['stock_remaining']} cylinders")
    separator()

    # Allocation audit trail
    allocated = q(
        """SELECT al.booking_id, c.full_name, c.consumer_type,
                  al.cylinders_allocated, al.priority_score,
                  b.booking_date,
                  DATEDIFF(CURDATE(), b.booking_date) AS days_waited
           FROM allocations al
           JOIN bookings b  ON al.booking_id  = b.booking_id
           JOIN consumers c ON b.consumer_id  = c.consumer_id
           WHERE b.agency_id = %s AND b.delivery_instructions = 'DEMO'
           ORDER BY al.priority_score ASC""",
        (agency_id,)
    )

    print()
    print("  ALLOCATION AUDIT TRAIL  (priority_score = dynamic P_eff stored at time of allocation)")
    separator("─")
    print(f"  {'Consumer':<26} {'Type':<12} {'Days':<6} {'P_eff stored':<14} {'Cylinders given'}")
    separator("─")
    for r in allocated:
        print(f"  {r['full_name']:<26} {r['consumer_type']:<12} "
              f"{r['days_waited']:<6} {float(r['priority_score']):<14} {r['cylinders_allocated']}")
    separator("─")

    # Backorders
    pending = q(
        """SELECT b.booking_id, c.full_name, c.consumer_type,
                  b.cylinders_requested, b.booking_date,
                  DATEDIFF(CURDATE(), b.booking_date) AS days_waited
           FROM bookings b
           JOIN consumers c ON b.consumer_id = c.consumer_id
           WHERE b.agency_id = %s AND b.status = 'pending'
             AND b.delivery_instructions = 'DEMO'""",
        (agency_id,)
    )

    if pending:
        print()
        print("  BACKORDERS  (pending — will be served in next supply batch)")
        separator("─")
        print(f"  {'Consumer':<26} {'Type':<12} {'Days waited':<14} {'Cylinders needed'}")
        separator("─")
        for r in pending:
            print(f"  {r['full_name']:<26} {r['consumer_type']:<12} "
                  f"{r['days_waited']:<14} {r['cylinders_requested']}")
        separator("─")
        print()
        print("  Note: booking_date is preserved on backorders.")
        print("  Ageing continues from original booking date, not from today.")

    print()
    separator()
    print()

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":

    if "--clean" in sys.argv:
        clean()
        print("Demo data removed.")
        sys.exit(0)

    if "--run" in sys.argv:
        rows = q("SELECT agency_id FROM agencies WHERE agency_name = %s",
                 ("Bengaluru Central LPG Agency",))
        if not rows:
            print("No demo data found. Run without flags first.")
            sys.exit(1)
        agency_id = rows[-1]["agency_id"]
        show_queue(agency_id)
        input("  Press ENTER to run the allocation engine...")
        run_allocation(agency_id)
        sys.exit(0)

    clean()
    agency_id = seed()
    show_queue(agency_id)
    print("  Run  'python demo_seed.py --run'    to execute allocation.")
    print("  Run  'python demo_seed.py --clean'  to remove demo data.")
    print()