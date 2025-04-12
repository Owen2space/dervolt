import sqlite3
import json

def dict_factory(cursor, row):
    """Convert database row objects to dictionary."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def get_database_data():
    """
    Get user and MT5 account data from the database and return as JSON.
    
    Returns:
        dict: A dictionary with database contents in JSON format
    """
    result = {
        "success": False,
        "message": "",
        "user_count": 0,
        "users": []
    }
    
    try:
        # Connect to the database
        conn = sqlite3.connect("oauth.db")
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        # Query user data
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        
        if not users:
            result["message"] = "No users found in the database."
            result["success"] = True  # Still a successful query, just empty
            return result
        
        result["user_count"] = len(users)
        
        # Format user information
        for user in users:
            user_data = {
                "user_id": user.get('loginid_accountid'),
                "full_name": user.get('fullname'),
                "email": user.get('email'),
                "is_virtual": user.get('is_vitual'),
                "balance": user.get('balance'),
                "currency": user.get('currency'),
                "country": user.get('country'),
                "mt5_account": None
            }
            
            # Add MT5 account information if available
            mt5_login = user.get('mt5_login')
            if mt5_login:
                user_data["mt5_account"] = {
                    "login": mt5_login,
                    "balance": user.get('mt5_balance'),
                    "leverage": user.get('mt5_leverage'),
                    "type": user.get('mt5_type'),
                    "group": user.get('mt5_group'),
                    "server": user.get('mt5_server')
                }
                
            result["users"].append(user_data)
        
        conn.close()
        result["success"] = True
        result["message"] = "Data retrieved successfully"
        
    except sqlite3.Error as e:
        result["message"] = f"Database error: {e}"
    except Exception as e:
        result["message"] = f"Error: {e}"
        
    return result

if __name__ == "__main__":
    # When run directly, get data and print as JSON
    db_data = get_database_data()
    print(json.dumps(db_data, indent=2)) 