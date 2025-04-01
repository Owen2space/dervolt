import sqlite3
from database import get_db
from datetime import datetime, timedelta

def create_notifications_table():
    """Create the notifications table if it doesn't exist"""
    with get_db() as db:
        cursor = db.cursor()
        
        # Create notifications table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            notification_type TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        print("Notifications table created successfully!")

def add_sample_notifications():
    """Add sample notifications for existing users"""
    with get_db() as db:
        cursor = db.cursor()
        
        # Check if we already have notifications
        cursor.execute("SELECT COUNT(*) FROM notifications")
        notification_count = cursor.fetchone()[0]
        
        if notification_count > 0:
            print(f"Found {notification_count} existing notifications. Skipping sample data.")
            return
        
        # Get all users
        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()
        
        if not users:
            print("No users found. Please run init_db.py first.")
            return
        
        notification_types = ["transaction", "account", "system"]
        notification_titles = [
            "Deposit Successful", 
            "Withdrawal Completed", 
            "Account Verified", 
            "Security Alert", 
            "System Update"
        ]
        notification_messages = [
            "Your deposit of $500 has been confirmed",
            "Your withdrawal of $200 has been processed",
            "Your account has been successfully verified",
            "New login detected from an unknown device",
            "Scheduled maintenance in 2 days"
        ]
        
        # Add notifications for each user
        for user in users:
            user_id = user[0]
            
            for i in range(7):
                days_ago = 7 - i
                notification_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
                
                notification_type = notification_types[i % len(notification_types)]
                title_index = i % len(notification_titles)
                
                cursor.execute("""
                    INSERT INTO notifications (
                        user_id, title, message, notification_type, is_read, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    notification_titles[title_index],
                    notification_messages[title_index],
                    notification_type,
                    1 if i < 3 else 0,  # First 3 are read, rest are unread
                    notification_date
                ))
        
        print(f"Added sample notifications for {len(users)} users!")

if __name__ == "__main__":
    create_notifications_table()
    add_sample_notifications() 