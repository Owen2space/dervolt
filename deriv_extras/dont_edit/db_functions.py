import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import uuid
import os

from deriv_functions import get_account_settings
from config import db_name, app_id
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

def save_user_info(user_data: Dict[str, Any], session_token: str) -> Tuple[bool, str]:
    try:
        # Extract data from the user_data JSON
        authorize_data = user_data.get('authorize', {})
        user_id = authorize_data.get('user_id')
        
        if not user_id:
            return False, "User ID not found in the data"
        
        # print("authorize_data", json.dumps(authorize_data))
        
            
        actual_account_id = authorize_data.get('loginid')
        # print("actual_account_id", actual_account_id)


        account_list = authorize_data.get('account_list', [])
        if not account_list:
            return False, "No accounts found for user"
        
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        account_id_temp = None
        
        # Process each account in the list
        for account in account_list:
            loginid = account.get('loginid')
            email = authorize_data.get('email', '')
            fullname = authorize_data.get('fullname', '')
            balance = account.get('balance', '0')
            country = authorize_data.get('country', '')
            currency = account.get('currency', '')
            is_virtual = str(account.get('is_virtual', False))

            # print(is_virtual)

            if str(is_virtual) == "1":
                continue

            account_id_temp = loginid
            account_settings = get_account_settings(session_token)
            account_settings = json.loads(account_settings[1])
            
            country_code = account_settings.get('get_settings').get('calling_country_code')
            phone_number = account_settings.get('get_settings').get('phone')

            
            # Check if user account exists
            cursor.execute("SELECT * FROM users WHERE user_id = ? AND loginid_accountid = ?", 
                           (user_id, loginid))
            existing_user = cursor.fetchone()
            
            if existing_user:
                # Update existing user
                cursor.execute("""
                    UPDATE users 
                    SET session_token = ?, email = ?, phone = ?, fullname = ?, balance = ?, country = ?, country_code = ?, 
                        currency = ?, is_vitual = ?, account_updated = ?
                    WHERE user_id = ? AND loginid_accountid = ?
                """, (session_token, email, phone_number, fullname, balance, country, country_code, currency, 
                     is_virtual, current_time, user_id, loginid))
            else:
                # Insert new user
                # Generate a unique ID for the record using the generate_uid function
                uid = generate_uid(16)
                cursor.execute("""
                    INSERT INTO users 
                    (uid, session_token, user_id, loginid_accountid, email, phone, fullname, balance, country, country_code,
                     currency, is_vitual, account_created, account_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (uid, session_token, user_id, loginid, email, phone_number, fullname, balance, country, country_code,
                     currency, is_virtual, current_time, current_time))
        
        conn.commit()
        conn.close()
        return True, "User information saved successfully", account_id_temp
        
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}", None
    except Exception as e:
        return False, f"Error saving user data: {str(e)}", None

def get_user_by_id(user_id: str) -> Optional[Dict]:
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