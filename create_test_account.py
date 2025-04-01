import sqlite3
import random
import string
from datetime import datetime, timedelta

# Add a print statement to ensure the script is running
print("Starting account balance update script...")

def get_db_connection():
    """Connect to the SQLite database and set up row factory for dictionary access."""
    conn = sqlite3.connect('der_volt.db')
    conn.row_factory = sqlite3.Row
    return conn

def generate_account_number():
    """Generate a random account number."""
    return ''.join(random.choices(string.digits, k=12))

def generate_transaction_reference():
    """Generate a random transaction reference."""
    return 'TX' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def update_existing_account():
    """Update the existing test account with ID 4 to have a $200 balance."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Set the account ID to 4 (the one showing in the UI)
    account_id = 4
    
    # Check if the account exists
    cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    account = cursor.fetchone()
    
    if not account:
        print(f"Account with ID {account_id} does not exist.")
        conn.close()
        return
    
    print(f"Updating account: {account['account_name']} (ID: {account_id})")
    
    # Update the account balance to $200
    cursor.execute("""
        UPDATE accounts 
        SET balance = 200.00, updated_at = datetime('now') 
        WHERE id = ?
    """, (account_id,))
    
    conn.commit()
    
    # Verify the update
    cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
    new_balance = cursor.fetchone()['balance']
    
    print(f"Updated account balance to: ${new_balance:.2f}")
    
    conn.close()
    print("Account balance updated successfully!")

def create_test_account():
    """Create a test account with $200 balance and fake transactions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Test user ID - we're using ID 4 as set in the app.py session code
    user_id = 4
    
    # Check if the user exists
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        print(f"User with ID {user_id} does not exist. Please create the user first.")
        conn.close()
        return
    
    print(f"Creating test account for user {user['first_name']} {user['last_name']} (ID: {user_id})")
    
    # Generate a new account number
    account_number = generate_account_number()
    account_name = "Test Account $200"
    
    # Create the account
    cursor.execute("""
        INSERT INTO accounts (user_id, account_number, account_name, account_type, currency, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (user_id, account_number, account_name, "standard", "USD", 1))
    
    account_id = cursor.lastrowid
    
    print(f"Created account: {account_name} (ID: {account_id}, Number: {account_number})")
    
    # Generate fake transactions to create a $200 balance
    transactions = []
    
    # Target balance is $200
    target_balance = 200.0
    current_balance = 0.0
    
    # Start date for transactions (30 days ago)
    start_date = datetime.now() - timedelta(days=30)
    
    # Create initial deposit to start the account
    initial_deposit = random.uniform(50.0, 150.0)
    current_balance += initial_deposit
    
    transactions.append({
        "account_id": account_id,
        "user_id": user_id,
        "transaction_type": "deposit",
        "amount": round(initial_deposit, 2),
        "status": "completed",
        "reference": generate_transaction_reference(),
        "payment_method": random.choice(["bank_account", "mpesa", "card_payment"]),
        "description": "Initial deposit",
        "created_at": start_date.strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Generate random transactions over the past 30 days
    transaction_count = random.randint(10, 20)
    
    for i in range(transaction_count):
        # Transaction date (random time within the past 30 days, sorted chronologically)
        days_ago = random.randint(0, 29 - int(i * 29 / transaction_count))
        transaction_date = datetime.now() - timedelta(days=days_ago, 
                                                     hours=random.randint(0, 23),
                                                     minutes=random.randint(0, 59))
        
        # Decide whether to deposit or withdraw based on current balance
        # More likely to deposit if balance is low
        if current_balance < 50 or random.random() < 0.6:  # 60% chance of deposit
            transaction_type = "deposit"
            amount = round(random.uniform(10.0, 100.0), 2)
            current_balance += amount
            description = random.choice([
                "Salary payment", 
                "Freelance work", 
                "Client payment", 
                "Refund", 
                "Investment return"
            ])
        else:
            transaction_type = "withdrawal"
            # Don't withdraw more than 80% of current balance
            max_withdrawal = min(100.0, current_balance * 0.8)
            amount = round(random.uniform(10.0, max_withdrawal), 2)
            current_balance -= amount
            description = random.choice([
                "Online purchase",
                "Bill payment",
                "Subscription fee",
                "Transfer to savings",
                "ATM withdrawal"
            ])
        
        transactions.append({
            "account_id": account_id,
            "user_id": user_id,
            "transaction_type": transaction_type,
            "amount": amount,
            "status": "completed",
            "reference": generate_transaction_reference(),
            "payment_method": random.choice(["bank_account", "mpesa", "card_payment"]),
            "description": description,
            "created_at": transaction_date.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    # Add final adjustment to reach exactly $200 balance
    adjustment_amount = round(target_balance - current_balance, 2)
    
    if adjustment_amount != 0:
        transaction_type = "deposit" if adjustment_amount > 0 else "withdrawal"
        amount = abs(adjustment_amount)
        
        transactions.append({
            "account_id": account_id,
            "user_id": user_id,
            "transaction_type": transaction_type,
            "amount": amount,
            "status": "completed",
            "reference": generate_transaction_reference(),
            "payment_method": random.choice(["bank_account", "mpesa", "card_payment"]),
            "description": "Account adjustment",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    # Insert all transactions
    for tx in transactions:
        cursor.execute("""
            INSERT INTO transactions (
                account_id, user_id, transaction_type, amount, status, 
                reference, payment_method, description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tx["account_id"], tx["user_id"], tx["transaction_type"], tx["amount"], 
            tx["status"], tx["reference"], tx["payment_method"], tx["description"], 
            tx["created_at"], tx["created_at"]
        ))
    
    # Calculate actual totals for verification
    deposits = sum(tx["amount"] for tx in transactions if tx["transaction_type"] == "deposit")
    withdrawals = sum(tx["amount"] for tx in transactions if tx["transaction_type"] == "withdrawal")
    actual_balance = deposits - withdrawals
    
    # Update the account balance in the database
    cursor.execute("""
        UPDATE accounts 
        SET balance = ?, updated_at = datetime('now') 
        WHERE id = ?
    """, (actual_balance, account_id))
    
    conn.commit()
    
    print(f"Created {len(transactions)} transactions")
    print(f"Total deposits: ${deposits:.2f}")
    print(f"Total withdrawals: ${withdrawals:.2f}")
    print(f"Final balance: ${actual_balance:.2f}")
    print(f"Updated account balance in database to: ${actual_balance:.2f}")
    
    conn.close()
    print("Test account created successfully!")

if __name__ == "__main__":
    # Run the update function instead of creating a new account
    update_existing_account()
