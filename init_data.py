import sqlite3
import os
import random
import string
import hashlib
from datetime import datetime, timedelta
import uuid
import json

def get_db_connection():
    """Get a database connection with dictionary row factory"""
    db_path = os.path.join(os.path.dirname(__file__), 'der_volt.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Simple password hashing function"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_reference():
    """Generate a unique reference ID for transactions"""
    return str(uuid.uuid4())[:13].upper()

def create_sample_data():
    # Set user_id directly to 4
    user_id = 4
    
    # Check if user exists in database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            print(f"User with ID: {user_id} does not exist in the database")
            conn.close()
            return
        
        print(f"Using existing user with ID: {user_id}")
        
        # Find the account for this user
        cursor.execute("SELECT * FROM accounts WHERE user_id = ? LIMIT 1", (user_id,))
        account = cursor.fetchone()
        
        if not account:
            print(f"No account found for user with ID: {user_id}")
            conn.close()
            return
        
        account_id = account['id']
        print(f"Using existing account with ID: {account_id}")
        
        # Clear existing transactions for this user's account
        print("Clearing existing transactions for the account...")
        cursor.execute("DELETE FROM transactions WHERE account_id = ?", (account_id,))
        conn.commit()
        
        # Generate random transactions over the last 18 months
        print("Creating sample transactions...")
        now = datetime.now()
        
        # Initial balance
        balance = 0
        
        # Track totals for reporting
        total_deposits = 0
        total_withdrawals = 0
        
        # Generate between 30-50 transactions
        num_transactions = random.randint(30, 50)
        
        for i in range(num_transactions):
            # Random date within last 18 months
            days_ago = random.randint(0, 540)  # Up to ~18 months
            transaction_date = now - timedelta(days=days_ago)
            
            # Randomly decide transaction type (biased toward deposits)
            transaction_type = "deposit" if random.random() < 0.7 else "withdrawal"
            
            # Generate random amount
            if transaction_type == "deposit":
                amount = round(random.uniform(100, 2000), 2)
                total_deposits += amount
            else:
                amount = round(random.uniform(50, 500), 2)
                total_withdrawals += amount
            
            # Create reference/description
            if transaction_type == "deposit":
                descriptions = ["Salary", "Freelance work", "Client payment", "Consulting fee", "Refund", "Investment return"]
                description = random.choice(descriptions)
            else:
                descriptions = ["Grocery shopping", "Rent payment", "Utility bill", "Subscription", "Dining out", "Online purchase"]
                description = random.choice(descriptions)
            
            reference = f"{transaction_type.upper()}-{transaction_date.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            
            # Insert the transaction
            cursor.execute("""
                INSERT INTO transactions 
                (account_id, user_id, amount, transaction_type, status, reference, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                account_id,
                user_id,
                amount,
                transaction_type,
                "completed",
                reference,
                description,
                transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                transaction_date.strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        # Commit the transaction data
        conn.commit()
        
        # Calculate net profit - using correct formula for trading accounts
        net_profit = total_withdrawals - total_deposits
        
        print(f"Created {num_transactions} sample transactions")
        print(f"Total Deposits: ${total_deposits:,.2f}")
        print(f"Total Withdrawals: ${total_withdrawals:,.2f}")
        print(f"Net Profit: ${net_profit:,.2f}")
        print("Sample data initialization completed!")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    create_sample_data() 