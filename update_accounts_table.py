import sqlite3
from database import get_db

def update_accounts_table():
    """
    Updates the accounts table to include the account_name column if it doesn't exist.
    This script should be run once to fix the database schema.
    """
    print("Updating accounts table to include account_name column...")
    
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # Check if account_name column exists
            cursor.execute("PRAGMA table_info(accounts)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if "account_name" not in columns:
                print("account_name column not found, adding it now...")
                
                try:
                    # Try to add the column to the existing table
                    cursor.execute("ALTER TABLE accounts ADD COLUMN account_name TEXT NOT NULL DEFAULT 'Default Account'")
                    db.commit()
                    print("Successfully added account_name column to accounts table.")
                    
                    # Update existing accounts with a name based on account number
                    cursor.execute("UPDATE accounts SET account_name = 'Account ' || substr(account_number, -4) WHERE account_name = 'Default Account'")
                    db.commit()
                    print("Updated existing accounts with names based on account numbers.")
                    
                except sqlite3.OperationalError as e:
                    print(f"Error adding column: {e}")
                    print("Attempting to recreate accounts table with correct schema...")
                    
                    # Backup existing accounts data
                    cursor.execute("SELECT id, user_id, account_number, account_type, balance, currency, is_active, created_at, updated_at FROM accounts")
                    existing_accounts = cursor.fetchall()
                    
                    # Create a temporary table with the correct schema
                    cursor.execute('''
                    CREATE TABLE accounts_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        account_number TEXT UNIQUE NOT NULL,
                        account_name TEXT NOT NULL DEFAULT 'Default Account',
                        account_type TEXT DEFAULT 'real',
                        balance REAL DEFAULT 0.0,
                        currency TEXT DEFAULT 'USD',
                        is_active INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                    ''')
                    
                    # Insert existing data into the new table
                    for account in existing_accounts:
                        account_name = f"Account {account['account_number'][-4:]}"
                        cursor.execute('''
                        INSERT INTO accounts_new (id, user_id, account_number, account_name, account_type, balance, currency, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            account['id'], 
                            account['user_id'], 
                            account['account_number'], 
                            account_name,
                            account['account_type'], 
                            account['balance'], 
                            account['currency'], 
                            account['is_active'], 
                            account['created_at'], 
                            account['updated_at']
                        ))
                    
                    # Replace the old table with the new one
                    cursor.execute("DROP TABLE accounts")
                    cursor.execute("ALTER TABLE accounts_new RENAME TO accounts")
                    db.commit()
                    print("Successfully recreated accounts table with account_name column.")
            else:
                print("account_name column already exists in accounts table.")
    
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    update_accounts_table() 