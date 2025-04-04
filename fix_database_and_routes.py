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

def inspect_table(table_name):
    """Inspect a table structure"""
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            print(f"{table_name} table does not exist yet.")
            conn.close()
            return False
        
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"Current {table_name} table columns:")
        column_names = [column[1] for column in columns]
        print(column_names)
        
        conn.close()
        return column_names
    except Exception as e:
        print(f"Error inspecting {table_name} table: {e}")
        return []

def update_table_column(table_name, column_name, column_def):
    """Add a column to a table if it doesn't exist"""
    try:
        # First check if the table exists and get its structure
        columns = inspect_table(table_name)
        if not columns:
            print(f"Cannot update {table_name} table - it doesn't exist or cannot be accessed.")
            return False
        
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Add column if needed
        if column_name not in columns:
            print(f"Adding {column_name} column to {table_name} table...")
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
            conn.commit()
            print(f"{table_name} table updated successfully.")
            changes_made = True
        else:
            print(f"No changes needed for {table_name} table. {column_name} already exists.")
            changes_made = False
        
        conn.close()
        return changes_made
    except Exception as e:
        print(f"Error updating {table_name} table: {e}")
        return False

def verify_update_status():
    """Check if required columns exist in the database"""
    tables_to_check = {
        'users': ['preferred_payment_method'],
        'accounts': ['account_number', 'account_name', 'account_type', 'status']
    }
    
    print("\nVerifying database schema:")
    all_columns_exist = True
    
    for table, columns in tables_to_check.items():
        existing_columns = inspect_table(table)
        if not existing_columns:
            print(f"⚠️ {table} table not found!")
            all_columns_exist = False
            continue
            
        for column in columns:
            if column in existing_columns:
                print(f"✓ {table}.{column} exists")
            else:
                print(f"✗ {table}.{column} is missing!")
                all_columns_exist = False
    
    return all_columns_exist

if __name__ == "__main__":
    print("Starting database fix...")
    
    # First back up the database
    if backup_database():
        # Then update the tables
        print("\nUpdating users table:")
        update_table_column('users', 'preferred_payment_method', 'TEXT DEFAULT "mpesa"')
        
        print("\nUpdating accounts table:")
        update_table_column('accounts', 'account_number', 'TEXT')
        update_table_column('accounts', 'account_name', 'TEXT DEFAULT "Default Account"')
        update_table_column('accounts', 'account_type', 'TEXT DEFAULT "standard"')
        update_table_column('accounts', 'status', 'TEXT DEFAULT "active"')
        
        # Verify all required columns exist
        verify_update_status()
    else:
        print("Database update aborted.")
    
    print("Database fix process completed.") 