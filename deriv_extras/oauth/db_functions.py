import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import uuid
import os

# Use the main application's database
from config import db_name
DB_NAME =  db_name

def generate_uid(length=12):
    """
    Generate a unique identifier with the specified length.
    
    Args:
        length: Length of the UID to generate (default: 12)
        
    Returns:
        A string containing a random UUID truncated to the specified length
    """
    # Generate a random UUID and convert to string
    random_uuid = str(uuid.uuid4())
    
    # Remove hyphens and truncate to desired length
    clean_uuid = random_uuid.replace('-', '')
    return clean_uuid[:length]

def dict_factory(cursor, row):
    """Convert database row objects to dictionary."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(DB_NAME)
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    # Return row objects as dictionaries
    conn.row_factory = dict_factory
    return conn

def save_user_info_1(user_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Save or update user information in the database
    
    Args:
        user_data: Dictionary containing user information
        
    Returns:
        Tuple of (success_bool, message)
    """
    try:
        # Extract data from the user_data JSON
        authorize_data = user_data.get('authorize', {})
        user_id = authorize_data.get('user_id')
        
        if not user_id:
            return False, "User ID not found in the data"
            
        account_list = authorize_data.get('account_list', [])
        if not account_list:
            return False, "No accounts found for user"
        
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Process each account in the list
        for account in account_list:
            loginid = account.get('loginid')
            email = authorize_data.get('email', '')
            fullname = authorize_data.get('fullname', '')
            balance = account.get('balance', '0')
            country = authorize_data.get('country', '')
            currency = account.get('currency', '')
            is_virtual = str(account.get('is_virtual', False))
            
            # Check if user account exists
            cursor.execute("SELECT * FROM users WHERE user_id = ? AND loginid_accountid = ?", 
                           (user_id, loginid))
            existing_user = cursor.fetchone()
            
            if existing_user:
                # Update existing user
                cursor.execute("""
                    UPDATE users 
                    SET email = ?, fullname = ?, balance = ?, country = ?, 
                        currency = ?, is_vitual = ?, account_updated = ?
                    WHERE user_id = ? AND loginid_accountid = ?
                """, (email, fullname, balance, country, currency, 
                     is_virtual, current_time, user_id, loginid))
            else:
                # Insert new user
                # Generate a unique ID for the record using the generate_uid function
                uid = generate_uid(16)
                cursor.execute("""
                    INSERT INTO users 
                    (uid, user_id, loginid_accountid, email, fullname, balance, country, 
                     currency, is_vitual, account_created, account_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (uid, user_id, loginid, email, fullname, balance, country, 
                     currency, is_virtual, current_time, current_time))
        
        conn.commit()
        conn.close()
        return True, "User information saved successfully", user_id
        
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}", None
    except Exception as e:
        return False, f"Error saving user data: {str(e)}", None


def save_user_info(user_data: Dict[str, Any]) -> Tuple[bool, str, int]:
    try:
        # Extract data from the user_data JSON
        authorize_data = user_data.get('authorize', {})
        deriv_user_id = authorize_data.get('user_id')
        
        if not deriv_user_id:
            return False, "User ID not found in the data", None
            
        account_list = authorize_data.get('account_list', [])
        if not account_list:
            return False, "No accounts found for user", None
        
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get actual column names from the users table
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col['name'] for col in columns]
        
        print(f"Found columns in users table: {column_names}")
        
        # Get column names from the accounts table
        cursor.execute("PRAGMA table_info(accounts)")
        account_columns = cursor.fetchall()
        account_column_names = [col['name'] for col in account_columns]
        
        print(f"Found columns in accounts table: {account_column_names}")
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (deriv_user_id,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"Found existing user: {existing_user['id']}")
            # Update existing user with only the columns that exist
            update_fields = []
            params = []
            
            # Always update these basic fields
            if 'email' in column_names:
                update_fields.append("email = ?")
                params.append(authorize_data.get('email', ''))
                
            if 'fullname' in column_names:
                update_fields.append("fullname = ?")
                params.append(authorize_data.get('fullname', ''))
                
            if 'country' in column_names:
                update_fields.append("country = ?")
                params.append(authorize_data.get('country', ''))
                
            if 'updated_at' in column_names:
                update_fields.append("updated_at = ?")
                params.append(current_time)
            
            # Add OAuth-specific fields if they exist
            if 'is_oauth_user' in column_names:
                update_fields.append("is_oauth_user = ?")
                params.append(1)
                
            if 'oauth_provider' in column_names:
                update_fields.append("oauth_provider = ?")
                params.append('deriv')
            
            # Add the user ID as the last parameter for the WHERE clause
            params.append(existing_user['user_id'])
            
            update_query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = ?"
            print(f"Executing update query: {update_query} with params: {params}")
            
            cursor.execute(update_query, params)
            
            user_id = existing_user['user_id']
            uid = existing_user['uid']
        else:
            print(f"Creating new user for Deriv ID: {deriv_user_id}")
            # Insert new user with only the columns that exist
            uid = generate_uid(16)
            
            insert_fields = ["uid"]
            insert_values = [uid]
            
            # Always include user_id
            if 'user_id' in column_names:
                insert_fields.append("user_id")
                insert_values.append(deriv_user_id)
            
            # Basic user fields
            if 'email' in column_names:
                insert_fields.append("email")
                insert_values.append(authorize_data.get('email', ''))
                
            if 'fullname' in column_names:
                insert_fields.append("fullname")
                insert_values.append(authorize_data.get('fullname', ''))
                
            if 'country' in column_names:
                insert_fields.append("country")
                insert_values.append(authorize_data.get('country', ''))
                
            if 'created_at' in column_names:
                insert_fields.append("created_at")
                insert_values.append(current_time)
                
            if 'updated_at' in column_names:
                insert_fields.append("updated_at")
                insert_values.append(current_time)
                
            if 'is_active' in column_names:
                insert_fields.append("is_active")
                insert_values.append(1)
            
            # OAuth specific fields
            if 'is_oauth_user' in column_names:
                insert_fields.append("is_oauth_user")
                insert_values.append(1)
                
            if 'oauth_provider' in column_names:
                insert_fields.append("oauth_provider")
                insert_values.append('deriv')
            
            # Create placeholders for the SQL query
            placeholders = ", ".join(["?"] * len(insert_values))
            insert_query = f"INSERT INTO users ({', '.join(insert_fields)}) VALUES ({placeholders})"
            
            print(f"Executing insert query: {insert_query} with values: {insert_values}")
            
            cursor.execute(insert_query, insert_values)
            
            # Get the id of the newly inserted user
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (deriv_user_id,))
            user = cursor.fetchone()
            if user:
                user_id = user['user_id']
            else:
                return False, "Failed to retrieve user ID after insert", None
        
        # Process accounts
        print(f"Processing {len(account_list)} accounts for user ID: {user_id}")
        for account in account_list:
            loginid = account.get('loginid')
            
            # Check if account exists
            cursor.execute("""
                SELECT * FROM accounts 
                WHERE user_id = ? AND loginid_accountid = ?
            """, (user_id, loginid))
            
            existing_account = cursor.fetchone()
            
            if existing_account:
                # Update existing account
                print(f"Updating existing account: {loginid}")
                
                # Build dynamic update query
                update_fields = []
                update_values = []
                
                if 'balance' in account_column_names:
                    update_fields.append("balance = ?")
                    update_values.append(account.get('balance', '0'))
                
                if 'currency' in account_column_names:
                    update_fields.append("currency = ?")
                    update_values.append(account.get('currency', ''))
                
                if 'is_virtual' in account_column_names:
                    update_fields.append("is_virtual = ?")
                    update_values.append(str(account.get('is_virtual', False)))
                
                if 'updated_at' in account_column_names:
                    update_fields.append("updated_at = ?")
                    update_values.append(current_time)
                
                # Add the account ID for the WHERE clause
                update_values.append(existing_account['id'])
                
                if update_fields:
                    update_query = f"UPDATE accounts SET {', '.join(update_fields)} WHERE id = ?"
                    print(f"Executing account update query: {update_query}")
                    cursor.execute(update_query, update_values)
            else:
                # Insert new account
                print(f"Creating new account: {loginid}")
                account_uid = generate_uid(16)
                account_number = f"DR{generate_uid(10)}"
                
                # Build dynamic insert query
                insert_fields = []
                insert_values = []
                
                # Required fields
                if 'uid' in account_column_names:
                    insert_fields.append('uid')
                    insert_values.append(account_uid)
                
                if 'user_id' in account_column_names:
                    insert_fields.append('user_id')
                    insert_values.append(user_id)
                
                if 'deriv_id' in account_column_names:
                    insert_fields.append('deriv_id')
                    insert_values.append(deriv_user_id)
                
                if 'loginid' in account_column_names:
                    insert_fields.append('loginid')
                    insert_values.append(loginid)
                
                # Optional fields that were causing issues
                if 'account_number' in account_column_names:
                    insert_fields.append('account_number')
                    insert_values.append(account_number)
                
                if 'account_name' in account_column_names:
                    insert_fields.append('account_name')
                    insert_values.append(f"Deriv {loginid}")
                
                if 'account_type' in account_column_names:
                    insert_fields.append('account_type')
                    insert_values.append("deriv")
                
                # Basic account details
                if 'balance' in account_column_names:
                    insert_fields.append('balance')
                    insert_values.append(account.get('balance', '0'))
                
                if 'currency' in account_column_names:
                    insert_fields.append('currency')
                    insert_values.append(account.get('currency', ''))
                
                if 'is_virtual' in account_column_names:
                    insert_fields.append('is_virtual')
                    insert_values.append(str(account.get('is_virtual', False)))
                
                if 'status' in account_column_names:
                    insert_fields.append('status')
                    insert_values.append("active")
                
                if 'is_active' in account_column_names:
                    insert_fields.append('is_active')
                    insert_values.append(1)
                
                if 'created_at' in account_column_names:
                    insert_fields.append('created_at')
                    insert_values.append(current_time)
                
                if 'updated_at' in account_column_names:
                    insert_fields.append('updated_at')
                    insert_values.append(current_time)
                
                # Create placeholders for the SQL query
                placeholders = ", ".join(["?"] * len(insert_values))
                insert_query = f"INSERT INTO accounts ({', '.join(insert_fields)}) VALUES ({placeholders})"
                
                print(f"Executing account insert query: {insert_query}")
                cursor.execute(insert_query, insert_values)
        
        conn.commit()
        conn.close()
        print(f"User saved successfully with ID: {user_id}")
        return True, "User saved successfully", user_id
        
    except sqlite3.Error as e:
        print(f"SQLite error in save_user_info: {e}")
        return False, f"Database error: {str(e)}", None
    except Exception as e:
        print(f"Unexpected error in save_user_info: {e}")
        return False, f"Error saving user data: {str(e)}", None

def get_user_by_id(user_id: str) -> Optional[Dict]:
    """
    Retrieve user information from the database by Deriv user_id
    
    Args:
        user_id: The Deriv user ID to look up
        
    Returns:
        Dictionary with user information or None if not found
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists in main users table
        cursor.execute("SELECT * FROM users WHERE loginid_accountid = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return None
            
        # Get all accounts for this user
        cursor.execute("SELECT * FROM accounts WHERE user_id = ?", (user['id'],))
        accounts = cursor.fetchall()
        
        # Add accounts to user data
        user_data = dict(user)
        user_data['accounts'] = accounts
        
        conn.close()
        return user_data
        
    except sqlite3.Error as e:
        print(f"Database error in get_user_by_id: {e}")
        return None
    except Exception as e:
        print(f"Error in get_user_by_id: {e}")
        return None


def get_user_by_id_1(user_id: str) -> Optional[Dict]:
    """
    Retrieve user information from the database by user_id
    
    Args:
        user_id: The user ID to look up
        
    Returns:
        Dictionary with user information or None if not found
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        accounts = cursor.fetchall()
        
        if not accounts:
            return None
            
        # Convert accounts to dictionary format
        user_accounts = [dict(account) for account in accounts]
        conn.close()
        
        return {"user_id": user_id, "accounts": user_accounts}
        
    except sqlite3.Error:
        return None