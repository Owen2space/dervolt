import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List
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

def save_user_info(user_data: Dict[str, Any], session_token: str) -> Tuple[bool, str, Optional[str]]:
    try:
        # Extract data from the user_data JSON
        authorize_data = user_data.get('authorize', {})
        user_id = authorize_data.get('user_id')
        
        if not user_id:
            return False, "User ID not found in the data", None
        
        # print("authorize_data", json.dumps(authorize_data))
        
            
        actual_account_id = authorize_data.get('loginid')
        # print("actual_account_id", actual_account_id)


        account_list = authorize_data.get('account_list', [])
        if not account_list:
            return False, "No accounts found for user", None
        
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
            # Default values for new fields
            password = None
            is_active = "0"  # Set as active by default
            
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
                # Update existing user but preserve password and is_active values
                cursor.execute("""
                    UPDATE users 
                    SET session_token = ?, email = ?, phone = ?, fullname = ?, balance = ?, country = ?, country_code = ?, 
                        currency = ?, is_virtual = ?, account_updated = ?
                    WHERE user_id = ? AND loginid_accountid = ?
                """, (session_token, email, phone_number, fullname, balance, country, country_code, currency, 
                     is_virtual, current_time, user_id, loginid))
            else:
                # Insert new user with default password and is_active values
                # Generate a unique ID for the record using the generate_uid function
                uid = generate_uid(16)
                cursor.execute("""
                    INSERT INTO users 
                    (uid, session_token, user_id, loginid_accountid, email, phone, fullname, balance, country, country_code,
                     currency, is_virtual, password, is_active, account_created, account_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (uid, session_token, user_id, loginid, email, phone_number, fullname, balance, country, country_code,
                     currency, is_virtual, password, is_active, current_time, current_time))
        
        conn.commit()
        conn.close()
        return True, "User information saved successfully", account_id_temp
        
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}", None
    except Exception as e:
        return False, f"Error saving user data: {str(e)}", None
    
def save_mt5_info(user_id: str, mt5_accounts_info):
    """
    Save MT5 account information for a user to the mt5_accounts table.
    Only saves real accounts (filters out demo accounts).
    
    Args:
        user_id: The user's account ID
        mt5_accounts_info: List of MT5 account information dictionaries
        
    Returns:
        A tuple containing (success: bool, message: str)
    """
    try:
        # Filter out demo accounts, keep only real accounts
        real_mt5_accounts = [account for account in mt5_accounts_info if account.get('type', '').lower() == 'real']
        
        if not real_mt5_accounts:
            return True, "No real MT5 accounts to save"
            
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # For each MT5 account, insert or update the record in the mt5_accounts table
        for mt5_account in real_mt5_accounts:
            mt5_login = mt5_account.get('login', '')
            mt5_balance = str(mt5_account.get('balance', '0'))
            mt5_leverage = str(mt5_account.get('leverage', '0'))
            mt5_currency = mt5_account.get('currency', 'USD')
            mt5_group = mt5_account.get('group', '')
            mt5_server = mt5_account.get('server', '')
            
            # Check if this MT5 login already exists for ANY user 
            # (ensures mt5_login is treated as unique)
            cursor.execute("""
                SELECT * FROM mt5_accounts 
                WHERE mt5_login = ?
            """, (mt5_login,))
            
            existing_account = cursor.fetchone()
            
            if existing_account:
                # Update existing MT5 account record
                cursor.execute("""
                    UPDATE mt5_accounts
                    SET user_id = ?, mt5_balance = ?, mt5_leverage = ?, mt5_currency = ?,
                        mt5_group = ?, mt5_server = ?, account_updated = ?
                    WHERE mt5_login = ?
                """, (user_id, mt5_balance, mt5_leverage, mt5_currency, mt5_group, 
                      mt5_server, current_time, mt5_login))
            else:
                # Insert new MT5 account record
                cursor.execute("""
                    INSERT INTO mt5_accounts
                    (user_id, mt5_login, mt5_balance, mt5_leverage, mt5_currency,
                     mt5_group, mt5_server, account_created, account_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, mt5_login, mt5_balance, mt5_leverage, mt5_currency,
                      mt5_group, mt5_server, current_time, current_time))
                
        conn.commit()
        conn.close()
        return True, "MT5 account information saved successfully"
        
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Error saving MT5 data: {str(e)}"

def get_user_by_id(user_id: str) -> Optional[Dict]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE loginid_accountid = ?", (user_id,))
        accounts = cursor.fetchall()
        
        if not accounts:
            return None
            
        return accounts
        
    except sqlite3.Error:
        return None

def get_user_by_email(email: str) -> Optional[Dict]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        accounts = cursor.fetchall()
        
        if not accounts:
            return None
            
        return accounts
        
    except sqlite3.Error:
        return None


def set_user_password(user_id: str, password: str) -> Tuple[bool, str]:
    """
    Update a user's password and set their account to active.
    
    Args:
        user_id: The user's ID
        password: The password to set
        
    Returns:
        A tuple containing (success: bool, message: str)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE loginid_accountid = ?", (user_id,))
        existing_user = cursor.fetchone()
        
        if not existing_user:
            conn.close()
            return False, f"User with ID {user_id} not found"
        
        # Update password and set account as active
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE users
            SET password = ?, is_active = ?, account_updated = ?
            WHERE loginid_accountid = ?
        """, (password, "1", current_time, user_id))
        
        conn.commit()
        conn.close()
        
        return True, "Password updated successfully"
        
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Error updating password: {str(e)}"