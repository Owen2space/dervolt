import sqlite3
from database import get_db, create_tables
from werkzeug.security import generate_password_hash
import uuid
from datetime import datetime, timedelta

def generate_account_number():
    return f"CR{uuid.uuid4().hex[:8].upper()}"

def generate_transaction_reference():
    return f"TRX{uuid.uuid4().hex[:8].upper()}"

def init_sample_data():
    """Initialize the database with sample data for testing"""
    create_tables()  # Ensure tables exist
    
    with get_db() as db:
        cursor = db.cursor()
        
        # Check if we already have sample data
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count > 0:
            print("Sample data already exists. Skipping initialization.")
            return
        
        # Create sample user
        cursor.execute("""
            INSERT INTO users (first_name, last_name, email, password_hash, phone_number, is_verified)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "John",
            "Doe",
            "john@example.com",
            generate_password_hash("password123"),
            "+1234567890",
            1
        ))
        
        user_id = cursor.lastrowid
        
        # Create sample accounts
        account_types = ["Savings", "Checking", "Investment"]
        account_ids = []
        
        for account_type in account_types:
            account_number = generate_account_number()
            cursor.execute("""
                INSERT INTO accounts (user_id, account_number, account_type, balance, currency)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                account_number,
                account_type,
                float(5000 + (1000 * account_types.index(account_type))),
                "USD"
            ))
            account_ids.append(cursor.lastrowid)
        
        # Create sample transactions
        transaction_types = ["deposit", "withdrawal", "transfer"]
        payment_methods = ["card", "bank", "wallet"]
        
        for i in range(10):
            days_ago = 10 - i
            transaction_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
            
            transaction_type = transaction_types[i % len(transaction_types)]
            account_id = account_ids[i % len(account_ids)]
            amount = float(100 + (i * 50))
            
            cursor.execute("""
                INSERT INTO transactions (
                    user_id, account_id, transaction_type, amount, 
                    status, reference, payment_method, description, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                account_id,
                transaction_type,
                amount,
                "completed" if i % 4 != 0 else "pending",
                generate_transaction_reference(),
                payment_methods[i % len(payment_methods)],
                f"Sample {transaction_type} transaction #{i+1}",
                transaction_date
            ))
        
        # Create sample notifications
        notification_types = ["transaction", "account", "system"]
        notification_titles = [
            "Deposit Successful", 
            "Withdrawal Completed", 
            "Account Verified", 
            "Security Alert", 
            "System Update"
        ]
        notification_messages = [
            "Your deposit of $500 has been confirmed",
            "Your withdrawal of $200 has been processed",
            "Your account has been successfully verified",
            "New login detected from an unknown device",
            "Scheduled maintenance in 2 days"
        ]
        
        for i in range(7):
            days_ago = 7 - i
            notification_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
            
            notification_type = notification_types[i % len(notification_types)]
            title_index = i % len(notification_titles)
            
            cursor.execute("""
                INSERT INTO notifications (
                    user_id, title, message, notification_type, is_read, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                notification_titles[title_index],
                notification_messages[title_index],
                notification_type,
                1 if i < 3 else 0,  # First 3 are read, rest are unread
                notification_date
            ))
        
        print("Sample data initialized successfully!")

if __name__ == "__main__":
    init_sample_data() 