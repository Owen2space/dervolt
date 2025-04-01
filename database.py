import sqlite3
import os
import traceback
from contextlib import contextmanager
from datetime import datetime

DATABASE_URL = "der_volt.db"

def create_tables():
    """Create all required tables if they don't exist."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                phone_number TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')
            
            # Create accounts table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_number TEXT UNIQUE NOT NULL,
                account_name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
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
            if cursor.fetchone()[0] == 0:
                # Insert default value until API provides real rate
                cursor.execute('''
                    INSERT INTO forex_rates (currency, rate, updated_at)
                    VALUES (?, ?, ?)
                ''', ('USD/KES', 130.0, datetime.now()))
                print("Added initial USD/KES forex rate")
            
            conn.commit()
            print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")
        traceback.print_exc()

@contextmanager
def get_db():
    """Context manager for database connections"""
    # Use the database file directly in the backend directory
    db_path = os.path.join(os.path.dirname(__file__), 'der_volt.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def dict_factory(cursor, row):
    """Convert database rows to dictionaries"""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

def get_db_connection():
    """Get a database connection with dictionary row factory"""
    db_path = os.path.join(os.path.dirname(__file__), 'der_volt.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory
    return conn

def init_db():
    """Initialize the database and create tables."""
    try:
        create_tables()
        
        # Add any additional columns needed
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Check if preferred_payment_method column exists in users table
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'preferred_payment_method' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN preferred_payment_method TEXT DEFAULT 'mpesa'")
                print("Added preferred_payment_method column to users table")
            
            # Check if is_default column exists in accounts table
            cursor.execute("PRAGMA table_info(accounts)")
            account_columns = [column[1] for column in cursor.fetchall()]
            
            if 'is_default' not in account_columns:
                cursor.execute("ALTER TABLE accounts ADD COLUMN is_default INTEGER DEFAULT 0")
                print("Added is_default column to accounts table")
                
                # Set the first account for each user as default
                cursor.execute("""
                    WITH RankedAccounts AS (
                        SELECT id, user_id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY id) as rn
                        FROM accounts
                    )
                    UPDATE accounts SET is_default = 1
                    WHERE id IN (SELECT id FROM RankedAccounts WHERE rn = 1)
                """)
                print("Set default accounts for each user")
            
            # Check if blocked_reason and blocked_at columns exist in users table
            if 'blocked_reason' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN blocked_reason TEXT")
                print("Added blocked_reason column to users table")
            
            if 'blocked_at' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN blocked_at TEXT")
                print("Added blocked_at column to users table")
                
            # Check if is_active column exists in users table
            if 'is_active' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
                print("Added is_active column to users table")
                
            # Check if password_reset_required column exists in users table
            if 'password_reset_required' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN password_reset_required INTEGER DEFAULT 0")
                print("Added password_reset_required column to users table")
            
            # Check if details column exists in user_activity_logs table
            cursor.execute("PRAGMA table_info(user_activity_logs)")
            activity_log_columns = [column[1] for column in cursor.fetchall()]
            
            if 'details' not in activity_log_columns:
                cursor.execute("ALTER TABLE user_activity_logs ADD COLUMN details TEXT")
                print("Added details column to user_activity_logs table")
            
            # Check if metadata column exists in transactions table
            cursor.execute("PRAGMA table_info(transactions)")
            transaction_columns = [column[1] for column in cursor.fetchall()]
            
            if 'metadata' not in transaction_columns:
                cursor.execute("ALTER TABLE transactions ADD COLUMN metadata TEXT")
                print("Added metadata column to transactions table")
                
            # Check if user_id column exists in transactions table
            if 'user_id' not in transaction_columns:
                cursor.execute("ALTER TABLE transactions ADD COLUMN user_id INTEGER")
                print("Added user_id column to transactions table")
                
                # Populate user_id column based on account_id
                cursor.execute("""
                    UPDATE transactions 
                    SET user_id = (
                        SELECT user_id FROM accounts 
                        WHERE accounts.id = transactions.account_id
                    )
                """)
                print("Populated user_id column in transactions table")
            
            conn.commit()
        
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        traceback.print_exc()

#initialize the database
if __name__ == "__main__":
    init_db()
