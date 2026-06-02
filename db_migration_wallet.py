import sys
import os

# Add the project root to sys.path to enable app imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.database import execute_query

def migrate():
    print("Starting database migration for Wallet Feature...")
    
    # 1. Add wallet_balance to consumers if it doesn't exist
    cols = execute_query("DESCRIBE consumers")
    has_wallet_balance = any(c['Field'] == 'wallet_balance' for c in cols)
    if not has_wallet_balance:
        print("Altering consumers table to add wallet_balance field...")
        execute_query("ALTER TABLE consumers ADD COLUMN wallet_balance DECIMAL(10, 2) DEFAULT 0.00", fetch=False)
        print("consumers table altered successfully.")
    else:
        print("consumers table already contains wallet_balance field.")

    # 2. Create wallet_transactions table
    print("Creating wallet_transactions table if not exists...")
    execute_query("""
    CREATE TABLE IF NOT EXISTS wallet_transactions (
        transaction_id INT AUTO_INCREMENT PRIMARY KEY,
        consumer_id INT NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        transaction_type ENUM('credit', 'debit') NOT NULL,
        description VARCHAR(255) NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (consumer_id) REFERENCES consumers(consumer_id) ON DELETE CASCADE
    )
    """, fetch=False)
    print("wallet_transactions table verified.")
    print("Wallet feature database migration complete!")

if __name__ == "__main__":
    migrate()
