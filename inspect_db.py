import sqlite3
import os
from datetime import datetime

# Database file
DB_FILE = "der_volt.db"

def dict_factory(cursor, row):
    """Convert database row objects to dictionary."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def inspect_database():
    """Inspect the database structure and print out details"""
    if not os.path.exists(DB_FILE):
        print(f"Database file {DB_FILE} not found.")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"Found {len(tables)} tables in database:")
        for table in tables:
            table_name = table['name']
            print(f"\n=== TABLE: {table_name} ===")
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("Columns:")
            for col in columns:
                print(f"  - {col['name']} ({col['type']})")
            
            # Check row count
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            count = cursor.fetchone()['count']
            print(f"Row count: {count}")
            
            # Print sample data (first 3 rows) if table has data
            if count > 0 and table_name not in ['sqlite_sequence']:
                print("Sample data (first 3 rows):")
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                sample_data = cursor.fetchall()
                for row in sample_data:
                    print(f"  {row}")
        
        conn.close()
    except Exception as e:
        print(f"Error inspecting database: {e}")

def debug_save_user_attempt():
    """Test a simplified version of user save functionality"""
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        # Get users table schema
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        print("\n=== DEBUGGING USER SAVE OPERATION ===")
        print("Users table columns:")
        column_names = [col['name'] for col in columns]
        print(column_names)
        
        # Test a simplified insert
        uid = "test_" + datetime.now().strftime("%Y%m%d%H%M%S")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # Get required columns for insert
            required_fields = []
            for col in columns:
                if col['notnull'] == 1 and col['dflt_value'] is None and col['name'] != 'id':
                    required_fields.append(col['name'])
            
            print(f"Required fields: {required_fields}")
            
            # Build a dynamic query based on available columns
            insert_cols = ['uid', 'email', 'created_at', 'updated_at']
            
            # Add OAuth columns if they exist
            if 'is_oauth_user' in column_names:
                insert_cols.append('is_oauth_user')
            if 'oauth_provider' in column_names:
                insert_cols.append('oauth_provider')
            if 'user_id' in column_names:
                insert_cols.append('user_id')
            if 'is_active' in column_names:
                insert_cols.append('is_active')
            
            # Create placeholders
            placeholders = ', '.join(['?' for _ in insert_cols])
            cols_str = ', '.join(insert_cols)
            
            # Create values
            values = [uid, 'test@example.com', current_time, current_time]
            
            # Add values for OAuth columns
            if 'is_oauth_user' in column_names:
                values.append(1)
            if 'oauth_provider' in column_names:
                values.append('deriv')
            if 'user_id' in column_names:
                values.append('test_user_id')
            if 'is_active' in column_names:
                values.append(1)
            
            # Create and execute query
            query = f"INSERT INTO users ({cols_str}) VALUES ({placeholders})"
            print(f"Test query: {query}")
            print(f"Test values: {values}")
            
            cursor.execute(query, values)
            conn.commit()
            print("Test insert successful!")
        except sqlite3.Error as e:
            print(f"Test insert failed with SQLite error: {e}")
            
            # Try with minimal fields
            try:
                cursor.execute("""
                    INSERT INTO users (uid, email, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (uid, 'test@example.com', current_time, current_time))
                conn.commit()
                print("Minimal insert successful!")
            except sqlite3.Error as e2:
                print(f"Minimal insert failed with SQLite error: {e2}")
        
        conn.close()
    except Exception as e:
        print(f"Error in debug function: {e}")

if __name__ == "__main__":
    print("Starting database inspection...")
    inspect_database()
    debug_save_user_attempt()
    print("\nDatabase inspection completed.") 