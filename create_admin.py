import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

def create_admin_user(username, email, password, role='admin'):
    """Create an admin user in the database"""
    try:
        # Connect to the database
        db_path = os.path.join(os.path.dirname(__file__), 'der_volt.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the admin already exists
        cursor.execute("SELECT COUNT(*) FROM admins WHERE username = ? OR email = ?", (username, email))
        count = cursor.fetchone()[0]
        
        if count > 0:
            print("Admin with this username or email already exists!")
            return False
        
        # Get more detailed schema to see all constraints
        cursor.execute("PRAGMA table_info(admins)")
        columns = cursor.fetchall()
        print("Schema of admins table with constraints:")
        for col in columns:
            # PRAGMA returns: (cid, name, type, notnull, dflt_value, pk)
            name = col[1]
            type_ = col[2]
            notnull = col[3]
            print(f"- {name} ({type_}) {'NOT NULL' if notnull else ''}")
        
        # Create admin user with timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build the query dynamically based on the schema
        fields = []
        parameters = []
        
        # Always include the core fields
        fields.extend(['username', 'email', 'password', 'role'])
        parameters.extend([username, email, generate_password_hash(password), role])
        
        # Add timestamps if they're in the schema
        column_names = [col[1] for col in columns]
        
        if 'created_at' in column_names:
            fields.append('created_at')
            parameters.append(now)
            
        if 'updated_at' in column_names:
            fields.append('updated_at')
            parameters.append(now)
            
        # Add is_active if it's in the schema
        if 'is_active' in column_names:
            fields.append('is_active')
            parameters.append(1)  # 1 = active
            
        # Generate the SQL query
        field_list = ', '.join(fields)
        placeholder_list = ', '.join(['?' for _ in parameters])
        query = f"INSERT INTO admins ({field_list}) VALUES ({placeholder_list})"
        
        print(f"Executing query: {query}")
        print(f"With parameters: {parameters}")
        
        cursor.execute(query, parameters)
        
        # Commit the changes and close the connection
        conn.commit()
        conn.close()
        
        print(f"Admin user '{username}' created successfully!")
        print(f"You can now log in at /admin/login with username: {username}")
        return True
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Get input from the user
    print("Create Admin User")
    print("-----------------")
    username = input("Enter admin username: ")
    email = input("Enter admin email: ")
    password = input("Enter admin password (min 8 characters): ")
    role = input("Enter role (admin or super_admin, default is admin): ") or "admin"
    
    if len(password) < 8:
        print("Password must be at least 8 characters long!")
    else:
        create_admin_user(username, email, password, role) 