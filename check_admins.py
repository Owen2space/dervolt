import sqlite3
import os

def check_admins():
    try:
        # Connect to the database
        db_path = os.path.join(os.path.dirname(__file__), 'der_volt.db')
        print(f"Using database at: {os.path.abspath(db_path)}")
        
        if not os.path.exists(db_path):
            print(f"Database file not found at {os.path.abspath(db_path)}!")
            return False
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # List all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Tables in the database:")
        for table in tables:
            print(f"- {table[0]}")
        
        # First check if the admins table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admins'")
        if cursor.fetchone() is None:
            print("\nThe 'admins' table does not exist in the database!")
            return False
        
        # Get schema of admins table
        cursor.execute("PRAGMA table_info(admins)")
        columns = cursor.fetchall()
        print("\nSchema of admins table:")
        for col in columns:
            print(f"- {col['name']} ({col['type']})")
            
        # Check if there are any admins
        cursor.execute("SELECT * FROM admins")
        admins = cursor.fetchall()
        
        if not admins:
            print("\nNo admin users found in the database!")
            return False
        
        print(f"\nFound {len(admins)} admin users:")
        for admin in admins:
            admin_dict = dict(admin)
            print(f"- Username: {admin_dict.get('username', 'N/A')}")
            print(f"  Email: {admin_dict.get('email', 'N/A')}")
            print(f"  Role: {admin_dict.get('role', 'N/A')}")
            print(f"  Available columns: {', '.join(admin_dict.keys())}")
            print("-----------------------------")
        
        conn.close()
        return True
    except Exception as e:
        print(f"Error checking admins: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_admins() 