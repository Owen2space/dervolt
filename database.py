import sqlite3
import os
import traceback
from contextlib import contextmanager
from datetime import datetime
import uuid

DATABASE_URL = "der_volt.db"

def generate_uid(length=16):
    """
    Generate a unique identifier with the specified length.
    
    Args:
        length: Length of the UID to generate (default: 16)
        
    Returns:
        A string containing a random UUID truncated to the specified length
    """
    # Generate a random UUID and convert to string
    random_uuid = str(uuid.uuid4())
    
    # Remove hyphens and truncate to desired length
    clean_uuid = random_uuid.replace('-', '')
    return clean_uuid[:length]

def create_tables():
    """Create all required tables if they don't exist."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Create users table - both standard and Deriv OAuth users
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT UNIQUE,
                user_id TEXT UNIQUE,
                first_name TEXT,
                last_name TEXT,
                fullname TEXT,
                email TEXT UNIQUE,
                password_hash TEXT,
                phone_number TEXT,
                country TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                oauth_provider TEXT,
                is_oauth_user INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                blocked_reason TEXT,
                blocked_at TEXT
            )
            ''')
            
            # Create accounts table - standard accounts
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT UNIQUE,
                user_id INTEGER,
                deriv_id TEXT,
                account_number TEXT UNIQUE,
                loginid TEXT,
                account_name TEXT,
                account_type TEXT,
                currency TEXT,
                balance TEXT,
                is_virtual TEXT,
                status TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Create transactions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                payment_method TEXT,
                description TEXT,
                reference TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
            ''')
            
            # Create notifications table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Create withdrawal_otps table for large withdrawal verification
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawal_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                otp TEXT NOT NULL,
                amount REAL NOT NULL,
                account_id INTEGER NOT NULL,
                used INTEGER DEFAULT 0,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
            ''')
            
            # Create password_reset_otps table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_reset_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                otp TEXT NOT NULL,
                is_used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')
            
            # Create password_change_otps table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_change_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                otp TEXT NOT NULL,
                is_used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Create admins table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                permissions TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                last_login TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')
            
            # Create admin_logs table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (admin_id) REFERENCES admins (id)
            )
            ''')
            
            # Create system_settings table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')
            
            # Create broadcasts table for system-wide messages
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL,
                scheduled_at TEXT,
                is_sent INTEGER DEFAULT 0,
                sent_at TEXT,
                FOREIGN KEY (admin_id) REFERENCES admins (id)
            )
            ''')
            
            # Create email_logs table for tracking emails sent
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT,
                status TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL
            )
            ''')
            
            # Create user_activity_logs table for tracking user logins and actions
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Create error_logs table for system errors
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                stack_trace TEXT,
                url TEXT,
                method TEXT,
                user_id INTEGER,
                ip_address TEXT,
                user_agent TEXT,
                severity TEXT NOT NULL,
                is_resolved INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            
            # Create security_logs table for suspicious activities
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                user_id INTEGER,
                admin_id INTEGER,
                threat_level TEXT NOT NULL,
                is_resolved INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (admin_id) REFERENCES admins (id)
            )
            ''')
            
            # Create forex_rates table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS forex_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                currency TEXT UNIQUE,
                rate REAL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Check if we need to insert initial forex rate
            cursor.execute("SELECT COUNT(*) FROM forex_rates WHERE currency='USD/KES'")
            count_result = cursor.fetchone()
            if count_result['COUNT(*)'] == 0:
                # Insert default value until API provides real rate
                cursor.execute('''
                    INSERT INTO forex_rates (currency, rate, updated_at)
                    VALUES (?, ?, ?)
                ''', ('USD/KES', 130.0, datetime.now()))
                print("Added initial USD/KES forex rate")
            
            # Create indexes for deriv tables
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_deriv_user_id ON users(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_deriv_id ON accounts(deriv_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_loginid ON accounts(loginid)")
            
            conn.commit()
            print("Database tables created successfully")
            return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        traceback.print_exc()
        return False

@contextmanager
def get_db():
    """Get database connection with context manager."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    finally:
        if conn:
            conn.close()

def dict_factory(cursor, row):
    """Convert database row objects to dictionary."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialize the database."""
    if not os.path.exists(DATABASE_URL):
        # Create database if it doesn't exist
        conn = sqlite3.connect(DATABASE_URL)
        conn.close()
        print(f"Created database: {DATABASE_URL}")
    
    success = create_tables()
    return success

# Helper functions for Deriv OAuth integration

def get_deriv_user_by_id(deriv_user_id):
    """
    Get a user by their Deriv user ID.
    
    Args:
        deriv_user_id: The Deriv user ID to look up
        
    Returns:
        User data dictionary or None if not found
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (deriv_user_id,))
            user = cursor.fetchone()
            
            if not user:
                return None
                
            # Get all accounts for this user
            cursor.execute("SELECT * FROM accounts WHERE user_id = ?", (user['id'],))
            accounts = cursor.fetchall()
            
            # Add accounts to user data
            user['accounts'] = accounts
            
            return user
            
    except Exception as e:
        print(f"Error getting Deriv user: {e}")
        return None

def save_deriv_user(user_data):
    """
    Save a Deriv user to the database.
    
    Args:
        user_data: Dictionary containing user data from Deriv API
        
    Returns:
        Tuple of (success: bool, user_id: int or None, message: str)
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Extract data
            authorize_data = user_data.get('authorize', {})
            deriv_user_id = authorize_data.get('user_id')
            
            if not deriv_user_id:
                return False, None, "User ID not found in data"
                
            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (deriv_user_id,))
            existing_user = cursor.fetchone()
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if existing_user:
                # Update existing user
                cursor.execute("""
                    UPDATE users SET 
                    email = ?, 
                    fullname = ?, 
                    country = ?,
                    updated_at = ?,
                    is_oauth_user = 1,
                    oauth_provider = 'deriv'
                    WHERE id = ?
                """, (
                    authorize_data.get('email', ''),
                    authorize_data.get('fullname', ''),
                    authorize_data.get('country', ''),
                    current_time,
                    existing_user['id']
                ))
                
                user_id = existing_user['id']
                uid = existing_user['uid']
            else:
                # Insert new user
                uid = generate_uid(16)
                cursor.execute("""
                    INSERT INTO users (
                        uid, user_id, email, fullname, country, 
                        created_at, updated_at, is_oauth_user, oauth_provider
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'deriv')
                """, (
                    uid,
                    deriv_user_id,
                    authorize_data.get('email', ''),
                    authorize_data.get('fullname', ''),
                    authorize_data.get('country', ''),
                    current_time,
                    current_time
                ))
                
                # Get the id of the newly inserted user
                cursor.execute("SELECT id FROM users WHERE user_id = ?", (deriv_user_id,))
                user = cursor.fetchone()
                if user:
                    user_id = user['id']
                else:
                    return False, None, "Failed to retrieve user ID after insert"
            
            # Process accounts
            account_list = authorize_data.get('account_list', [])
            for account in account_list:
                loginid = account.get('loginid')
                
                # Check if account exists
                cursor.execute("""
                    SELECT * FROM accounts 
                    WHERE user_id = ? AND loginid = ?
                """, (user_id, loginid))
                
                existing_account = cursor.fetchone()
                
                if existing_account:
                    # Update existing account
                    cursor.execute("""
                        UPDATE accounts SET
                        balance = ?,
                        currency = ?,
                        is_virtual = ?,
                        updated_at = ?
                        WHERE id = ?
                    """, (
                        account.get('balance', '0'),
                        account.get('currency', ''),
                        str(account.get('is_virtual', False)),
                        current_time,
                        existing_account['id']
                    ))
                else:
                    # Insert new account
                    account_uid = generate_uid(16)
                    account_number = f"DR{generate_uid(10)}"
                    
                    cursor.execute("""
                        INSERT INTO accounts (
                            uid, user_id, deriv_id, loginid,
                            account_number, account_name, account_type,
                            balance, currency, is_virtual,
                            status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        account_uid,
                        user_id,
                        deriv_user_id,
                        loginid,
                        account_number,
                        f"Deriv {loginid}",
                        "deriv",
                        account.get('balance', '0'),
                        account.get('currency', ''),
                        str(account.get('is_virtual', False)),
                        "active",
                        current_time,
                        current_time
                    ))
            
            conn.commit()
            return True, user_id, "User saved successfully"
            
    except Exception as e:
        print(f"Error saving Deriv user: {e}")
        traceback.print_exc()
        return False, None, str(e)

#initialize the database
if __name__ == "__main__":
    init_db()
