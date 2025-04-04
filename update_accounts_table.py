import sqlite3
import os
from datetime import datetime

# Database file
DB_FILE = "der_volt.db"

def backup_database():
    """Create a backup of the database before making changes"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"der_volt_backup_{timestamp}.db"
    
    if not os.path.exists(DB_FILE):
        print(f"Database file {DB_FILE} not found.")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        
        # Back up to a new database file
        backup_conn = sqlite3.connect(backup_file)
        conn.backup(backup_conn)
        
        # Close connections
        backup_conn.close()
        conn.close()
        
        print(f"Database backed up to {backup_file}")
        return True
    except Exception as e:
        print(f"Backup failed: {e}")
        return False

def inspect_accounts_table():
    """Inspect the accounts table structure"""
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if accounts table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'")
        if not cursor.fetchone():
            print("Accounts table does not exist yet.")
            conn.close()
            return False
        
        # Get table schema
        cursor.execute("PRAGMA table_info(accounts)")
        columns = cursor.fetchall()
        
        print("Current accounts table columns:")
        column_names = [column[1] for column in columns]
        print(column_names)
        
        conn.close()
        return column_names
    except Exception as e:
        print(f"Error inspecting accounts table: {e}")
        return []

def update_accounts_table():
    """Add required columns to the accounts table"""
    try:
        # First check if the table exists and get its structure
        columns = inspect_accounts_table()
        if not columns:
            print("Cannot update accounts table - it doesn't exist or cannot be accessed.")
            return False
        
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        changes_made = False
        
        # Add account_number if needed
        if 'account_number' not in columns:
            print("Adding account_number column to accounts table...")
            cursor.execute("ALTER TABLE accounts ADD COLUMN account_number TEXT")
            changes_made = True
        
        # Add account_name if needed
        if 'account_name' not in columns:
            print("Adding account_name column to accounts table...")
            cursor.execute("ALTER TABLE accounts ADD COLUMN account_name TEXT")
            changes_made = True
            
        # Add account_type if needed
        if 'account_type' not in columns:
            print("Adding account_type column to accounts table...")
            cursor.execute("ALTER TABLE accounts ADD COLUMN account_type TEXT")
            changes_made = True
            
        # Add status if needed
        if 'status' not in columns:
            print("Adding status column to accounts table...")
            cursor.execute("ALTER TABLE accounts ADD COLUMN status TEXT DEFAULT 'active'")
            changes_made = True
        
        if changes_made:
            # Commit changes
            conn.commit()
            print("Accounts table updated successfully.")
        else:
            print("No changes needed for accounts table.")
        
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating accounts table: {e}")
        return False

if __name__ == "__main__":
    print("Starting accounts table update...")
    
    # First back up the database
    if backup_database():
        # Then update the accounts table
        update_accounts_table()
    else:
        print("Database update aborted.")
    
    print("Accounts table update process completed.") 