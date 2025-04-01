from database import get_db

def check_table_exists():
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='password_reset_otps'")
        result = cursor.fetchone()
        if result:
            print("Table exists:", result[0])
        else:
            print("Table does not exist")

if __name__ == "__main__":
    check_table_exists() 