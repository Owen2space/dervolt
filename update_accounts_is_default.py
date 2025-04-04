import sqlite3
import os
import datetime
import time

DB_FILE = "der_volt.db"

def backup_database():
    """Create a backup of the database before making any changes"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"der_volt_backup_{timestamp}.db"
    
    if os.path.exists(DB_FILE):
        # Create a copy of the database file
        with open(DB_FILE, 'rb') as source:
            with open(backup_file, 'wb') as target:
                target.write(source.read())
        print(f"Database backed up to {backup_file}")
        return True
    else:
        print(f"Database file {DB_FILE} not found!")
        return False

def inspect_accounts_table():
    """Check the structure of the accounts table"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get column info for the accounts table
        cursor.execute("PRAGMA table_info(accounts)")
        columns = cursor.fetchall()
        
        print("Current columns in accounts table:")
        column_names = []
        for column in columns:
            if hasattr(column, 'keys'):
                # Dictionary-like row
                name = column['name']
                column_type = column['type']
                print(f"  - {name} ({column_type})")
                column_names.append(name)
            else:
                # Tuple-like row
                name = column[1] if len(column) > 1 else "unknown"
                column_type = column[2] if len(column) > 2 else "unknown"
                print(f"  - {name} ({column_type})")
                column_names.append(name)
                
        conn.close()
        return column_names
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

def update_accounts_table():
    """Add the is_default column to the accounts table if it doesn't exist"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get column names
        column_names = inspect_accounts_table()
        
        # Check for required columns and add them if missing
        columns_to_add = []
        
        if 'is_default' not in column_names:
            columns_to_add.append(("is_default", "INTEGER DEFAULT 0"))
        
        # Add missing columns
        for column_name, column_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE accounts ADD COLUMN {column_name} {column_type}")
                print(f"Added column {column_name} ({column_type}) to accounts table")
            except sqlite3.Error as e:
                print(f"Error adding column {column_name}: {e}")
        
        # Set first account for each user as default if is_default column was added
        if 'is_default' in columns_to_add:
            try:
                cursor.execute("""
                    WITH FirstAccounts AS (
                        SELECT id, user_id,
                            ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY id) as row_num
                        FROM accounts
                    )
                    UPDATE accounts
                    SET is_default = 1
                    WHERE id IN (
                        SELECT id FROM FirstAccounts WHERE row_num = 1
                    )
                """)
                print(f"Set default accounts for users")
            except sqlite3.Error as e:
                print(f"Error setting default accounts: {e}")
        
        conn.commit()
        conn.close()
        
        print("Update completed successfully")
        
        # Confirm changes by re-inspecting the table
        inspect_accounts_table()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Starting database update process...")
    if backup_database():
        time.sleep(1)  # Brief pause
        update_accounts_table()
    else:
        print("Backup failed, update aborted for safety.") 