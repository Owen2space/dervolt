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

def update_users_table():
    """Add OAuth columns to the users table"""
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        changes_made = False
        
        # Add is_oauth_user column if it doesn't exist
        if 'is_oauth_user' not in columns:
            print("Adding is_oauth_user column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_oauth_user INTEGER DEFAULT 0")
            changes_made = True
        
        # Add oauth_provider column if it doesn't exist
        if 'oauth_provider' not in columns:
            print("Adding oauth_provider column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN oauth_provider TEXT")
            changes_made = True
            
        # Add user_id column for external service IDs if it doesn't exist
        if 'user_id' not in columns:
            print("Adding user_id column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN user_id TEXT")
            changes_made = True
        
        if changes_made:
            # Commit changes and close connection
            conn.commit()
            print("Users table updated successfully.")
        else:
            print("No changes were needed. OAuth columns already exist.")
            
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating users table: {e}")
        return False

if __name__ == "__main__":
    print("Starting database update...")
    
    # First back up the database
    if backup_database():
        # Then update the users table
        update_users_table()
    else:
        print("Database update aborted.")
    
    print("Database update process completed.") 