import sqlite3

db_name = "oauth.db"

conn = sqlite3.connect(db_name)

cursor = conn.cursor()
# uid, user_id, loginid, email, fullname, balance, country, currency, is_vitual, account_created, account_updated

# Drop existing table if needed
# cursor.execute("DROP TABLE IF EXISTS users")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    uid TEXT NOT NULL,
    user_id TEXT NOT NULL,
    loginid_accountid TEXT NOT NULL,
    email TEXT,
    fullname TEXT,
    balance TEXT,
    country TEXT,
    currency TEXT,
    is_vitual TEXT,
    account_created TEXT,
    account_updated TEXT
)
""")

# Create index for faster lookups
cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON users(user_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_loginid ON users(loginid_accountid)")

conn.commit()

conn.close()

