import sqlite3

db_name = "oauth.db"

conn = sqlite3.connect(db_name)

cursor = conn.cursor()
# uid, user_id, loginid, email, fullname, balance, country, currency, is_virtual, account_created, account_updated


cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    uid TEXT NOT NULL,
    session_token TEXT NOT NULL,
    user_id TEXT NOT NULL,
    loginid_accountid TEXT NOT NULL,
    password TEXT,
    email TEXT,
    phone TEXT,
    fullname TEXT,
    balance TEXT,
    country TEXT,
    country_code TEXT,
    currency TEXT,
    is_virtual TEXT,
    is_active TEXT,
    account_created TEXT,
    account_updated TEXT
)
""")

# Create index for faster lookups
cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON users(user_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_loginid ON users(loginid_accountid)")

conn.commit()

# mt5 account table
cursor.execute("""
CREATE TABLE IF NOT EXISTS mt5_accounts (
    user_id TEXT NOT NULL,
    mt5_login TEXT NOT NULL,
    mt5_balance TEXT NOT NULL,
    mt5_leverage TEXT NOT NULL,
    mt5_currency TEXT NOT NULL,
    mt5_group TEXT NOT NULL,
    mt5_server TEXT NOT NULL,
    account_created TEXT,
    account_updated TEXT
)
""")

# Create index for faster lookups
cursor.execute("CREATE INDEX IF NOT EXISTS idx_mt5_login ON mt5_accounts(mt5_login)")

conn.commit()

conn.close()

print("Database schema created successfully with MT5 fields added.")

