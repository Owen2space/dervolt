import sqlite3
import datetime
import uuid

# Database file
DB_NAME = "der_volt.db"

def generate_uid(length=16):
    """Generate a unique identifier with the specified length."""
    random_uuid = str(uuid.uuid4())
    clean_uuid = random_uuid.replace('-', '')
    return clean_uuid[:length]

def print_separator():
    """Print a separator line for better readability."""
    print("\n" + "="*50 + "\n")

def verify_schema():
    """Verify the database schema."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("Tables in the database:")
        for table in tables:
            table_name = table[0]
            print(f"\n📋 Table: {table_name}")
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            print("Columns:")
            for column in columns:
                col_id, name, type_, not_null, default, pk = column
                primary_key = "🔑 " if pk else "   "
                print(f"{primary_key}{name} ({type_})")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
        return False

def test_insert():
    """Test inserting a user and account record."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Insert a test user
        uid = generate_uid(16)
        deriv_user_id = f"test{generate_uid(8)}"
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO users (
                uid, user_id, email, fullname, country, 
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            deriv_user_id,
            "test@example.com",
            "Test User",
            "US",
            current_time,
            current_time
        ))
        
        # Get the user ID
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (deriv_user_id,))
        user = cursor.fetchone()
        user_id = user[0]
        
        print(f"\n✅ Created test user with ID {user_id}")
        
        # Insert a test account
        account_uid = generate_uid(16)
        
        cursor.execute("""
            INSERT INTO accounts (
                uid, user_id, deriv_id, loginid,
                balance, currency, is_virtual,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            account_uid,
            user_id,
            deriv_user_id,
            "CR12345",
            "1000.00",
            "USD",
            "false",
            current_time,
            current_time
        ))
        
        # Get the account ID
        cursor.execute("SELECT id FROM accounts WHERE uid = ?", (account_uid,))
        account = cursor.fetchone()
        account_id = account[0]
        
        print(f"✅ Created test account with ID {account_id}")
        
        # Now test retrieving the data
        cursor.execute("""
            SELECT u.*, a.balance, a.currency 
            FROM users u
            JOIN accounts a ON u.id = a.user_id
            WHERE u.user_id = ?
        """, (deriv_user_id,))
        result = cursor.fetchone()
        
        if result:
            print("\n📝 Retrieved user data:")
            print(f"  User ID: {result['id']}")
            print(f"  Deriv User ID: {result['user_id']}")
            print(f"  Email: {result['email']}")
            print(f"  Balance: {result['balance']} {result['currency']}")
        
        # Commit changes
        conn.commit()
        
        # Clean up test data
        cursor.execute("DELETE FROM accounts WHERE uid = ?", (account_uid,))
        cursor.execute("DELETE FROM users WHERE uid = ?", (uid,))
        conn.commit()
        
        print("\n🧹 Cleaned up test data")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
        return False

def main():
    """Main function to run the database verification."""
    print("🔍 Starting database verification...")
    print_separator()
    
    schema_success = verify_schema()
    if schema_success:
        print_separator()
        print("✅ Database schema verification successful!")
    else:
        print("❌ Database schema verification failed.")
        return
    
    print_separator()
    print("🧪 Testing basic database operations...")
    insert_success = test_insert()
    
    if insert_success:
        print_separator()
        print("✅ Database operations test successful!")
    else:
        print("❌ Database operations test failed.")

if __name__ == "__main__":
    main() 