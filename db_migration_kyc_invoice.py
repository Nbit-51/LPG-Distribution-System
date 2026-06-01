import sys
import os
import random

# Add the project root to sys.path to enable app imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.database import get_connection, execute_query

def migrate():
    print("Starting database updates for KYC and Invoices...")
    
    # 1. Add KYC columns to consumers
    cols = execute_query("DESCRIBE consumers")
    has_kyc_status = any(c['Field'] == 'kyc_status' for c in cols)
    if not has_kyc_status:
        print("Altering consumers table to add KYC fields...")
        execute_query("ALTER TABLE consumers ADD COLUMN kyc_status ENUM('unverified', 'pending', 'verified', 'rejected') DEFAULT 'unverified'", fetch=False)
        execute_query("ALTER TABLE consumers ADD COLUMN kyc_doc_type VARCHAR(50) NULL", fetch=False)
        execute_query("ALTER TABLE consumers ADD COLUMN kyc_doc_num VARCHAR(50) NULL", fetch=False)
        execute_query("ALTER TABLE consumers ADD COLUMN kyc_submitted_at DATETIME NULL", fetch=False)
        print("consumers table altered successfully.")
    else:
        print("consumers table already contains KYC fields.")

    # 2. Create invoices table
    print("Creating invoices table if not exists...")
    execute_query("""
    CREATE TABLE IF NOT EXISTS invoices (
        invoice_id INT AUTO_INCREMENT PRIMARY KEY,
        invoice_number VARCHAR(30) NOT NULL UNIQUE,
        booking_id INT NOT NULL,
        consumer_id INT NOT NULL,
        agency_id INT NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        cgst DECIMAL(10, 2) NOT NULL,
        sgst DECIMAL(10, 2) NOT NULL,
        delivery_fee DECIMAL(10, 2) NOT NULL,
        total_amount DECIMAL(10, 2) NOT NULL,
        payment_method VARCHAR(20) NOT NULL,
        payment_status ENUM('pending', 'paid', 'refunded') NOT NULL DEFAULT 'pending',
        issued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
        FOREIGN KEY (consumer_id) REFERENCES consumers(consumer_id) ON DELETE CASCADE,
        FOREIGN KEY (agency_id) REFERENCES agencies(agency_id) ON DELETE CASCADE
    )
    """, fetch=False)
    print("invoices table verified.")

    # 3. Clear and seed 50 agencies in Bangalore & Mysore in a single connection session
    conn = get_connection()
    try:
        cursor = conn.cursor()
        print("Clearing and reseeding premium LPG agencies inside transaction...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("DELETE FROM supply_stock")
        cursor.execute("DELETE FROM agencies")
        
        # 50 Agencies details
        bangalore_regions = [
            ("Indiranagar", 12.9719, 77.6412), ("Jayanagar", 12.9308, 77.5838),
            ("Koramangala", 12.9352, 77.6244), ("Whitefield", 12.9698, 77.7500),
            ("HSR Layout", 12.9103, 77.6450), ("Malleshwaram", 12.9961, 77.5714),
            ("Rajajinagar", 12.9902, 77.5529), ("Banashankari", 12.9254, 77.5468),
            ("Hebbal", 13.0354, 77.5988), ("BTM Layout", 12.9166, 77.6101),
            ("JP Nagar", 12.9063, 77.5857), ("Marathahalli", 12.9569, 77.7011),
            ("Bellandur", 12.9304, 77.6784), ("Yelahanka", 13.1006, 77.5963),
            ("Kengeri", 12.9175, 77.4838), ("Yeshwanthpur", 13.0232, 77.5501),
            ("Basavanagudi", 12.9417, 77.5755), ("Ulsoor", 12.9817, 77.6285),
            ("Richmond Town", 12.9616, 77.5984), ("Frazer Town", 12.9972, 77.6144),
            ("Sadashivanagar", 13.0068, 77.5802), ("Kalyan Nagar", 13.0221, 77.6403),
            ("Electronic City", 12.8452, 77.6602), ("Vasanth Nagar", 12.9891, 77.5927),
            ("Domlur", 12.9625, 77.6382), ("CV Raman Nagar", 12.9818, 77.6637),
            ("Kanakapura Road", 12.8712, 77.5732), ("Bannerghatta Road", 12.8951, 77.5982),
            ("Vijayanagar", 12.9738, 77.5313), ("RT Nagar", 13.0189, 77.5948),
            ("Peenya", 13.0284, 77.5192), ("HAL Road", 12.9654, 77.6582),
            ("Cox Town", 12.9982, 77.6221), ("New BEL Road", 13.0312, 77.5684),
            ("Mathikere", 13.0298, 77.5611)
        ]

        mysore_regions = [
            ("Gokulam", 12.3308, 76.6268), ("Kuvempunagar", 12.2922, 76.6221),
            ("Vijayanagar Mysore", 12.3382, 76.6084), ("Hebbal Mysore", 12.3551, 76.6134),
            ("Vidyaranyapuram", 12.2818, 76.6534), ("Saraswathipuram", 12.3012, 76.6341),
            ("Jayalakshmipuram", 12.3168, 76.6284), ("Chamundipuram", 12.2898, 76.6582),
            ("J P Nagar Mysore", 12.2718, 76.6612), ("Siddhartha Layout", 12.3021, 76.6784),
            ("Yadavagiri", 12.3298, 76.6432), ("Bannimantap", 12.3382, 76.6548),
            ("Metagalli", 12.3484, 76.6281), ("Devaraja Mohalla", 12.3082, 76.6512),
            ("Nazarbad", 12.3098, 76.6682)
        ]

        all_agencies = []
        for region, lat, lng in bangalore_regions:
            all_agencies.append({
                "name": f"{region} LPG Alliance",
                "region": "Bangalore",
                "address": f"No. {random.randint(10, 199)}, Main Road, {region}, Bangalore, Karnataka",
                "lat": lat,
                "lng": lng
            })
        for region, lat, lng in mysore_regions:
            all_agencies.append({
                "name": f"{region} Gas Corporation",
                "region": "Mysore",
                "address": f"Plot {random.randint(20, 250)}, Double Road, {region}, Mysore, Karnataka",
                "lat": lat,
                "lng": lng
            })

        print(f"Inserting {len(all_agencies)} premium agencies...")
        for idx, a in enumerate(all_agencies, start=1):
            phone = f"9886{idx:06d}"
            email = f"contact@{a['name'].lower().replace(' ', '')}.com"
            
            # Insert agency
            cursor.execute("""
            INSERT INTO agencies (agency_id, agency_name, address, contact_number, email, region, latitude, longitude, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            """, (idx, a["name"], a["address"], phone, email, a["region"], a["lat"], a["lng"]))
            
            # Seed random stock for supply_stock table
            cylinders_received = random.randint(150, 450)
            cylinders_available = cylinders_received - random.randint(10, 60)
            cursor.execute("""
            INSERT INTO supply_stock (agency_id, cylinders_received, cylinders_available, cylinders_allocated, supply_date, supplier_name, notes)
            VALUES (%s, %s, %s, 0, CURDATE(), 'Hindustan Petroleum Corp', 'Standard weekly cylinder supply seeded')
            """, (idx, cylinders_received, cylinders_available))

        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        print("Agencies and stocks successfully seeded!")
        print("Migration and Seeding complete!")
    except Exception as e:
        conn.rollback()
        print(f"FAIL during database migration transaction: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
