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

def inspect_users_table():
    """Inspect the users table structure"""
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("Users table does not exist yet.")
            conn.close()
            return False
        
        # Get table schema
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        print("Current users table columns:")
        column_names = [column[1] for column in columns]
        print(column_names)
        
        conn.close()
        return column_names
    except Exception as e:
        print(f"Error inspecting users table: {e}")
        return []

def update_users_table():
    """Add preferred_payment_method column to the users table"""
    try:
        # First check if the table exists and get its structure
        columns = inspect_users_table()
        if not columns:
            print("Cannot update users table - it doesn't exist or cannot be accessed.")
            return False
        
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        changes_made = False
        
        # Add preferred_payment_method if needed
        if 'preferred_payment_method' not in columns:
            print("Adding preferred_payment_method column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN preferred_payment_method TEXT DEFAULT 'mpesa'")
            changes_made = True
        
        if changes_made:
            # Commit changes
            conn.commit()
            print("Users table updated successfully.")
        else:
            print("No changes needed for users table.")
        
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating users table: {e}")
        return False

if __name__ == "__main__":
    print("Starting users table update...")
    
    # First back up the database
    if backup_database():
        # Then update the users table
        update_users_table()
    else:
        print("Database update aborted.")
    
    print("Users table update process completed.") 