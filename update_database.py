import sqlite3
import os
import sys
from datetime import datetime

# Database file
DB_NAME = "der_volt.db"

def backup_database():
    """Create a backup of the current database"""
    backup_name = f"der_volt_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    if os.path.exists(DB_NAME):
        try:
            # Read the original database
            with open(DB_NAME, 'rb') as src_file:
                data = src_file.read()
            
            # Write to the backup file
            with open(backup_name, 'wb') as backup_file:
                backup_file.write(data)
                
            print(f"✅ Database backed up to {backup_name}")
            return True
        except Exception as e:
            print(f"❌ Database backup failed: {e}")
            return False
    else:
        print(f"❌ Original database {DB_NAME} not found")
        return False

def update_database_schema():
    """Update the database schema by dropping and recreating tables"""
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Drop existing tables if they exist
        print("Dropping existing tables...")
        cursor.execute("DROP TABLE IF EXISTS accounts")
        print("✅ Dropped accounts table")
        
        cursor.execute("DROP TABLE IF EXISTS users")
        print("✅ Dropped users table")
        
        # Create users table with updated schema
        print("Creating updated users table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL UNIQUE,
            user_id TEXT NOT NULL UNIQUE,
            email TEXT,
            fullname TEXT,
            country TEXT,
            is_active INTEGER DEFAULT 1,
            blocked_reason TEXT,
            blocked_at TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """)
        print("✅ Created users table")
        
        # Create accounts table with updated schema
        print("Creating updated accounts table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            deriv_id TEXT,
            loginid TEXT NOT NULL,
            balance TEXT,
            currency TEXT,
            is_virtual TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)
        print("✅ Created accounts table")
        
        # Create indexes for faster lookups
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON users(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_loginid ON accounts(loginid)")
        print("✅ Created indexes")
        
        # Commit changes
        conn.commit()
        print("✅ All changes committed")
        
        # Close connection
        conn.close()
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error updating database: {e}")
        return False

def main():
    """Main function to run the database update"""
    print("Starting database update process...")
    
    # Check if database exists
    if not os.path.exists(DB_NAME):
        print(f"❌ Database {DB_NAME} does not exist. Creating new database.")
        
    # Backup the database before making changes
    backup_success = backup_database()
    if not backup_success and os.path.exists(DB_NAME):
        confirm = input("Failed to backup database. Continue anyway? (y/n): ").lower()
        if confirm != 'y':
            print("Update cancelled.")
            sys.exit(1)
    
    # Update the database schema
    update_success = update_database_schema()
    
    if update_success:
        print("✅ Database schema updated successfully!")
    else:
        print("❌ Failed to update database schema.")
        sys.exit(1)

if __name__ == "__main__":
    main() 