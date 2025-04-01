from flask import Flask, request, jsonify, render_template, session, redirect, url_for, make_response, flash, abort, g, Response, send_from_directory, send_file
import sqlite3
from database import get_db, create_tables, init_db
import json
from datetime import datetime, timedelta
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps
import traceback
import random
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# Import email_service for OTP functionality
from email_service import generate_otp, send_otp_email, save_otp_to_db, verify_otp, process_password_change_request
import re
import string
import time
import threading
import logging
# import markdown  # Removed unused import
from io import BytesIO
import base64
from email_helpers import send_password_reset_email
# Import forex utilities
from forex_utils import fetch_forex_rate, get_latest_forex_rate, calculate_deposit_amount, calculate_withdrawal_amount, store_forex_rate, get_deposit_rate, get_withdrawal_rate
# Import scheduler
import scheduler
from werkzeug.utils import secure_filename

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# More robust helper function for datetime conversion
def ensure_datetime(value):
    """Convert a string timestamp to a datetime object if it's not already one"""
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value
        
    if isinstance(value, str):
        try:
            # Try standard format
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                # Try alternate format
                return datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                try:
                    # Try another common format
                    return datetime.strptime(value, '%b %d, %Y')
                except ValueError:
                    # If all parsing fails, return current time to avoid errors
                    print(f"Warning: Could not parse date string '{value}', using current time")
                    return datetime.now()
    
    # If it's not a string or datetime, return current time
    print(f"Warning: Value '{value}' is not a string or datetime, using current time")
    return datetime.now()

# Helper function to process a row dictionary and convert date fields
def process_date_fields(row_dict, date_fields=None):
    """Process all date fields in a row dictionary"""
    if row_dict is None:
        return None
        
    # Default date fields to check if not specified
    if date_fields is None:
        date_fields = ['created_at', 'updated_at', 'timestamp', 'date']
        
    # Convert all date fields to datetime objects
    for field in date_fields:
        if field in row_dict:
            row_dict[field] = ensure_datetime(row_dict[field])
            
    return row_dict

app = Flask(__name__,
    template_folder='templates',    # Look for templates in backend/templates
    static_folder='static'         # Look for static files in backend/static
)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')

# Add built-in functions to Jinja2 environment
app.jinja_env.globals.update(min=min, max=max)

# Add custom fromjson filter to parse JSON strings
@app.template_filter('fromjson')
def fromjson_filter(value):
    """Convert a JSON string to a Python object"""
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        # Return empty dict if parsing fails
        return {}

# Direct transaction data API endpoint for debugging
@app.route('/api/transactions-debug')
def transactions_debug():
    """Simple API endpoint to return transaction data for debugging"""
    from datetime import datetime, timedelta
    
    user_id = session.get('user_id', 4)  # Default to user_id 4 for testing
    print(f"[Debug API] Using user_id: {user_id}")
    
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # Get account IDs for this user
            cursor.execute("SELECT id FROM accounts WHERE user_id = ?", (user_id,))
            account_ids = [row['id'] for row in cursor.fetchall()]
            
            if not account_ids:
                print(f"[Debug API] No accounts found for user_id: {user_id}")
                # Use a fake account ID for testing
                account_ids = [1]
            
            print(f"[Debug API] Using account_ids: {account_ids}")
            
            # Get transaction data for the last 12 months
            now = datetime.now()
            start_date = (now - timedelta(days=365)).strftime('%Y-%m-%d')
            
            # Get transactions by month and type
            placeholders = ','.join(['?' for _ in account_ids])
            
            # First try to get data by month
            try:
                cursor.execute(f"""
                    SELECT 
                        strftime('%Y-%m', created_at) as month,
                        transaction_type,
                        SUM(amount) as total_amount
                    FROM transactions
                    WHERE account_id IN ({placeholders})
                    AND created_at >= ?
                    GROUP BY month, transaction_type
                    ORDER BY month
                """, account_ids + [start_date])
                
                month_transactions = cursor.fetchall()
                print(f"[Debug API] Found {len(month_transactions)} monthly transaction records")
                
                # If we couldn't get monthly data, use simple totals
                if not month_transactions:
                    raise Exception("No monthly data found")
                    
                # Process month data
                months_list = []
                deposits = {}
                withdrawals = {}
                
                # Get all months in the date range
                current = datetime.strptime(start_date, '%Y-%m-%d')
                while current <= now:
                    month_key = current.strftime('%Y-%m')
                    month_display = current.strftime('%b %Y')
                    months_list.append(month_display)
                    deposits[month_key] = 0
                    withdrawals[month_key] = 0
                    current = (current.replace(day=1) + timedelta(days=32)).replace(day=1)
                
                # Fill in actual values from the database
                for row in month_transactions:
                    month = row['month']
                    if row['transaction_type'].lower() == 'deposit':
                        deposits[month] = row['total_amount']
                    elif row['transaction_type'].lower() == 'withdrawal':
                        withdrawals[month] = row['total_amount']
                
                # Convert dictionaries to arrays in the order of months_list
                deposits_data = [deposits.get(datetime.strptime(month, '%b %Y').strftime('%Y-%m'), 0) for month in months_list]
                withdrawals_data = [withdrawals.get(datetime.strptime(month, '%b %Y').strftime('%Y-%m'), 0) for month in months_list]
                
            except Exception as e:
                print(f"[Debug API] Error getting monthly data: {e}")
                # Fallback to simple data
                # Get deposits and withdrawals totals
                cursor.execute("""
                    SELECT 
                        transaction_type, 
                        SUM(amount) as total 
                    FROM transactions 
                    WHERE user_id = ? 
                    GROUP BY transaction_type
                """, (user_id,))
                
                results = cursor.fetchall()
                
                # Process results
                total_deposits = 0
                total_withdrawals = 0
                
                for row in results:
                    if row['transaction_type'].lower() == 'deposit':
                        total_deposits = row['total']
                    elif row['transaction_type'].lower() == 'withdrawal':
                        total_withdrawals = row['total']
                
                # Create a simple response with dummy monthly breakdown
                months_list = []
                deposits_data = []
                withdrawals_data = []
                
                # Create 12 months of data points
                for i in range(12):
                    month = (now - timedelta(days=30 * (11 - i))).strftime('%b %Y')
                    months_list.append(month)
                    deposits_data.append(total_deposits / 12)
                    withdrawals_data.append(total_withdrawals / 12)
            
            # Get totals for summary
            cursor.execute(f"""
                SELECT 
                    transaction_type,
                    SUM(amount) as total_amount
                FROM transactions
                WHERE account_id IN ({placeholders})
                GROUP BY transaction_type
            """, account_ids)
            
            totals = cursor.fetchall()
            
            # Process totals
            total_deposits = 0
            total_withdrawals = 0
            
            for total in totals:
                if total['transaction_type'].lower() == 'deposit':
                    total_deposits = total['total_amount']
                elif total['transaction_type'].lower() == 'withdrawal':
                    total_withdrawals = total['total_amount']
            
            # Calculate profits
            profits_data = [w - d for w, d in zip(withdrawals_data, deposits_data)]
            # Corrected profit calculation for trading profits: withdrawals - deposits 
            total_profit = total_withdrawals - total_deposits
            
            print(f"[Debug API] Total deposits: {total_deposits}, withdrawals: {total_withdrawals}, profit: {total_profit}")
            
            return jsonify({
                'success': True,
                'labels': months_list,
                'deposits': deposits_data,
                'withdrawals': withdrawals_data,
                'profits': profits_data,
                'summary': {
                    'totalDeposits': total_deposits,
                    'totalWithdrawals': total_withdrawals,
                    'totalProfit': total_profit
                }
            })
    except Exception as e:
        print(f"[Debug API] Error: {e}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

def create_activity_logs_table():
    """Create activity_logs table if it doesn't exist"""
    try:
        with get_db() as db:
            cursor = db.cursor()
            # Check if the table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='activity_logs'")
            if not cursor.fetchone():
                print("Creating activity_logs table as it doesn't exist")
                cursor.execute("""
                    CREATE TABLE activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    action TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                    )


                """)
                db.commit()
                print("activity_logs table created successfully")
    except Exception as e:
        print(f"Error creating activity_logs table: {e}")

# Instead of @app.before_first_request, use app.before_request with a flag
_database_initialized = False


def populate_activity_logs():
    pass


@app.before_request
def initialize_database_if_needed():
    """Initialize database and create missing tables if not already done."""
    global _database_initialized
    if not _database_initialized:
        try:
            print("Initializing database and checking for missing tables...")
            create_activity_logs_table()
            populate_activity_logs()  # Add this line to populate activity logs
            _database_initialized = True
        except Exception as e:
            print(f"Error initializing database: {e}")

def get_current_user_id():
    return session.get('user_id')

# CORS middleware configuration
@app.after_request
def add_cors_headers(response):
    # Since we're using credentials, we need to specify the exact origin instead of '*'
    response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
    return response

def get_system_setting(key, default=None):
    """Helper function to get a system setting by key"""
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result['value'] if result else default
    except Exception as e:
        print(f"Error getting system setting '{key}': {e}")
        return default

@app.before_request
def check_maintenance_mode():
    """Check if maintenance mode is enabled and redirect non-admin users to maintenance page"""
    # Skip for static files, login page, and admin routes
    if request.path.startswith('/static') or \
       request.path == '/login' or \
       request.path.startswith('/admin') or \
       request.path == '/maintenance':
        return

    # Check if maintenance mode is enabled
    maintenance_mode = get_system_setting('maintenance_mode', '0')

    if maintenance_mode == '1' and 'admin_id' not in session:
        return redirect(url_for('maintenance'))

@app.before_request
def check_session_timeout():
    """Check for session timeout based on system settings"""
    # Skip for static files, login, logout, and public routes
    if (request.path.startswith('/static') or
        request.path in ['/login', '/logout', '/', '/signup', '/forgot', '/maintenance'] or
        request.path.startswith('/auth/') or
        request.path.startswith('/admin/') or  # Skip all admin routes
        request.endpoint in ['static', None]):
        return

    # Get session timeout from settings (in minutes)
    timeout_minutes = int(get_system_setting('session_timeout', '30'))

    # Check if user is logged in
    if 'user_id' in session:
        # Check if last_activity is in session
        if 'last_activity' not in session:
            # First request after login, set the timestamp
            session['last_activity'] = time.time()
        else:
            # Check if session has timed out
            last_activity = session.get('last_activity')
            if last_activity and (time.time() - last_activity) > (timeout_minutes * 60):
                # Session has timed out
                session.clear()
                flash("Your session has expired due to inactivity. Please log in again.", "info")
                return redirect(url_for('login'))

            # Update last activity timestamp
            session['last_activity'] = time.time()

    # Check if admin is logged in
    elif 'admin_id' in session:
        # Check if admin_last_activity is in session
        if 'admin_last_activity' not in session:
            # First request after admin login, set the timestamp
            session['admin_last_activity'] = time.time()
        else:
            # Check if admin session has timed out
            admin_last_activity = session.get('admin_last_activity')
            if admin_last_activity and (time.time() - admin_last_activity) > (timeout_minutes * 60):
                # Admin session has timed out
                session.clear()
                flash("Your admin session has expired due to inactivity. Please log in again.", "info")
                return redirect(url_for('admin_login'))

            # Update admin last activity timestamp
            session['admin_last_activity'] = time.time()

@app.route("/maintenance")
def maintenance():
    """Display maintenance page"""
    maintenance_message = get_system_setting(
        'maintenance_message',
        'We are currently performing scheduled maintenance. Please check back later.'
    )
    return render_template("maintenance.html", message=maintenance_message)

# Helper functions
def generate_account_number():
    prefix = "DERV"
    random_digits = ''.join(random.choices(string.digits, k=8))
    return f"{prefix}{random_digits}"

def generate_transaction_reference():
    prefix = "TXN"
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}{timestamp}{random_chars}"

# Page routes
@app.route("/")
def index():
    try:
        print(f"Templates directory: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')}")
        print(f"Templates directory exists: {os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))}")
        print(f"Index.html exists: {os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'index.html'))}")
        print("Attempting to render index.html")
        return render_template("index.html")
    except Exception as e:
        print(f"Error rendering index.html: {e}")
        print(traceback.format_exc())
        return f"Error: {str(e)}", 500

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            session.clear()
            response = make_response(redirect(url_for('login')))
            # Set strict cache control headers
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            # Clear session cookie
            response.set_cookie('session', '', expires=0)
            return response

        # Check if user is blocked
        try:
            user_id = session.get('user_id')
            with get_db() as db:
                cursor = db.cursor()
                cursor.execute("SELECT is_active, blocked_reason FROM users WHERE id = ?", (user_id,))
                user = cursor.fetchone()
                
                if not user:
                    # User doesn't exist anymore
                    session.clear()
                    flash('Account not found', 'error')
                    response = make_response(redirect(url_for('login')))
                    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                    response.set_cookie('session', '', expires=0)
                    return response
                    
                # Convert to dict to safely access fields
                user_dict = dict(user)
                
                # Check if user is blocked (is_active = 0)
                if user_dict.get('is_active') == 0:
                    # User is blocked
                    session.clear()
                    
                    # Get block reason and date
                    blocked_reason = user_dict.get('blocked_reason')
                    blocked_at = user_dict.get('blocked_at')
                    
                    # Construct a more detailed block message
                    if blocked_reason:
                        blocked_message = f"Access Denied: {blocked_reason}"
                        if blocked_at:
                            blocked_message += f" (Blocked on: {blocked_at})"
                    else:
                        blocked_message = "Your account has been blocked for violating our policies. Please contact support."
                    
                    flash(blocked_message, 'error')
                    response = make_response(redirect(url_for('login')))
                    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                    response.set_cookie('session', '', expires=0)
                    return response
        except Exception as e:
            print(f"Error checking user active status: {e}")
            # In case of error, still allow the user to proceed
            # This is a fallback to prevent complete system lockout

        # Add cache control headers to all authenticated responses
        response = make_response(f(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return decorated_function

@app.after_request
def add_header(response):
    # Prevent caching of authenticated pages but allow back navigation
    if 'user_id' in session:
        # Modified to allow back navigation while maintaining security
        response.headers['Cache-Control'] = 'private, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.route("/dashboard")
@login_required
def dashboard():
    """
    Render the dashboard with user data, accounts, transactions and notifications.
    """
    current_user_id = session.get('user_id')

    try:
        # Connect to the database
        with get_db() as db:
            cursor = db.cursor()

            # Fetch user data
            cursor.execute("SELECT * FROM users WHERE id = ?", (current_user_id,))
            user = cursor.fetchone()

            if not user:
                session.clear()
                return redirect(url_for('login'))

            # Fetch user accounts
            cursor.execute("""
                SELECT a.*, 
                COALESCE((SELECT SUM(amount) FROM transactions 
                WHERE account_id = a.id AND transaction_type = 'deposit' AND status = 'completed'), 0) -
                COALESCE((SELECT SUM(amount) FROM transactions 
                WHERE account_id = a.id AND transaction_type = 'withdrawal' AND status = 'completed'), 0) as balance
                FROM accounts a
                WHERE a.user_id = ?


            """, (current_user_id,))
            accounts = cursor.fetchall()

            # If no accounts, create a default one
            if not accounts:
                account_number = generate_account_number()
                cursor.execute("""
                    INSERT INTO accounts (user_id, account_number, account_name, account_type, currency, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)


                """, (current_user_id, account_number, "Default Account", "standard", "USD", 1))
                db.commit()

                # Fetch the newly created account
                cursor.execute("""
                    SELECT a.*, 0 as balance
                    FROM accounts a
                    WHERE a.id = last_insert_rowid()


                """)
                accounts = cursor.fetchall()

            # Fetch recent transactions
            cursor.execute("""
                SELECT t.*, a.account_number 
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE a.user_id = ?
                ORDER BY t.created_at DESC
                LIMIT 10


            """, (current_user_id,))
            transactions = cursor.fetchall()
            
            # Process all transactions to ensure date fields are datetime objects
            processed_transactions = []
            for transaction in transactions:
                # Convert the Row object to a dictionary
                transaction_dict = dict(transaction)
                # Process all date fields
                processed_transaction = process_date_fields(transaction_dict)
                processed_transactions.append(processed_transaction)
            
            transactions = processed_transactions
            print(f"Processed {len(transactions)} transactions with datetime conversion")

            # Fetch recent notifications
            cursor.execute("""
                SELECT * FROM notifications 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 5


            """, (current_user_id,))
            notifications = cursor.fetchall()
            
            # Process all notifications to ensure date fields are datetime objects
            processed_notifications = []
            for notification in notifications:
                # Convert the Row object to a dictionary
                notification_dict = dict(notification)
                # Process all date fields
                processed_notification = process_date_fields(notification_dict)
                processed_notifications.append(processed_notification)
                
            notifications = processed_notifications
            print(f"Processed {len(notifications)} notifications with datetime conversion")

            # Count unread notifications
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM notifications
                WHERE user_id = ? AND is_read = 0


            """, (current_user_id,))
            unread_result = cursor.fetchone()
            unread_count = unread_result['count'] if unread_result else 0

        # Format accounts for JSON serialization (needed for JavaScript)
        accounts_json = []
        for account in accounts:
            account_dict = dict(account)
            account_dict['balance'] = float(account_dict['balance'])  # Ensure numeric
            processed_account = process_date_fields(account_dict)
            accounts_json.append(processed_account)

        # Current timestamp - ensure it's a datetime object
        now = datetime.now()

        # Debug log the types
        for t in transactions[:2]:
            if 'created_at' in t:
                print(f"Transaction created_at: {t['created_at']} (type: {type(t['created_at']).__name__})")
                
        for n in notifications[:2]:
            if 'created_at' in n:
                print(f"Notification created_at: {n['created_at']} (type: {type(n['created_at']).__name__})")

        # If we have accounts, determine which one to display by default
        selected_account_id = None
        if accounts:
            # Use the account with the highest balance as the default selected account
            accounts_by_balance = sorted(accounts, key=lambda x: float(x['balance']), reverse=True)
            selected_account_id = accounts_by_balance[0]['id']
            print(f"Selected account ID for dashboard display: {selected_account_id}")

        # Render template with all required data
        return render_template(
            'dashboard.html',
            user=user,
            accounts=accounts,
            transactions=transactions,
            notifications=notifications,
            unread_count=unread_count,
            now=now,
            selected_account_id=selected_account_id,
            accounts_json=json.dumps(accounts_json, default=str)  # Handle datetime serialization
        )

    except Exception as e:
        # Log the error
        print(f"Dashboard error: {str(e)}")
        traceback.print_exc()
        return redirect(url_for('login'))

@app.route("/login")
def login():
    # Check if there's a success message from password reset
    success_message = request.args.get('success')
    if success_message:
        flash(success_message, "success")
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login_post():
    # Handle both form and JSON data
    if request.is_json:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        remember = data.get("remember", False)
    else:
        email = request.form.get("email")
        password = request.form.get("password")
        remember = request.form.get("remember", False)

    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password_hash"], password):
            # Check if user is blocked
            # Convert Row to dict to safely access keys
            user_dict = dict(user)
            if user_dict.get("is_active") == 0:
                # User is blocked
                blocked_reason = user_dict.get("blocked_reason", "Your account has been blocked")
                blocked_at = user_dict.get("blocked_at")
                
                # Construct a more informative blocked message
                if blocked_reason:
                    # Make more robust and detailed message
                    blocked_message = f"Access Denied: {blocked_reason}"
                    if blocked_at:
                        blocked_message += f" (Blocked on: {blocked_at})"
                else:
                    blocked_message = "Your account has been blocked for violating our policies. Please contact support."
                
                # Log blocked user attempt
                log_security_event(
                    "blocked_login", 
                    f"Blocked user attempted to login: {email}", 
                    "medium", 
                    user["id"]
                )
                
                if request.is_json:
                    return jsonify({
                        "success": False,
                        "message": blocked_message
                    }), 403
                else:
                    flash(blocked_message, "error")
                    return redirect(url_for("login"))
            
            # User is active, proceed with login
            # Log successful login
            log_user_activity(user["id"], "login", f"User {user['email']} logged in successfully")
            
            # Set session
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            session["first_name"] = user["first_name"]
            session["last_name"] = user["last_name"]
            
            if remember:
                session.permanent = True
            
            if request.is_json:
                return jsonify({
                    "success": True,
                    "message": "Login successful!",
                    "user": {
                        "id": user["id"],
                        "email": user["email"],
                        "first_name": user["first_name"],
                        "last_name": user["last_name"]
                    }
                })
            else:
                flash("Login successful!", "success")
                return redirect(url_for("dashboard"))
        else:
            # Log failed login attempt
            if user:
                log_security_event("failed_login", f"Failed login attempt for user {email}", "medium", user["id"])
            else:
                log_security_event("failed_login", f"Failed login attempt for non-existent user {email}", "low")
            
            if request.is_json:
                return jsonify({
                    "success": False,
                    "message": "Invalid email or password"
                }), 401
            else:
                flash("Invalid email or password", "error")
                return redirect(url_for("login"))

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/forgot")
def forgot():
    return render_template("forgot.html", step="email")

@app.route("/forgot", methods=["POST"])
def forgot_post():
    try:
        data = request.get_json()
        email = data.get("email")

        print(f"Received password reset request for email: {email}")

        if not email:
            print("Error: Email is required")
            return jsonify({"success": False, "message": "Email is required"})

        # Import the email service
        from email_service import process_password_reset_request

        success, message = process_password_reset_request(email)
        print(f"Password reset request result: success={success}, message={message}")

        return jsonify({"success": success, "message": message})
    except Exception as e:
        print(f"Error in forgot_post route: {e}")
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data = request.get_json()
        email = data.get("email")
        otp = data.get("otp")

        if not email or not otp:
            return jsonify({"success": False, "message": "Email and OTP are required"})

        # Import the email service
        from email_service import verify_otp as verify_otp_func

        # Verify OTP but don't mark as used yet (we'll mark it as used during password reset)
        is_valid = verify_otp_func(email, otp, mark_as_used=False)

        if is_valid:
            return jsonify({"success": True, "message": "OTP verified successfully"})
        else:
            return jsonify({"success": False, "message": "Invalid or expired OTP"})
    except Exception as e:
        print(f"Error in verify_otp route: {e}")
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500

@app.route("/reset-password", methods=["POST"])
def reset_password():
    try:
        print("Reset password endpoint called")

        # Get form data instead of JSON
        email = request.form.get("email")
        otp = request.form.get("otp")
        password = request.form.get("password")

        print(f"Form data received: email={email}, otp={otp}, password={'*' * len(password) if password else None}")

        if not email or not otp or not password:
            print("Error: Email, OTP, and password are required")
            return render_template("forgot.html", step="password", email=email, otp=otp,
                error="Email, OTP, and password are required")

        # Import the email service
        from email_service import verify_otp as verify_otp_func
        from werkzeug.security import generate_password_hash

        # Verify OTP again for security
        is_valid = verify_otp_func(email, otp, mark_as_used=True)
        print(f"OTP verification result: {is_valid}")

        if not is_valid:
            print(f"Error: Invalid or expired OTP for email {email}")
            return render_template("forgot.html", step="password", email=email, otp=otp,
                error="Invalid or expired OTP")

        # Update user's password
        try:
            with get_db() as db:
                cursor = db.cursor()
                cursor.execute(
                    "UPDATE users SET password_hash = ? WHERE email = ?",
                    (generate_password_hash(password), email)
                )
                db.commit()  # Explicitly commit the changes

                if cursor.rowcount > 0:
                    print(f"Password reset successful for email {email}")
                    # Redirect to login page with success message
                    return redirect(url_for('login', success_message="Your password has been reset successfully"))
                else:
                    print(f"Error: Failed to reset password for email {email}")
                    return render_template("forgot.html", step="password", email=email, otp=otp,
                        error="Failed to reset password")


        except Exception as e:

            print(f"Error occurred: {e}")
        except Exception as e:
            print(f"Database error while resetting password: {e}")
            return render_template("forgot.html", step="password", email=email, otp=otp,
                error="An error occurred while resetting password")
    except Exception as e:
        print(f"Error in reset_password route: {e}")
        traceback.print_exc()  # Print the full exception traceback
        return render_template("forgot.html", step="password",
            error=f"An error occurred: {str(e)}")

@app.route("/help")
@login_required
def help():
    user_id = get_current_user_id()
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
    return render_template("help.html", user=user)

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user_id = get_current_user_id()
    with get_db() as db:
        cursor = db.cursor()

        if request.method == "POST":
            try:
                # Process payment method update
                user_data = request.json
                payment_method = user_data.get('payment_method')
                deriv_account = user_data.get('deriv_account')
                mpesa_phone = user_data.get('mpesa_phone')
                
                # Validate inputs
                if not payment_method:
                    return jsonify({"message": "Payment method is required", "success": False}), 400
                
                # Update user payment preferences in the database
                updates = []
                params = []
                
                if payment_method:
                    updates.append("preferred_payment_method = ?")
                    params.append(payment_method)
                
                if mpesa_phone:
                    updates.append("phone_number = ?")
                    params.append(mpesa_phone)
                
                if updates:
                    # Update user record
                    query = f"UPDATE users SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                    params.append(user_id)
                    cursor.execute(query, params)
                    app.logger.info(f"Updated payment method for user {user_id}: {payment_method}")
                
                # Update default account if specified
                if deriv_account:
                    # Clear previous default settings
                    cursor.execute("UPDATE accounts SET is_default = 0 WHERE user_id = ?", (user_id,))
                    # Set new default
                    cursor.execute("UPDATE accounts SET is_default = 1 WHERE id = ? AND user_id = ?", 
                                  (deriv_account, user_id))
                    app.logger.info(f"Updated default account for user {user_id}: {deriv_account}")
                
                # Explicitly commit changes
                db.commit()
                app.logger.info(f"Successfully committed payment method changes for user {user_id}")
                
                return jsonify({"message": "Payment method updated successfully", "success": True}), 200
            except Exception as e:
                db.rollback()
                app.logger.error(f"Error updating payment method for user {user_id}: {str(e)}")
                return jsonify({"message": "An error occurred. Please try again", "success": False}), 500

        cursor.execute("""
            SELECT *, 
                   COALESCE(preferred_payment_method, 'mpesa') AS preferred_payment_method
            FROM users 
            WHERE id = ?
        """, (user_id,))
        user = cursor.fetchone()

        # Fetch user accounts for the Deriv account selector
        cursor.execute("""
            SELECT a.*, 
            COALESCE((SELECT SUM(amount) FROM transactions 
            WHERE account_id = a.id AND transaction_type = 'deposit' AND status = 'completed'), 0) -
            COALESCE((SELECT SUM(amount) FROM transactions 
            WHERE account_id = a.id AND transaction_type = 'withdrawal' AND status = 'completed'), 0) as balance
            FROM accounts a
            WHERE a.user_id = ?
        """, (user_id,))
        accounts = cursor.fetchall()

        # If no accounts exist, create a default one
        if not accounts:
            account_number = generate_account_number()
            cursor.execute("""
                INSERT INTO accounts (user_id, account_number, account_name, account_type, currency, is_active, is_default)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (user_id, account_number, "Default Account", "standard", "USD", 1))
            db.commit()

            # Fetch the newly created account
            cursor.execute("""
                SELECT a.*, 0 as balance
                FROM accounts a
                WHERE a.id = last_insert_rowid()
            """)
            accounts = cursor.fetchall()
            
        # Check if any account is set as default
        any_default_account = any(account['is_default'] == 1 for account in accounts)
        
        # If no account is set as default, set the first one
        if not any_default_account and accounts:
            cursor.execute("UPDATE accounts SET is_default = 1 WHERE id = ?", (accounts[0]['id'],))
            db.commit()
            accounts[0]['is_default'] = 1
            any_default_account = True

    return render_template("settings.html", user=user, accounts=accounts, any_default_account=any_default_account)

@app.route("/transactions", methods=["POST"])
@login_required
def create_transaction():
    """
    Create a new transaction:
    - Deposits: User inputs USD amount, system converts to KES using deposit rate with spread
    - Withdrawals: User inputs USD amount, system converts to KES using withdrawal rate with spread
    
    Forex rates are updated every 12 hours from Open Exchange Rates API.
    """
    try:
        data = request.get_json()

        # Get data from request
        account_id = data.get('account_id')
        amount = float(data.get('amount', 0))  # Amount in USD
        transaction_type = data.get('transaction_type')
        payment_method = data.get('payment_method')
        description = data.get('description', '')
        otp = data.get('otp')

        # Validate required fields
        if not account_id or amount <= 0 or not transaction_type:
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        if transaction_type not in ['deposit', 'withdrawal']:
            return jsonify({"success": False, "message": "Invalid transaction type"}), 400
            
        # Get user_id from session
        user_id = session.get('user_id')
        
        # Calculate amounts with forex rate and appropriate spread
        forex_calculation = None
        if transaction_type == 'deposit':
            # Use higher rate for deposits (favorable to customers)
            forex_calculation = calculate_deposit_amount(amount)
        else:  # withdrawal
            # Use lower rate for withdrawals
            forex_calculation = calculate_withdrawal_amount(amount)
            
        if not forex_calculation.get('success'):
            return jsonify({"success": False, "message": forex_calculation.get('message', "Error calculating forex conversion")}), 400
            
        # Use these values for the transaction
        converted_amount = forex_calculation['kes_amount']  # Amount in KES
        fee = forex_calculation['fee_usd']  # Fee in USD
        forex_rate = forex_calculation['forex_rate']  # The applied rate with spread
        
        # Additional metadata to store with transaction
        forex_metadata = {
            "forex_rate": forex_rate,
            "converted_amount_kes": converted_amount,
            "fee_usd": fee,
            "fee_percent": forex_calculation['fee_percent'],
            "rate_timestamp": forex_calculation['rate_updated_at']
        }
        
        # Convert metadata to JSON string
        forex_metadata_json = json.dumps(forex_metadata)

        # Generate unique reference number
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S")
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
        reference = f"TXN{timestamp}{random_suffix}"

        with get_db() as db:
            cursor = db.cursor()

            # Check if account exists and belongs to the user
            cursor.execute(
                "SELECT * FROM accounts WHERE id = ? AND user_id = ?",
                (account_id, user_id)
            )
            account = cursor.fetchone()

            if not account:
                return jsonify({"success": False, "message": "Account not found or does not belong to user"}), 404

            # Set status based on transaction type and amount
            # For deposits, transactions above $1000 require approval
            # For withdrawals, transactions above $500 require approval
            status = 'pending'
            if (transaction_type == 'deposit' and amount <= 1000) or (transaction_type == 'withdrawal' and amount <= 500):
                status = 'completed'

            # For pending withdrawals, don't update balance yet
            balance_update = amount if transaction_type == 'deposit' and status == 'completed' else 0
            if transaction_type == 'withdrawal' and status == 'completed':
                balance_update = -amount  # Negative for withdrawals

            # Insert transaction
            cursor.execute("""
                INSERT INTO transactions 
                (account_id, user_id, amount, transaction_type, payment_method, status, reference, description, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                account_id,
                user_id,
                amount,
                transaction_type,
                payment_method,
                status,
                reference,
                description,
                forex_metadata_json,
                now.strftime("%Y-%m-%d %H:%M:%S")
            ))

            # Update account balance if transaction is completed
            if status == 'completed':
                cursor.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                    (balance_update, account_id)
                )

            # Create notification
            notification_message = f"Your {transaction_type} of ${amount:.2f} has been {status}."
            if status == 'pending':
                notification_message += " It will be reviewed shortly."

            cursor.execute("""
                INSERT INTO notifications 
                (user_id, title, message, notification_type, is_read, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                f"{transaction_type.capitalize()} {status}",
                notification_message,
                transaction_type,
                0,
                now.strftime("%Y-%m-%d %H:%M:%S")
            ))

            db.commit()

            return jsonify({
                "success": True,
                "message": f"{transaction_type.capitalize()} {status}",
                "transaction": {
                    "reference": reference,
                    "amount": amount,
                    "transaction_type": transaction_type,
                    "status": status,
                    "forex_rate": forex_rate,
                    "converted_amount_kes": converted_amount,
                    "fee_usd": fee
                }
            })

    except Exception as e:
        print(f"Error creating transaction: {str(e)}")
        traceback.print_exc()
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500

@app.route("/transactions/<int:user_id>")
def get_user_transactions(user_id):
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM transactions WHERE user_id = ?", (user_id,))
        transactions = cursor.fetchall()
        return jsonify({"transactions": [dict(tx) for tx in transactions]})

@app.route("/transactions")
@login_required
def transactions():
    user_id = get_current_user_id()
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()

            cursor.execute("""
                SELECT t.*, a.account_number 
                FROM transactions t
                LEFT JOIN accounts a ON t.account_id = a.id
                WHERE a.user_id = ?
                ORDER BY t.created_at DESC


            """, (user_id,))
            transactions = cursor.fetchall()
            
            # Process all transactions to ensure date fields are datetime objects
            processed_transactions = []
            for transaction in transactions:
                # Convert the Row object to a dictionary
                transaction_dict = dict(transaction)
                # Process all date fields
                processed_transaction = process_date_fields(transaction_dict)
                
                # Process metadata field if it exists
                if processed_transaction.get('metadata'):
                    try:
                        # Ensure metadata is properly parsed to JSON
                        if isinstance(processed_transaction['metadata'], str):
                            processed_transaction['metadata'] = json.loads(processed_transaction['metadata'])
                    except Exception as e:
                        print(f"Error parsing transaction metadata: {str(e)}")
                        print(f"Raw metadata: {processed_transaction.get('metadata')}")
                        # Keep as is if there's an error
                
                processed_transactions.append(processed_transaction)
            
            transactions = processed_transactions
            print(f"Processed {len(transactions)} transactions for transactions page")
            
            # Debug log the types of first few transactions
            for t in transactions[:2]:
                if 'created_at' in t:
                    print(f"Transaction created_at: {t['created_at']} (type: {type(t['created_at']).__name__})")
        
        # Current timestamp for the template
        now = datetime.now()
        
        return render_template("transactions.html", user=user, transactions=transactions, now=now)
        
    except Exception as e:
        # Log the error
        print(f"Transactions page error: {str(e)}")
        traceback.print_exc()
        return redirect(url_for('login'))

# Notification endpoints
@app.route("/notifications")
@login_required
def view_all_notifications():
    user_id = get_current_user_id()
    try:
        if not user_id:
            return redirect(url_for('login'))

        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()

            if not user:
                session.clear()
                return redirect(url_for('login'))

            cursor.execute("""
                SELECT * FROM notifications 
                WHERE user_id = ? 
                ORDER BY created_at DESC


            """, (user_id,))
            notifications = cursor.fetchall()
            
            # Process all notifications to ensure date fields are datetime objects
            processed_notifications = []
            for notification in notifications:
                # Convert the Row object to a dictionary
                notification_dict = dict(notification)
                # Process all date fields
                processed_notification = process_date_fields(notification_dict)
                processed_notifications.append(processed_notification)
                
            notifications = processed_notifications
            print(f"Processed {len(notifications)} notifications for notifications page")

        # Current timestamp for the template
        now = datetime.now()
        
        response = make_response(render_template("notifications.html", user=user, notifications=notifications, now=now))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
        
    except Exception as e:
        # Log the error
        print(f"Notifications page error: {str(e)}")
        traceback.print_exc()
        return redirect(url_for('login'))

@app.route("/notifications/mark-read", methods=["POST"])
@login_required
def mark_notification_read():
    notification_id = request.json.get('notification_id')
    user_id = get_current_user_id()

    try:
        with get_db() as db:
            cursor = db.cursor()
            if notification_id == 'all':
                cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
                db.commit()  # Explicitly commit the transaction
                return jsonify({"success": True, "message": "All notifications marked as read"}), 200
            else:
                cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
                    (notification_id, user_id))
                db.commit()  # Explicitly commit the transaction
                return jsonify({"success": True, "message": "Notification marked as read"}), 200
    except Exception as e:
        print(f"Error marking notification as read: {str(e)}")
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@app.route("/notifications/delete", methods=["POST"])
@login_required
def delete_notification():
    notification_id = request.json.get('notification_id')
    user_id = get_current_user_id()

    if not notification_id:
        return jsonify({"success": False, "message": "Notification ID is required"}), 400

    try:
        with get_db() as db:
            cursor = db.cursor()
            if notification_id == 'all':
                cursor.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
                affected_rows = cursor.rowcount
                db.commit()  # Explicitly commit the transaction
                return jsonify({
                    "success": True, 
                    "message": "All notifications deleted",
                    "count": affected_rows
                }), 200
            else:
                # First check if notification exists and belongs to user
                cursor.execute("SELECT id FROM notifications WHERE id = ? AND user_id = ?", 
                    (notification_id, user_id))
                notification = cursor.fetchone()
                
                if not notification:
                    return jsonify({"success": False, "message": "Notification not found"}), 404
                
                cursor.execute("DELETE FROM notifications WHERE id = ? AND user_id = ?", 
                    (notification_id, user_id))
                db.commit()  # Explicitly commit the transaction
                return jsonify({"success": True, "message": "Notification deleted"}), 200
    except Exception as e:
        print(f"Error deleting notification: {str(e)}")
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@app.route("/notifications/create", methods=["POST"])
@login_required
def create_notification():
    data = request.get_json()
    
    user_id = data.get('user_id')
    title = data.get('title')
    message = data.get('message')
    notification_type = data.get('notification_type', 'info')
    
    if not all([user_id, title, message]):
        return jsonify({
            "success": False,
            "message": "Missing required fields"
        }), 400
    
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, notification_type, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                title,
                message,
                notification_type,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            
            db.commit()
            
            return jsonify({
                "success": True,
                "message": "Notification created successfully"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error creating notification: {str(e)}"
        }), 500

@app.route("/api/user/current", methods=["GET"])
def get_current_user():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            session.clear()
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "user": {
                "first_name": user['first_name'],
                "last_name": user['last_name'],
                "email": user['email'],
                "phone_number": user['phone_number']
            }
        })

@app.route("/logout")
def logout():
    # Clear the session
    session.clear()
    return redirect(url_for('index'))

@app.route("/api/check-auth")
def check_auth():
    is_authenticated = 'user_id' in session
    if not is_authenticated:
        # Clear any lingering session data
        session.clear()

    response = jsonify({
        "authenticated": is_authenticated,
        "timestamp": datetime.now().timestamp()
    })

    # Set cache control headers to prevent caching of auth status
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'

    return response, 200 if is_authenticated else 401

@app.route("/test-forgot", methods=["GET"])
def test_forgot():
    """Debug route to test the forgot password functionality"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Forgot Password</title>
    </head>
    <body>
        <h1>Test Forgot Password</h1>
        <form id="testForm">
            <input type="email" id="email" placeholder="Enter email" required>
            <button type="submit">Send Reset Code</button>
        </form>
        <div id="result"></div>

        <script>
            document.getElementById('testForm').addEventListener('submit', function(e) {
                e.preventDefault();
                const email = document.getElementById('email').value;
                const resultDiv = document.getElementById('result');

                resultDiv.innerHTML = 'Sending request...';

                fetch('/forgot', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ email: email }),
                })
                .then(response => {
                    console.log('Response status:', response.status);
                    return response.json();
                })
                .then(data => {
                    console.log('Response data:', data);
                    resultDiv.innerHTML = JSON.stringify(data, null, 2);
                })
                .catch(error => {
                    console.error('Error:', error);
                    resultDiv.innerHTML = 'Error: ' + error;
                });
            });
        </script>
    </body>
    </html>
    """

@app.route("/api/verify-password", methods=["POST"])
@login_required
def verify_password():
    user_id = get_current_user_id()
    current_password = request.json.get("currentPassword")

    if not current_password:
        return jsonify({"success": False, "message": "Current password is required"}), 400

    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT password_hash, email FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        # Verify the current password
        if not check_password_hash(user["password_hash"], current_password):
            return jsonify({"success": False, "message": "Current password is incorrect"}), 401

        try:
            # Generate OTP
            from email_service import generate_otp
            otp_code = generate_otp()
            print(f"Generated OTP for password change: {otp_code}")

            # Check if a previous OTP exists for this email and mark it as used
            cursor.execute("SELECT * FROM password_reset_otps WHERE email = ? AND is_used = 0", (user["email"],))
            existing_otp = cursor.fetchone()

            if existing_otp:
                # Mark previous OTP as used
                cursor.execute("UPDATE password_reset_otps SET is_used = 1 WHERE id = ?", (existing_otp['id'],))

            # Generate expiration time (30 minutes from now)
            expires_at = (datetime.now() + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
            # Insert new OTP
            cursor.execute(
                "INSERT INTO password_reset_otps (email, otp_code, expires_at) VALUES (?, ?, ?)",
                (user["email"], otp_code, expires_at)
            )

            # Send OTP email
            send_otp_email(user["email"], otp_code)

            return jsonify({
                "success": True,
                "message": "Password reset OTP has been sent to your email"
            })
        except Exception as e:
            print(f"Error sending OTP: {e}")
            return jsonify({
                "success": False,
                "message": "Could not send OTP. Please try again later."
            }), 500

@app.route("/api/resend-otp", methods=["POST"])
@login_required
def resend_otp():
    user_id = get_current_user_id()

    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        try:
            # Generate OTP
            from email_service import generate_otp
            otp_code = generate_otp()
            print(f"Generated new OTP for password change: {otp_code}")

            # Save OTP to database
            with get_db() as db:
                cursor = db.cursor()
                # First invalidate any existing OTPs for this email
                cursor.execute(
                    "UPDATE password_reset_otps SET is_used = 1 WHERE email = ?",
                    (user["email"],)
                )
                # Calculate expiration time (30 minutes from now)
                expires_at = (datetime.now() + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
                # Insert new OTP
                cursor.execute(
                    "INSERT INTO password_reset_otps (email, otp_code, expires_at) VALUES (?, ?, ?)",
                    (user["email"], otp_code, expires_at)
                )

            # Send OTP email
            from email_service import send_otp_email
            email_sent = send_otp_email(user["email"], otp_code, "Change Your Password")

            if email_sent:
                return jsonify({"success": True, "message": "New verification code sent to your email"}), 200
            else:
                return jsonify({"success": False, "message": "Failed to send verification code. Please try again."}), 500
        except Exception as e:
            print(f"Error resending OTP: {str(e)}")
            traceback.print_exc()
            return jsonify({"success": False, "message": "Failed to send verification code. Please try again."}), 500

@app.route("/api/change-password", methods=["POST"])
@login_required
def change_password():
    user_id = get_current_user_id()
    otp = request.json.get("otp")
    new_password = request.json.get("newPassword")

    print(f"Password change request received - user_id: {user_id}, OTP: {otp}")

    if not otp or not new_password:
        return jsonify({"success": False, "message": "OTP and new password are required"}), 400

    try:
        with get_db() as db:
            cursor = db.cursor()

            # Get user email
            cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()

            if not user:
                print(f"User not found with ID: {user_id}")
                return jsonify({"success": False, "message": "User not found"}), 404

            print(f"Retrieved user email: {user['email']}")

            # Verify OTP using the same method as forgot password
            from email_service import verify_otp
            otp_valid = verify_otp(user["email"], otp)
            print(f"OTP verification result: {otp_valid}")

            if not otp_valid:
                return jsonify({"success": False, "message": "Invalid or expired verification code"}), 401

            # Update password
            try:
                password_hash = generate_password_hash(new_password)
                cursor.execute("""
                    UPDATE users SET password_hash = ?
                    WHERE id = ?
                """, (password_hash, user_id))
                db.commit()
                print(f"Password updated successfully for user_id: {user_id}")
            except Exception as e:
                print(f"Error updating password: {e}")
                db.rollback()
                return jsonify({"success": False, "message": f"Failed to update password: {str(e)}"}), 500

            # Create notification
            try:
                cursor.execute("""
                    INSERT INTO notifications (user_id, title, message, notification_type, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    "Password Updated",
                    "Your account password was successfully changed.",
                    "system",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                db.commit()
                print(f"Notification created for user_id: {user_id}")
            except Exception as e:
                print(f"Error creating notification: {e}")
                # Continue even if notification creation fails

            # Send confirmation email
            try:
                send_result = send_password_change_confirmation_email(user["email"])
                print(f"Confirmation email result: {send_result}")
            except Exception as e:
                print(f"Error sending confirmation email: {e}")
                # Continue even if email sending fails

            return jsonify({"success": True, "message": "Password changed successfully"}), 200

    except Exception as e:
        print(f"Error in change_password route: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


def send_password_change_confirmation_email(email):
    """Send confirmation email for password change"""
    subject = "Der-volt - Password Changed Successfully"
    body = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                text-align: center;
            }}
            .container {{
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                width: 80%;
                margin: auto;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }}
            h2 {{
                color: #2E86C1;
            }}
            .success {{
                font-size: 18px;
                font-weight: bold;
                color: #27AE60;
                margin: 20px 0;
            }}
            .footer {{
                font-size: 12px;
                color: #888;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🔒 Password Changed Successfully</h2>
            <p>Hello,</p>
            <p>Your password for Der-Volt account has been successfully changed.</p>
            <p class="success">Your account is now secure with the new password.</p>
            <p>If you did not make this change, please contact our support team immediately.</p>
            <p>Thank you,<br><b>Der-Volt Team</b></p>
            <p class="footer">This is an automated email. Please do not reply.</p>
        </div>
    </body>
    </html>
    """
    # Use the same sending logic from email_service
    try:
        # Create the email message
        msg = MIMEMultipart()
        msg["From"] = "no-reply@dervolt.site"
        msg["To"] = email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "html"))

        # For development, just print to console
        print(f"\n----- PASSWORD CHANGE CONFIRMATION EMAIL -----")
        print(f"To: {email}")
        print(f"Subject: {subject}")
        print(f"----- END EMAIL -----\n")

        # In production, use the SMTP settings from email_service.py
        if os.environ.get('FLASK_ENV') == 'production':
            from email_service import SMTP_SERVER, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, email, msg.as_string())
            server.quit()

        return True
    except Exception as e:
        print(f"Error sending confirmation email: {str(e)}")
        traceback.print_exc()
        return False

# API endpoint to get account data for a user (for real-time updates)
@app.route("/api/accounts/<int:user_id>")
@login_required
def get_user_accounts_api(user_id):
    """
    API endpoint to fetch user accounts with balances.
    """
    # Security check - only allow users to see their own accounts
    current_user_id = session.get('user_id')
    if current_user_id != user_id:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    try:
        # First, update all account balances to ensure they're accurate
        update_account_balances()
        
        with get_db() as db:
            cursor = db.cursor()

            # Add cache-busting query parameter support
            cache_bust = request.args.get('nocache', '')
            force_refresh = request.args.get('forceRefresh', '')
            
            if cache_bust or force_refresh:
                print(f"Cache-busting request detected: nocache={cache_bust}, forceRefresh={force_refresh}")

            # Fetch accounts with stored balances (rather than calculating on the fly)
            cursor.execute("""
                SELECT * FROM accounts WHERE user_id = ?
            """, (user_id,))

            accounts = cursor.fetchall()
            
            # Debug info only visible in server logs, not to users
            print(f"API: Fetched account information for user_id {user_id}:")
            for account in accounts:
                account_id = account['id']
                balance = account['balance']
                print(f"  - Account {account_id}: balance = {balance}")

            # Format accounts for JSON serialization
            accounts_json = []
            for account in accounts:
                account_dict = dict(account)
                account_dict['balance'] = float(account_dict['balance']) if account_dict['balance'] is not None else 0
                accounts_json.append(account_dict)

            return jsonify({"success": True, "accounts": accounts_json})

    except Exception as e:
        print(f"API error: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

def update_account_balances():
    """
    Update the balance column in the accounts table for all accounts,
    based on the sum of all completed deposit and withdrawal transactions.
    Also ensures balances never go below zero.
    """
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # First, make sure the balance column exists
            try:
                cursor.execute("SELECT balance FROM accounts LIMIT 1")
            except sqlite3.OperationalError:
                # If the column doesn't exist, add it
                cursor.execute("ALTER TABLE accounts ADD COLUMN balance REAL DEFAULT 0")
                db.commit()
                print("Added balance column to accounts table")
            
            # Get all accounts
            cursor.execute("SELECT id, user_id FROM accounts")
            accounts = cursor.fetchall()
            
            updated_count = 0
            for account in accounts:
                account_id = account['id']
                
                # Calculate balance from transactions
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN transaction_type = 'deposit' AND status = 'completed' THEN amount ELSE 0 END), 0) as deposits,
                        COALESCE(SUM(CASE WHEN transaction_type = 'withdrawal' AND status = 'completed' THEN amount ELSE 0 END), 0) as withdrawals
                    FROM transactions 
                    WHERE account_id = ?
                """, (account_id,))
                
                result = cursor.fetchone()
                deposits = result['deposits'] if result and result['deposits'] is not None else 0
                withdrawals = result['withdrawals'] if result and result['withdrawals'] is not None else 0
                
                # Calculate balance, ensuring it never goes negative
                calculated_balance = max(0, deposits - withdrawals)
                
                # Update the account balance
                cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?", (calculated_balance, account_id))
                updated_count += 1
            
            db.commit()
            print(f"Updated {updated_count} account balances in the database")
            return True
    except Exception as e:
        print(f"Error updating account balances: {e}")
        return False

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash("Please log in to access the admin area.", "error")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Function to get current admin ID
def get_current_admin_id():
    admin_id = session.get('admin_id')
    if admin_id == '':
        return None
    return admin_id

def get_admin_data(admin_id):
    """Get admin data as a dictionary for templates"""
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM admins WHERE id = ?", (admin_id,))
        admin = cursor.fetchone()
        if admin:
            return dict(admin)
        return None

# Function to log admin activity
def log_admin_activity(admin_id, action, details=None):
    # List of important actions that should be logged
    important_actions = [
        # Authentication actions
        "login", "logout", "failed_login",
        
        # User management actions
        "block_user", "unblock_user", "reset_password", "edit_user",
        
        # Admin management actions
        "add_admin", "edit_admin", "activate_admin", "deactivate_admin",
        
        # Transaction actions
        "transaction_approve", "transaction_reject",
        
        # System settings
        "update_settings", "maintenance_mode_toggle",
        
        # Security events
        "send_notification", "security_alert"
    ]
    
    # Check if the action is in our list of important actions to log
    action_type = action.lower().split('_')[0] if '_' in action else action.lower()
    
    if action_type in important_actions or any(important in action.lower() for important in important_actions):
        try:
            with get_db() as db:
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO admin_logs (admin_id, action, details, ip_address, user_agent, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, (
                    admin_id,
                    action,
                    details,
                    request.remote_addr,
                    request.user_agent.string if request.user_agent else None
                ))
                db.commit()
        except Exception as e:
            print(f"Error logging admin activity: {e}")

# Admin routes
@app.route("/admin/login")
def admin_login():
    # If already logged in, redirect to admin dashboard
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template("admin/login.html")

@app.route("/admin/login", methods=["POST"])
def admin_login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
        admin = cursor.fetchone()
        
        if not admin:
            flash("Username or password is incorrect", "error")
            return redirect(url_for('admin_login'))
        
        if check_password_hash(admin['password'], password):
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            session['admin_role'] = admin['role']
            session['last_activity'] = time.time()
            
            log_admin_activity(admin['id'], "login", f"Admin {username} logged in successfully from {request.remote_addr}")
            
            return redirect(url_for('admin_dashboard'))
        else:
            # Log failed login attempts as security measure
            log_admin_activity(admin['id'] if admin else None, "failed_login", f"Failed login attempt for username {username} from {request.remote_addr}")
            flash("Username or password is incorrect", "error")
            return redirect(url_for('admin_login'))

@app.route("/admin/logout")
def admin_logout():
    # Log the activity before clearing the session
    admin_username = session.get('admin_username', 'Unknown')
    log_admin_activity(session.get('admin_id'), "logout", f"Admin {admin_username} logged out from {request.remote_addr}")
    
    # Clear the session
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    session.pop('admin_role', None)
    session.pop('last_activity', None)
    
    flash("You have been logged out", "success")
    return redirect(url_for('admin_login'))

@app.route("/admin")
@admin_required
def admin_dashboard():
    # Log admin activity
    admin_id = get_current_admin_id()
    log_admin_activity(admin_id, "Viewed admin dashboard")

    # Get admin data
    admin_data = get_admin_data(admin_id)

    # Get total users count
    with get_db() as db:
        cursor = db.cursor()

        # Total users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        # User growth (last 30 days)
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE created_at >= datetime('now', '-30 days')
        """)
        new_users_month = cursor.fetchone()[0]

        user_growth = round((new_users_month / total_users) * 100, 1) if total_users > 0 else 0

        # For System Metrics card
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions 
            WHERE transaction_type = 'deposit' AND status = 'completed'
        """)
        total_deposits = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM transactions 
            WHERE created_at >= datetime('now', '-7 days')
        """)
        transaction_volume = cursor.fetchone()[0]

        new_users_rate = round((new_users_month / max(1, total_users)) * 100, 1)

        # Active users (last 24 hours)
        active_users = 0
        prev_active_users = 1  # Default to avoid division by zero
        active_users_growth = 0

        # try with user_activity_logs table first (preferred)
        try:
            # Try with user_activity_logs table first (preferred)
            try:
                cursor.execute("""
                    SELECT COUNT(DISTINCT user_id) FROM user_activity_logs 
                    WHERE created_at >= datetime('now', '-1 day')
                """)
                active_users = cursor.fetchone()[0]

                # Active users growth
                cursor.execute("""
                    SELECT COUNT(DISTINCT user_id) FROM user_activity_logs 
                    WHERE created_at >= datetime('now', '-2 days') 
                    AND created_at < datetime('now', '-1 day')
                """)
                prev_active_users = cursor.fetchone()[0] or 1  # Avoid division by zero
            except sqlite3.OperationalError as e:
                # Fall back to activity_logs if user_activity_logs doesn't exist
                if "no such table: user_activity_logs" in str(e):
                    cursor.execute("""
                        SELECT COUNT(DISTINCT user_id) FROM activity_logs 
                        WHERE timestamp >= datetime('now', '-1 day')
                    """)
                    active_users = cursor.fetchone()[0]

                    # Active users growth
                    cursor.execute("""
                        SELECT COUNT(DISTINCT user_id) FROM activity_logs 
                        WHERE timestamp >= datetime('now', '-2 days') 
                        AND timestamp < datetime('now', '-1 day')
                    """)
                    prev_active_users = cursor.fetchone()[0] or 1  # Avoid division by zero
                else:
                    raise

            active_users_growth = round(((active_users - prev_active_users) / max(prev_active_users, 1)) * 100, 1)
        except sqlite3.OperationalError as e:
            # Handle missing activity_logs table
            if "no such table: activity_logs" in str(e):
                print("Warning: neither user_activity_logs nor activity_logs table exists. Using default values for active users.")
                active_users = 0
                prev_active_users = 1
                active_users_growth = 0
            else:
                # Re-raise other database errors
                raise

        # Total transactions (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) FROM transactions 
            WHERE created_at >= datetime('now', '-1 day')
        """)
        total_transactions = cursor.fetchone()[0]

        # Revenue (current month)
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions 
            WHERE created_at >= datetime('now', 'start of month')
            AND status = 'completed'
        """)
        revenue = cursor.fetchone()[0]

        # Get recent admin activities
        try:
            cursor.execute("""
                SELECT a.id, a.username, aa.action, aa.timestamp
                FROM admin_activity_logs aa
                JOIN admins a ON aa.admin_id = a.id
                ORDER BY aa.timestamp DESC
                LIMIT 5
            """)
            admin_activities = cursor.fetchall()
        except sqlite3.OperationalError as e:
            if "no such table: admin_activity_logs" in str(e):
                print("Warning: admin_activity_logs table doesn't exist. Using empty list.")
                admin_activities = []
            else:
                # Re-raise other database errors
                raise

        # Format admin activities for the dashboard
        activity_logs = []
        for activity in admin_activities:
            activity_logs.append({
                'admin_name': activity['username'] if 'username' in activity else 'Admin',
                'action': activity['action'] if 'action' in activity else 'performed an action',
                'timestamp': activity['timestamp'] if 'timestamp' in activity else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'status_color': 'green',
                'status': 'SUCCESS'
            })

        # Get notification count for admin
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM admin_notifications
                WHERE admin_id = ? AND read = 0
            """, (admin_id,))
            notification_count = cursor.fetchone()[0]
        except sqlite3.OperationalError as e:
            if "no such table: admin_notifications" in str(e):
                print("Warning: admin_notifications table doesn't exist. Using default value.")
                notification_count = 0
            else:
                # Re-raise other database errors
                raise

        # Total platform balance (sum of all account balances)
        cursor.execute("""
            SELECT COALESCE(SUM(balance), 0) FROM accounts
            WHERE is_active = 1
        """)
        total_platform_balance = cursor.fetchone()[0]

    # Prepare the data for the template
    dashboard_data = {
        'admin': admin_data,
        'total_users': total_users,
        'user_growth': user_growth,
        'active_users': active_users,
        'active_users_growth': active_users_growth,
        'total_transactions': total_transactions,
        'transaction_count': total_transactions,  # For today's transactions
        'revenue': revenue,
        'admin_activities': admin_activities,
        'activity_logs': activity_logs,
        'notification_count': notification_count,
        'total_deposits': total_deposits,
        'transaction_volume': transaction_volume,
        'new_users_rate': new_users_rate,
        'system_health': get_system_health(),
        'total_platform_balance': total_platform_balance
    }

    return render_template('admin/dashboard.html', **dashboard_data)

@app.route("/admin/settings")
@admin_required
def admin_settings():
    admin_id = get_current_admin_id()

    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM system_settings ORDER BY key")
        settings_rows = cursor.fetchall()

        # Convert to a dictionary for easier access in the template
        settings = {}
        for row in settings_rows:
            row_dict = dict(row)
            settings[row_dict['key']] = row_dict['value']

    # Get current forex rates for display
    forex_rate, forex_updated_at = get_latest_forex_rate()
    deposit_rate, _ = get_deposit_rate()
    withdrawal_rate, _ = get_withdrawal_rate()

    # Log the activity
    log_admin_activity(admin_id, 'view_settings', 'Viewed system settings')

    return render_template("admin/settings.html",
        admin=get_admin_data(admin_id),
        settings=settings,
        forex_rate=forex_rate,
        deposit_rate=deposit_rate,
        withdrawal_rate=withdrawal_rate,
        forex_updated_at=forex_updated_at)

@app.route('/admin/broadcast')
@admin_required
def admin_broadcast():
    """Admin broadcast page for sending messages to users."""
    admin_id = get_current_admin_id()
    print(f"Admin ID: {admin_id}")
    
    # Use get_admin_data instead of get_admin_by_id
    admin = get_admin_data(admin_id)
    print(f"Admin object: {admin}")
    
    log_admin_activity(admin_id, f"viewed broadcast page")
    
    return render_template('admin/broadcast.html', admin=admin)

@app.route('/admin/broadcast/send', methods=['POST'])
@admin_required
def admin_send_broadcast():
    """Handle sending broadcast messages to users."""
    admin_id = get_current_admin_id()
    print(f"Send Broadcast - Admin ID: {admin_id}")
    
    # Get form data
    title = request.form.get('message-title')
    content = request.form.get('message-content')
    category = request.form.get('message-category')
    send_email = request.form.get('send-email') == 'on'
    send_notification = request.form.get('send-notification') == 'on'
    schedule_time = request.form.get('schedule-time')
    
    # Validate required fields
    if not title or not content:
        flash('Title and content are required', 'error')
        return redirect(url_for('admin_broadcast'))
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Get active users (users who have logged in within the last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "SELECT id, email FROM users WHERE last_login > ? OR last_activity > ?", 
            (thirty_days_ago, thirty_days_ago)
        )
        active_users = cursor.fetchall()
        
        # Create broadcast record
        cursor.execute(
            "INSERT INTO broadcasts (admin_id, title, content, category, created_at, scheduled_at) VALUES (?, ?, ?, ?, ?, ?)",
            (admin_id, title, content, category, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), schedule_time)
        )
        broadcast_id = cursor.lastrowid
        
        # Send notifications and emails
        for user in active_users:
            user_id = user['id']
            
            # Add to notifications
            if send_notification:
                cursor.execute(
                    "INSERT INTO notifications (user_id, title, message, notification_type, is_read, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, title, content, category, 0, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
            
            # Send email
            if send_email and user['email']:
                # In a real application, you would use an email service here
                try:
                    send_email_to_user(user['email'], title, content)
                except Exception as e:
                    print(f"Failed to send email to {user['email']}: {str(e)}")
        
        db.commit()
        log_admin_activity(admin_id, f"sent broadcast: {title}")
        
        flash(f'Broadcast sent to {len(active_users)} users', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error sending broadcast: {str(e)}', 'error')
        print(f"Broadcast error: {str(e)}")
    
    return redirect(url_for('admin_broadcast'))

@app.route("/admin/settings/update", methods=["POST"])
@admin_required
def admin_update_settings():
    admin_id = get_current_admin_id()
    section = request.form.get('section', '')
    settings_data = request.form.to_dict()

    # Remove the section field from the settings data
    if 'section' in settings_data:
        del settings_data['section']

    # Handle checkbox fields - if they're not in the form data, they're unchecked
    checkbox_fields = ['maintenance_mode', 'mpesa_enabled', 'bank_enabled', 'card_enabled',
        'require_otp_password_change', 'require_otp_large_withdrawal']

    for checkbox in checkbox_fields:
        if checkbox not in settings_data and section in ['general', 'transactions', 'security']:
            # If a checkbox from the current section is not in the form data, set it to '0' (off)
            settings_data[checkbox] = '0'

    with get_db() as db:
        cursor = db.cursor()

        # Debug log
        print(f"Updating settings for section: {section}")
        print(f"Settings data: {settings_data}")

        for key, value in settings_data.items():
            # Check if setting exists
            cursor.execute("SELECT * FROM system_settings WHERE key = ?", (key,))
            setting = cursor.fetchone()

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if setting:
                # Update existing setting
                print(f"Updating setting: {key} = {value}")
                cursor.execute("""
                    UPDATE system_settings 
                    SET value = ?, updated_at = ?
                    WHERE key = ?


                """, (value, current_time, key))
            else:
                # Create new setting
                print(f"Creating new setting: {key} = {value}")
                cursor.execute("""
                    INSERT INTO system_settings (key, value, created_at, updated_at)
                    VALUES (?, ?, ?, ?)


                """, (key, value, current_time, current_time))

        db.commit()

    # Special handling for forex settings
    if section == 'forex':
        # If API key was updated, try to fetch a new rate
        if 'apilayer_api_key' in settings_data:
            try:
                # Fetch new rate with the updated API key
                new_rate = fetch_forex_rate()
                if new_rate:
                    flash(f"Successfully fetched new forex rate: {new_rate} KES/USD", "success")
                else:
                    flash("API key updated, but unable to fetch a new rate. Please check the key and try again.", "warning")
            except Exception as e:
                flash(f"Error fetching new rate: {str(e)}", "error")

    # Log the activity
    log_admin_activity(admin_id, 'update_settings', f'Updated system settings section: {section}')

    flash(f"{section.capitalize()} settings updated successfully", "success")
    return redirect(url_for('admin_settings'))

@app.route("/admin/logs")
@admin_required
def admin_logs():
    current_admin_id = get_current_admin_id()

    # Get filter parameters
    filter_admin_id = request.args.get('admin_id', '')
    action = request.args.get('action', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    log_type = request.args.get('type', '')  # Added parameter for log type

    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    # Initialize variables before the with block
    total_logs = 0
    logs = []
    admins_list = []
    title = "Admin Activity Logs"

    # Set title based on log type
    if log_type == 'error':
        title = "Error Logs"
    elif log_type == 'security':
        title = "Security Logs"

    with get_db() as db:
        cursor = db.cursor()

        # Fetch all admins for the dropdown
        cursor.execute("SELECT id, username, role FROM admins")
        admins = cursor.fetchall()
        admins_list = [dict(a) for a in admins]

        # Build query conditions dynamically
        conditions = []
        params = []
        
        # Different queries based on log type
        if log_type == 'error':
            base_query = """
                SELECT id, error_type as action, error_message as details, severity, 
                       user_id as admin_id, created_at, 'error' as log_type
                FROM error_logs
            """
        elif log_type == 'security':
            base_query = """
                SELECT id, event_type as action, description as details, threat_level as severity,
                       user_id as admin_id, created_at, 'security' as log_type
                FROM security_logs
            """
        else:
            # Default admin logs query
            base_query = """
                SELECT al.*, a.username, a.role, 'admin' as log_type
                FROM admin_logs al
                JOIN admins a ON al.admin_id = a.id
            """

        if filter_admin_id and log_type not in ['error', 'security']:
            conditions.append("al.admin_id = ?")
            params.append(filter_admin_id)

        if action and log_type not in ['error', 'security']:
            conditions.append("al.action = ?")
            params.append(action)
        elif action and log_type == 'error':
            conditions.append("error_type = ?")
            params.append(action)
        elif action and log_type == 'security':
            conditions.append("event_type = ?")
            params.append(action)

        if date_from:
            if log_type not in ['error', 'security']:
                conditions.append("DATE(al.created_at) >= DATE(?)")
            else:
                conditions.append("DATE(created_at) >= DATE(?)")
            params.append(date_from)

        if date_to:
            if log_type not in ['error', 'security']:
                conditions.append("DATE(al.created_at) <= DATE(?)")
            else:
                conditions.append("DATE(created_at) <= DATE(?)")
            params.append(date_to)

        # Add WHERE clause if there are conditions
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        # Query for logs with pagination
        query = base_query + " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        try:
            cursor.execute(query, params)
            logs = cursor.fetchall()
            
            # Count total logs for pagination (with same filters)
            if log_type == 'error':
                count_query = "SELECT COUNT(*) as count FROM error_logs"
            elif log_type == 'security':
                count_query = "SELECT COUNT(*) as count FROM security_logs"
            else:
                count_query = "SELECT COUNT(*) as count FROM admin_logs al"
                
            count_params = []

            if conditions:
                count_query += " WHERE " + " AND ".join(conditions)
                count_params = params[:-2]  # Remove the LIMIT and OFFSET params

            cursor.execute(count_query, count_params)
            total_logs = cursor.fetchone()['count']
            
        except sqlite3.OperationalError as e:
            # Handle the case where tables don't exist
            if "no such table" in str(e):
                logs = []
                total_logs = 0
                flash(f"The requested log type is not available: {str(e)}", "error")
            else:
                # Re-raise other operational errors
                raise

        # Convert to dictionaries for the template
        logs = [dict(log) for log in logs]

        # Log the activity
        log_admin_activity(current_admin_id, 'view_logs', f'Viewed {log_type if log_type else "admin"} logs with filters')

    # Calculate total pages outside the with block, using the variables set within
    total_pages = (total_logs + per_page - 1) // per_page if total_logs > 0 else 1

    return render_template("admin/logs.html",
        admin=get_admin_data(current_admin_id),
                          logs=logs,
                          total_logs=total_logs,
                          page=page,
                          total_pages=total_pages,
                          admins=admins_list,
                          admin_id=filter_admin_id,
                          action=action,
                          date_from=date_from,
                          date_to=date_to,
                          log_type=log_type,
                          title=title)

@app.route("/admin/admins")
@admin_required
def admin_manage_admins():
    admin_id = get_current_admin_id()

    # If admin_id is None, redirect to login
    if admin_id is None:
        flash("Please log in to access the admin panel", "error")
        return redirect(url_for('admin_login'))

    with get_db() as db:
        cursor = db.cursor()

        # Get current admin role
        cursor.execute("SELECT role FROM admins WHERE id = ?", (admin_id,))
        current_admin_role = cursor.fetchone()['role']

        # Only super_admin can manage admins
        if current_admin_role != 'super_admin':
            flash("You don't have permission to manage admins", "error")
            return redirect(url_for('admin_dashboard'))

        # Get all admins
        cursor.execute("SELECT * FROM admins ORDER BY username")
        admins_rows = cursor.fetchall()

        # Convert to dictionaries for the template
        admins = [dict(a) for a in admins_rows]

        # Count total admins
        cursor.execute("SELECT COUNT(*) as count FROM admins")
        total_admins = cursor.fetchone()['count']

        # Log the activity
        log_admin_activity(admin_id, 'view_admins', 'Viewed admin management page')

    return render_template("admin/admins.html",
        admin=get_admin_data(admin_id),
                          admins=admins,
                          total_admins=total_admins)

@app.route("/admin/admins/add", methods=["GET", "POST"])
@admin_required
def admin_add_admin():
    admin_id = get_current_admin_id()

    with get_db() as db:
        cursor = db.cursor()

        # Get current admin role
        cursor.execute("SELECT role FROM admins WHERE id = ?", (admin_id,))
        current_admin_role = cursor.fetchone()['role']

        # Only super_admin can add admins
        if current_admin_role != 'super_admin':
            flash("You don't have permission to add admins", "error")
            return redirect(url_for('admin_dashboard'))

    if request.method == "POST":
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')

        # Validate input
        if not all([username, email, password, confirm_password, role]):
            flash("All fields are required", "error")
            return render_template("admin/add_admin.html", admin=get_admin_data(admin_id))

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("admin/add_admin.html", admin=get_admin_data(admin_id))

        if len(password) < 8:
            flash("Password must be at least 8 characters long", "error")
            return render_template("admin/add_admin.html", admin=get_admin_data(admin_id))

        with get_db() as db:
            cursor = db.cursor()

            # Check if username or email already exists
            cursor.execute("SELECT * FROM admins WHERE username = ? OR email = ?", (username, email))
            existing_admin = cursor.fetchone()

            if existing_admin:
                flash("Username or email already exists", "error")
                return render_template("admin/add_admin.html", admin=get_admin_data(admin_id))

            # Create new admin
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO admins (username, email, password, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)


            """, (
                username,
                email,
                generate_password_hash(password),
                role,
                current_time,
                current_time
            ))
            db.commit()

            # Log the activity
            log_admin_activity(admin_id, "add_admin", f"Added new admin {username} with role {role}")

            flash("Admin added successfully", "success")
            return redirect(url_for('admin_manage_admins'))

    return render_template("admin/add_admin.html", admin=get_admin_data(admin_id))

@app.route("/admin/admins/edit/<int:admin_id>", methods=["POST"])
@admin_required
def admin_edit_admin(admin_id):
    current_admin_id = get_current_admin_id()

    with get_db() as db:
        cursor = db.cursor()

        # Get current admin role
        cursor.execute("SELECT role FROM admins WHERE id = ?", (current_admin_id,))
        current_admin_role = cursor.fetchone()['role']

        # Only super_admin can edit admins
        if current_admin_role != 'super_admin':
            flash("You don't have permission to edit admins", "error")
            return redirect(url_for('admin_dashboard'))

        # Make sure admin exists
        cursor.execute("SELECT * FROM admins WHERE id = ?", (admin_id,))
        admin_to_edit = cursor.fetchone()

        if not admin_to_edit:
            flash("Admin not found", "error")
            return redirect(url_for('admin_manage_admins'))

        # Make sure we're not editing a super_admin if we're not one
        if admin_to_edit['role'] == 'super_admin' and current_admin_role != 'super_admin':
            flash("You don't have permission to edit this admin", "error")
            return redirect(url_for('admin_manage_admins'))

        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')

        # Validate input
        if not all([username, email, role]):
            flash("All fields are required", "error")
            return redirect(url_for('admin_manage_admins'))

        # Check if username or email already exists for other admins
        cursor.execute("SELECT * FROM admins WHERE (username = ? OR email = ?) AND id != ?", (username, email, admin_id))
        existing_admin = cursor.fetchone()

        if existing_admin:
            flash("Username or email already exists", "error")
            return redirect(url_for('admin_manage_admins'))

        # Update admin
        cursor.execute("""
            UPDATE admins 
            SET username = ?, email = ?, role = ?, updated_at = ?
            WHERE id = ?


        """, (
            username,
            email,
            role,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            admin_id
        ))
        db.commit()

        # Parse and update permissions if applicable
        permissions = request.form.getlist('permissions')
        if permissions:
            permissions_str = ','.join(permissions)
            cursor.execute("""
                UPDATE admins 
                SET permissions = ?
                WHERE id = ?


            """, (permissions_str, admin_id))
            db.commit()

        # Log the activity
        log_admin_activity(current_admin_id, "edit_admin", f"Edited admin {username} (ID: {admin_id})")

        flash("Admin updated successfully", "success")
        return redirect(url_for('admin_manage_admins'))

@app.route("/admin/admins/activate/<int:admin_id>", methods=["POST"])
@admin_required
def admin_activate_admin(admin_id):
    current_admin_id = get_current_admin_id()

    with get_db() as db:
        cursor = db.cursor()

        # Get current admin role
        cursor.execute("SELECT role FROM admins WHERE id = ?", (current_admin_id,))
        current_admin_role = cursor.fetchone()['role']

        # Only super_admin can activate admins
        if current_admin_role != 'super_admin':
            flash("You don't have permission to activate admins", "error")
            return redirect(url_for('admin_dashboard'))

        # Make sure admin exists
        cursor.execute("SELECT * FROM admins WHERE id = ?", (admin_id,))
        admin_to_activate = cursor.fetchone()

        if not admin_to_activate:
            flash("Admin not found", "error")
            return redirect(url_for('admin_manage_admins'))

        # Activate admin
        cursor.execute("""
            UPDATE admins 
            SET is_active = 1, updated_at = ?
            WHERE id = ?


        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            admin_id
        ))
        db.commit()

        # Log the activity
        log_admin_activity(current_admin_id, "activate_admin", f"Activated admin ID: {admin_id}")

        flash("Admin activated successfully", "success")
        return redirect(url_for('admin_manage_admins'))

@app.route("/admin/admins/deactivate/<int:admin_id>", methods=["POST"])
@admin_required
def admin_deactivate_admin(admin_id):
    current_admin_id = get_current_admin_id()

    with get_db() as db:
        cursor = db.cursor()

        # Get current admin role
        cursor.execute("SELECT role FROM admins WHERE id = ?", (current_admin_id,))
        current_admin_role = cursor.fetchone()['role']

        # Only super_admin can deactivate admins
        if current_admin_role != 'super_admin':
            flash("You don't have permission to deactivate admins", "error")
            return redirect(url_for('admin_dashboard'))

        # Make sure admin exists
        cursor.execute("SELECT * FROM admins WHERE id = ?", (admin_id,))
        admin_to_deactivate = cursor.fetchone()

        if not admin_to_deactivate:
            flash("Admin not found", "error")
            return redirect(url_for('admin_manage_admins'))

        # Prevent deactivating yourself
        if int(admin_id) == int(current_admin_id):
            flash("You cannot deactivate your own account", "error")
            return redirect(url_for('admin_manage_admins'))

        # Deactivate admin
        cursor.execute("""
            UPDATE admins 
            SET is_active = 0, updated_at = ?
            WHERE id = ?


        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            admin_id
        ))
        db.commit()

        # Log the activity
        log_admin_activity(current_admin_id, "deactivate_admin", f"Deactivated admin ID: {admin_id}")

        flash("Admin deactivated successfully", "success")
        return redirect(url_for('admin_manage_admins'))

@app.route("/admin/user/<int:user_id>/send-notification", methods=["POST"])
@admin_required
def admin_send_notification(user_id):
    admin_id = get_current_admin_id()

    # Get form data
    title = request.form.get('title')
    message = request.form.get('message')
    notification_type = request.form.get('notification_type', 'admin')

    # Validate input
    if not title or not message:
        flash("Title and message are required", "error")
        return redirect(url_for('admin_user_detail', user_id=user_id))

    # Insert notification
    with get_db() as db:
        cursor = db.cursor()
        try:
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()

            if not user:
                flash("User not found", "error")
                return redirect(url_for('admin_users'))

            # Insert notification
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, notification_type, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                title,
                message,
                notification_type,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            db.commit()

            # Log the activity
            log_admin_activity(admin_id, 'send_notification', f'Sent notification to user ID: {user_id}')

            flash("Notification sent successfully", "success")


        except Exception as e:

            print(f"Error occurred: {e}")
        except Exception as e:
            flash(f"Error sending notification: {str(e)}", "error")

    return redirect(url_for('admin_user_detail', user_id=user_id))
@app.route("/admin/user/<int:user_id>/block", methods=["POST"])
@admin_required
def admin_block_user(user_id):
    try:
        admin_id = get_current_admin_id()
        reason = request.form.get('reason', 'No reason provided')
        
        with get_db() as db:
            cursor = db.cursor()
            # Get user info for logging
            cursor.execute("SELECT first_name, last_name, email FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            user_name = f"{user['first_name']} {user['last_name']}" if user else f"User ID: {user_id}"
            
            # Update user status
            cursor.execute("UPDATE users SET is_active = 0, blocked_reason = ?, blocked_at = CURRENT_TIMESTAMP WHERE id = ?", 
                          (reason, user_id))
            db.commit()
            
            # Log the action
            log_admin_activity(admin_id, 'block_user', f'Blocked user: {user_name} (ID: {user_id}). Reason: {reason}')
            
            flash(f"User {user_name} has been blocked successfully.", "success")
            return redirect(url_for('admin_user_detail', user_id=user_id))
            
    except Exception as e:
        flash(f"Error blocking user: {str(e)}", "error")
        return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route("/admin/user/<int:user_id>/unblock", methods=["POST"])
@admin_required
def admin_unblock_user(user_id):
    try:
        admin_id = get_current_admin_id()
        
        with get_db() as db:
            cursor = db.cursor()
            # Get user info for logging
            cursor.execute("SELECT first_name, last_name, email FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            user_name = f"{user['first_name']} {user['last_name']}" if user else f"User ID: {user_id}"
            
            # Update user status
            cursor.execute("UPDATE users SET is_active = 1, blocked_reason = NULL, blocked_at = NULL WHERE id = ?", (user_id,))
            db.commit()
            
            # Log the action
            log_admin_activity(admin_id, 'unblock_user', f'Unblocked user: {user_name} (ID: {user_id})')
            
            flash(f"User {user_name} has been unblocked successfully.", "success")
            return redirect(url_for('admin_user_detail', user_id=user_id))
            
    except Exception as e:
        flash(f"Error unblocking user: {str(e)}", "error")
        return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route("/admin/user/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def admin_reset_user_password(user_id):
    try:
        admin_id = get_current_admin_id()
        
        with get_db() as db:
            cursor = db.cursor()
            # Get user info
            cursor.execute("SELECT first_name, last_name, email FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                flash("User not found", "error")
                return redirect(url_for('admin_users'))
                
            user_name = f"{user['first_name']} {user['last_name']}"
            
            # Generate a temporary password
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            hashed_password = generate_password_hash(temp_password)
            
            # Update user's password
            cursor.execute("UPDATE users SET password_hash = ?, password_reset_required = 1 WHERE id = ?", 
                          (hashed_password, user_id))
            db.commit()
            
            # Send email to user with temporary password
            email_sent = send_password_reset_email(user['email'], user_name, temp_password, send_email_to_user)
            
            # Log admin activity
            log_admin_activity(admin_id, 'reset_password', f'Reset password for user: {user_name} (ID: {user_id}, Email: {user["email"]})')
            
            if email_sent:
                flash(f"Password for {user_name} has been reset. Temporary password was sent to their email: {user['email']}", "success")
            else:
                flash(f"Password for {user_name} has been reset, but failed to send email. Temporary password: {temp_password}", "warning")
                
            return redirect(url_for('admin_user_detail', user_id=user_id))
            
    except Exception as e:
        flash(f"Error resetting password: {str(e)}", "error")
        return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route("/admin/users")
@admin_required
def admin_users():
    admin_id = get_current_admin_id()
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    with get_db() as db:
        cursor = db.cursor()

        if search:
            search_term = f"%{search}%"
            cursor.execute("""
                SELECT u.*, COUNT(a.id) as account_count
                FROM users u
                LEFT JOIN accounts a ON u.id = a.user_id
                WHERE u.first_name LIKE ? OR u.last_name LIKE ? OR u.email LIKE ? OR u.phone_number LIKE ?
                GROUP BY u.id
                ORDER BY u.created_at DESC
                LIMIT ? OFFSET ?


            """, (search_term, search_term, search_term, search_term, per_page, offset))
        else:
            cursor.execute("""
                SELECT u.*, COUNT(a.id) as account_count
                FROM users u
                LEFT JOIN accounts a ON u.id = a.user_id
                GROUP BY u.id
                ORDER BY u.created_at DESC
                LIMIT ? OFFSET ?


            """, (per_page, offset))

        users = cursor.fetchall()

        # Get total count for pagination
        cursor.execute("SELECT COUNT(*) as count FROM users" +
            (" WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR phone_number LIKE ?"
                      if search else ""),
                    (search_term, search_term, search_term, search_term) if search else ())
        total_users = cursor.fetchone()['count']

        total_pages = (total_users + per_page - 1) // per_page

        # Convert to dictionaries for the template
        users = [dict(user) for user in users]

        # Log the admin activity
        log_admin_activity(admin_id, 'view_users', f'Viewed users list with search: {search}')

        return render_template("admin/users.html",
            admin=get_admin_data(admin_id),
                              users=users,
                              total_users=total_users,
                              page=page,
                              total_pages=total_pages,
                              search=search)

@app.route("/admin/user/<int:user_id>")
@admin_required
def admin_user_detail(user_id):
    """
    Route to show user details
    """
    admin_id = get_current_admin_id()
    
    with get_db() as db:
        cursor = db.cursor()
        
        # Get user data
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash("User not found", "error")
            return redirect(url_for('admin_users'))
        
        # Convert to dict for template
        user = dict(user)
        
        # Get user's accounts
        cursor.execute("""
            SELECT * FROM accounts 
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        accounts = [dict(account) for account in cursor.fetchall()]
        
        # Get recent transactions
        cursor.execute("""
            SELECT t.* FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ?
            ORDER BY t.created_at DESC
            LIMIT 10
        """, (user_id,))
        transactions = [dict(tx) for tx in cursor.fetchall()]
        
        # Get user's last login timestamp from activity logs
        cursor.execute("""
            SELECT created_at 
            FROM user_activity_logs 
            WHERE user_id = ? AND action = 'login' 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (user_id,))
        last_login = cursor.fetchone()
        
        # Add last login timestamp to user data
        if last_login:
            user['last_login'] = last_login['created_at']
        else:
            user['last_login'] = 'Never'
        
        # Log admin activity
        log_admin_activity(admin_id, 'view_user_detail', f'Viewed user detail for ID: {user_id}')
        
        return render_template("admin/user_detail.html",
                              admin=get_admin_data(admin_id),
                              user=user,
                              accounts=accounts,
                              transactions=transactions)

@app.route("/admin/user/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_user_edit(user_id):
    """
    Route to edit user details
    """
    admin_id = get_current_admin_id()
    
    with get_db() as db:
        cursor = db.cursor()
        
        # Get user data
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash("User not found", "error")
            return redirect(url_for('admin_users'))
        
        # Convert to dict for template
        user = dict(user)
        
        if request.method == "POST":
            # Handle form submission
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            phone_number = request.form.get('phone_number')
            
            # Validate input
            if not all([first_name, last_name, email]):
                flash("All required fields must be filled out", "error")
                return render_template("admin/user_edit.html", 
                                      admin=get_admin_data(admin_id),
                                      user=user)
            
            # Check if email exists for other users
            cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id))
            if cursor.fetchone():
                flash("Email already exists for another user", "error")
                return render_template("admin/user_edit.html", 
                                      admin=get_admin_data(admin_id),
                                      user=user)
            
            # Update user
            try:
                cursor.execute("""
                    UPDATE users SET 
                    first_name = ?, 
                    last_name = ?, 
                    email = ?, 
                    phone_number = ?,
                    updated_at = datetime('now')
                    WHERE id = ?
                """, (first_name, last_name, email, phone_number, user_id))
                db.commit()
                
                # Log admin activity
                log_admin_activity(admin_id, 'edit_user', f'Edited user details for ID: {user_id}')
                
                flash("User details updated successfully", "success")
                return redirect(url_for('admin_user_detail', user_id=user_id))
            except Exception as e:
                db.rollback()
                flash(f"Error updating user: {str(e)}", "error")
        
        # For GET request, show edit form
        return render_template("admin/user_edit.html", 
                              admin=get_admin_data(admin_id),
                              user=user)

@app.route("/admin/user/<int:user_id>/transactions")
@admin_required
def admin_user_transactions(user_id):
    """
    Route to show all transactions for a user
    """
    admin_id = get_current_admin_id()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    with get_db() as db:
        cursor = db.cursor()
        
        # Verify user exists
        cursor.execute("SELECT id, first_name, last_name FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash("User not found", "error")
            return redirect(url_for('admin_users'))
        
        # Get user's accounts
        cursor.execute("SELECT id FROM accounts WHERE user_id = ?", (user_id,))
        account_ids = [account['id'] for account in cursor.fetchall()]
        
        if not account_ids:
            # No accounts, so no transactions
            return render_template("admin/user_transactions.html",
                                 admin=get_admin_data(admin_id),
                                 user=dict(user),
                                 transactions=[],
                                 total_transactions=0,
                                 page=page,
                                 total_pages=0)
        
        # Get transactions
        placeholders = ', '.join(['?' for _ in account_ids])
        cursor.execute(f"""
            SELECT t.*, a.account_number 
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE t.account_id IN ({placeholders})
            ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?
        """, (*account_ids, per_page, offset))
        
        transactions = [dict(tx) for tx in cursor.fetchall()]
        
        # Get total count for pagination
        cursor.execute(f"""
            SELECT COUNT(*) as count 
            FROM transactions 
            WHERE account_id IN ({placeholders})
        """, tuple(account_ids))
        
        total_transactions = cursor.fetchone()['count']
        total_pages = (total_transactions + per_page - 1) // per_page
        
        # Log admin activity
        log_admin_activity(admin_id, 'view_user_transactions', f'Viewed transactions for user ID: {user_id}')
        
        return render_template("admin/user_transactions.html",
                              admin=get_admin_data(admin_id),
                              user=dict(user),
                              transactions=transactions,
                              total_transactions=total_transactions,
                              page=page,
                              total_pages=total_pages)

# Function to log user activity
def log_user_activity(user_id, action, details=None):
    """Log user activity such as logins, transactions, etc."""
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO user_activity_logs (user_id, action, details, ip_address, user_agent, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (
                user_id,
                action,
                details,
                request.remote_addr,
                request.user_agent.string if request.user_agent else None
            ))
            db.commit()
    except Exception as e:
        print(f"Error logging user activity: {e}")

# Function to log system errors
def log_error(error_type, error_message, stack_trace=None, severity="medium", user_id=None):
    """Log system errors for admin review"""
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO error_logs (
                error_type, error_message, stack_trace, url, method, 
                user_id, ip_address, user_agent, severity, is_resolved, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, datetime('now'))


            """, (
                error_type,
                error_message,
                stack_trace,
                request.path if request else None,
                request.method if request else None,
                user_id,
                request.remote_addr if request else None,
                request.user_agent.string if request and request.user_agent else None,
                severity
            ))
            db.commit()


    except Exception as e:

        print(f"Error occurred: {e}")
    except Exception as e:
        print(f"Error logging system error: {e}")

# Function to log security events
def log_security_event(event_type, description, threat_level="low", user_id=None, admin_id=None):
    """
    Log a security-related event
    """
    ip_address = request.remote_addr if request else "127.0.0.1"
    status = "INFO"

    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO security_logs (
                event_type, description, threat_level, user_id, admin_id, ip_address, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))


            """, (
                event_type,
                description,
                threat_level,
                user_id,
                admin_id,
                ip_address,
                status
            ))
            db.commit()
    except Exception as e:
        print(f"Error logging security event: {e}")

def get_error_logs(limit=50):
    """Get the most recent error logs"""
    try:
        with get_db() as db:
            cursor = db.cursor()

            cursor.execute("""
                SELECT 
                id, error_type, error_message, severity, 
                user_id, created_at as timestamp, level
                FROM error_logs
                ORDER BY created_at DESC
                LIMIT ?


            """, (limit,))

            logs = cursor.fetchall()
            return [dict(log) for log in logs] if logs else []
    except Exception as e:
        print(f"Error retrieving error logs: {e}")
        return []

def get_security_logs(limit=50):
    """Get the most recent security logs"""
    try:
        with get_db() as db:
            cursor = db.cursor()

            cursor.execute("""
                SELECT 
                id, event_type as action, description, threat_level,
                user_id, admin_id, ip_address, status,
                created_at as timestamp,
                (SELECT username FROM users WHERE id = s.user_id) as user
                FROM security_logs s
                ORDER BY created_at DESC
                LIMIT ?


            """, (limit,))

            logs = cursor.fetchall()
            return [dict(log) for log in logs] if logs else []
    except Exception as e:
        print(f"Error retrieving security logs: {e}")
        return []

def get_system_health():
    """Get the latest system health data"""
    return {
        'status': 'unknown',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def record_system_health():
    """Record system health metrics for monitoring"""
    pass

@app.route("/admin/system-health")
@admin_required
def admin_system_health():
    # Log admin activity
    admin_id = get_current_admin_id()
    # Fix: combine ip and user agent into details parameter
    log_admin_activity(admin_id, "Viewed system health page", f"IP: {request.remote_addr}, User Agent: {request.user_agent.string}")

    # Get date range parameters
    date_from = request.args.get('date_from', None)
    date_to = request.args.get('date_to', None)

    # Set default date range if not provided (last 7 days)
    if not date_from:
        date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')

    try:
        # Convert string dates to datetime objects
        from_date = datetime.strptime(date_from, '%Y-%m-%d')
        to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)  # Include the entire day

        # Query for health checks within the date range
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                "SELECT * FROM system_health_checks WHERE created_at BETWEEN ? AND ? ORDER BY created_at DESC",
                (from_date.strftime('%Y-%m-%d %H:%M:%S'), to_date.strftime('%Y-%m-%d %H:%M:%S'))
            )
            health_checks = cursor.fetchall()
            health_checks = [dict(check) for check in health_checks]

            # If no health checks found, run one now
            if not health_checks:
                record_system_health()
                cursor.execute("SELECT * FROM system_health_checks ORDER BY created_at DESC")
                health_checks = cursor.fetchall()
                health_checks = [dict(check) for check in health_checks]

            # Get the latest health check
            latest_health = health_checks[0] if health_checks else None

            # Extract data for charts
            chart_dates = []
            cpu_data = []
            memory_data = []
            disk_data = []
            response_data = []
            connections_data = []

            # We need to reverse the list to show chronological order in charts
            for check in reversed(health_checks):
                # Format date for display
                check_date = datetime.strptime(check['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%m/%d %H:%M')
                chart_dates.append(check_date)
                cpu_data.append(check['cpu_usage'])
                memory_data.append(check['memory_usage'])
                disk_data.append(check['disk_usage'])
                response_data.append(check['response_time'])
                connections_data.append(check['active_connections'])

            # Get admin data for template
            admin = get_admin_data(admin_id)

            return render_template('admin/system_health.html',
                admin=admin,
                                  latest_health=latest_health,
                                  health_checks=health_checks,
                                  date_from=date_from,
                                  date_to=date_to,
                                  chart_dates=chart_dates,
                                  cpu_data=cpu_data,
                                  memory_data=memory_data,
                                  disk_data=disk_data,
                                  response_data=response_data,
                                  connections_data=connections_data)

    except Exception as e:
        flash(f"Error loading system health data: {str(e)}", "error")
        return redirect(url_for('admin_dashboard'))

@app.route("/admin/run-health-check", methods=["POST"])
@admin_required
def admin_run_health_check():
    admin_id = get_current_admin_id()

    # Log the admin activity
    log_admin_activity(admin_id, 'run_health_check', 'Manually ran system health check')

    # Run the health check
    record_system_health()

    flash("System health check completed successfully", "success")
    return redirect(url_for('admin_system_health'))

@app.route("/admin/transaction/reject/<reference>", methods=["POST"])
@admin_required
def admin_reject_transaction(reference):
    """Reject a pending transaction"""
    admin_id = get_current_admin_id()
    reason = request.form.get('reason', 'No reason provided')
    
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # Get transaction details first for logging
            cursor.execute("""
                SELECT t.*, u.first_name, u.last_name, u.email 
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.id
                WHERE t.reference = ?
            """, (reference,))
            
            transaction = cursor.fetchone()
            if not transaction:
                flash("Transaction not found", "error")
                return redirect(url_for('admin_transactions'))
            
            # Check if transaction is already processed
            if transaction['status'] != 'pending':
                flash(f"Cannot reject transaction that is already {transaction['status']}", "error")
                return redirect(url_for('admin_transaction_detail', reference=reference))
            
            # Update transaction status
            cursor.execute("""
                UPDATE transactions
                SET status = 'rejected', updated_at = ?, rejection_reason = ?
                WHERE reference = ?
            """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reason, reference))
            
            db.commit()
            
            # Get user information for notification
            user_id = transaction['user_id']
            user_name = f"{transaction['first_name']} {transaction['last_name']}" if transaction['first_name'] else "Unknown User"
            transaction_type = transaction['transaction_type']
            amount = transaction['amount']
            
            # Log the admin action with detailed information
            log_admin_activity(
                admin_id, 
                'transaction_reject', 
                f'Rejected {transaction_type} transaction {reference} for {amount} USD from {user_name} (ID: {user_id}). Reason: {reason}'
            )
            
            flash(f"Transaction {reference} has been rejected", "success")
            return redirect(url_for('admin_transaction_detail', reference=reference))
            
    except Exception as e:
        flash(f"Error rejecting transaction: {str(e)}", "error")
        return redirect(url_for('admin_transaction_detail', reference=reference))

@app.route("/admin/transaction/approve/<reference>", methods=["POST"])
@admin_required
def admin_approve_transaction(reference):
    """Approve a pending transaction"""
    admin_id = get_current_admin_id()
    
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # Get transaction details first for logging
            cursor.execute("""
                SELECT t.*, u.first_name, u.last_name, u.email 
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.id
                WHERE t.reference = ?
            """, (reference,))
            
            transaction = cursor.fetchone()
            if not transaction:
                flash("Transaction not found", "error")
                return redirect(url_for('admin_transactions'))
            
            # Check if transaction is already processed
            if transaction['status'] != 'pending':
                flash(f"Cannot approve transaction that is already {transaction['status']}", "error")
                return redirect(url_for('admin_transaction_detail', reference=reference))
            
            # Update transaction status
            cursor.execute("""
                UPDATE transactions
                SET status = 'completed', updated_at = ?
                WHERE reference = ?
            """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reference))
            
            db.commit()
            
            # Get user information for notification
            user_id = transaction['user_id']
            user_name = f"{transaction['first_name']} {transaction['last_name']}" if transaction['first_name'] else "Unknown User"
            transaction_type = transaction['transaction_type']
            amount = transaction['amount']
            
            # Log the admin action with detailed information
            log_admin_activity(
                admin_id, 
                'transaction_approve', 
                f'Approved {transaction_type} transaction {reference} for {amount} USD for {user_name} (ID: {user_id})'
            )
            
            flash(f"Transaction {reference} has been approved", "success")
            return redirect(url_for('admin_transaction_detail', reference=reference))
            
    except Exception as e:
        flash(f"Error approving transaction: {str(e)}", "error")
        return redirect(url_for('admin_transaction_detail', reference=reference))

@app.route("/admin/transaction/<reference>")
@admin_required
def admin_transaction_detail(reference):
    """
    Route to show transaction details
    """
    admin_id = get_current_admin_id()
    admin = get_admin_data(admin_id)

    with get_db() as db:
        cursor = db.cursor()

        # Get transaction details
        cursor.execute("""
            SELECT t.*, a.account_number, a.user_id, u.first_name, u.last_name, u.email
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            JOIN users u ON a.user_id = u.id
            WHERE t.reference = ?


        """, (reference,))

        transaction = cursor.fetchone()

        if not transaction:
            flash("Transaction not found", "error")
            return redirect(url_for('admin_transactions'))

        # Convert to dict for easier handling
        transaction = dict(transaction)

        return render_template('admin/transaction_detail.html',
            admin=admin,
                               transaction=transaction)
@app.route("/admin/transactions")
@admin_required
def admin_transactions():
    """Display all transactions for admin review"""
    try:
        admin_id = get_current_admin_id()
        log_admin_activity(admin_id, 'view_transactions', 'Viewed all transactions')
    except Exception as e:
        print(f"Error occurred: {e}")

    with get_db() as db:
        cursor = db.cursor()

        # Get query parameters for filtering
        status = request.args.get('status', 'all')
        search = request.args.get('search', '')

        # Get transaction metrics for the dashboard cards
        cursor.execute("SELECT COUNT(*) as count FROM transactions")
        total_transactions = cursor.fetchone()['count']
        
        cursor.execute("SELECT SUM(amount) as total FROM transactions")
        result = cursor.fetchone()
        total_volume = result['total'] if result and result['total'] is not None else 0
        
        cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE status = 'pending'")
        pending_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE status = 'failed'")
        failed_count = cursor.fetchone()['count']

        # Base query - simplified to avoid non-existent columns
        query = """
            SELECT t.* FROM transactions t WHERE 1=1
        """
        params = []

        # Add filters
        if status and status != 'all':
            query += " AND t.status = ?"
            params.append(status)

        if search:
            query += """ AND (
                t.reference LIKE ? 
                OR t.amount LIKE ?
                OR t.description LIKE ?
            )"""
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])

        # Order by most recent first
        query += " ORDER BY t.created_at DESC"

        cursor.execute(query, params)
        transactions = cursor.fetchall()

        # Format the transactions for display
        formatted_transactions = []
        for tx in transactions:
            # Get user information for this transaction
            user_id = tx['user_id']
            user_info = None
            account_number = None
            
            if user_id:
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                user_info = cursor.fetchone()
                
                # Get account number
                cursor.execute("SELECT account_number FROM accounts WHERE id = ?", (tx['account_id'],))
                account_result = cursor.fetchone()
                if account_result:
                    account_number = account_result['account_number']
            
            # Get sender and recipient if they exist
            # Use safer attribute access for sqlite3.Row objects
            sender_id = tx['sender_id'] if 'sender_id' in tx.keys() else None
            recipient_id = tx['recipient_id'] if 'recipient_id' in tx.keys() else None
            
            sender_name = "System"
            recipient_name = "System"
            
            if sender_id:
                cursor.execute("SELECT username FROM users WHERE id = ?", (sender_id,))
                sender = cursor.fetchone()
                if sender:
                    sender_name = sender['username']
                    
            if recipient_id:
                cursor.execute("SELECT username FROM users WHERE id = ?", (recipient_id,))
                recipient = cursor.fetchone()
                if recipient:
                    recipient_name = recipient['username']
            
            transaction_data = dict(tx)
            transaction_data['user'] = user_info
            transaction_data['account_number'] = account_number
            transaction_data['sender_username'] = sender_name
            transaction_data['recipient_username'] = recipient_name
            
            formatted_transactions.append(transaction_data)

    # Get admin data for the template
    admin = get_admin_data(admin_id)

    # Return the template with all necessary data
    return render_template(
        'admin/transactions.html',
        admin=admin,
        transactions=formatted_transactions,
        current_status=status,
        search=search,
        total_transactions=total_transactions,
        total_volume=total_volume,
        pending_count=pending_count,
        failed_count=failed_count
    )

@app.route('/admin/other-settings')
@admin_required
def admin_other_settings():
    # Get system health data
    health_data = get_system_health()

    # Get user metrics
    with get_db() as db:
        cursor = db.cursor()

        # Daily active users
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM activity_logs 
            WHERE timestamp >= datetime('now', '-1 day')


        """)
        daily_active_users = cursor.fetchone()[0]

        # Daily active users growth
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM activity_logs 
            WHERE timestamp >= datetime('now', '-2 days') 
            AND timestamp < datetime('now', '-1 day')


        """)
        prev_active_users = cursor.fetchone()[0]

        daily_growth = round(((daily_active_users - prev_active_users) / max(prev_active_users, 1)) * 100, 1)

        # Weekly average users
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM activity_logs 
            WHERE timestamp >= datetime('now', '-7 days')


        """)
        weekly_active_users = cursor.fetchone()[0]
        weekly_avg_users = round(weekly_active_users / 7)

        # Week before for comparison
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM activity_logs 
            WHERE timestamp >= datetime('now', '-14 days')
            AND timestamp < datetime('now', '-7 days')


        """)
        prev_weekly_active = cursor.fetchone()[0]
        prev_weekly_avg = round(prev_weekly_active / 7) if prev_weekly_active > 0 else 1

        weekly_avg_growth = round(((weekly_avg_users - prev_weekly_avg) / prev_weekly_avg) * 100, 1)

        # Retention rate
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        retention_rate = round((weekly_active_users / total_users) * 100, 1) if total_users > 0 else 0

        # Total platform balance (sum of all account balances)
        cursor.execute("""
            SELECT COALESCE(SUM(balance), 0) FROM accounts
            WHERE is_active = 1
        """)
        total_platform_balance = cursor.fetchone()[0]

    # Create user metrics dict
    user_metrics = {
        'daily_active_users': daily_active_users,
        'daily_growth': daily_growth,
        'weekly_avg_users': weekly_avg_users,
        'weekly_avg_growth': weekly_avg_growth,
        'retention_rate': retention_rate
    }

    # Get error logs
    error_logs = get_error_logs(limit=50)

    # Get security logs
    security_logs = get_security_logs(limit=50)

    return render_template(
        'admin/other_settings.html',
        health_data=health_data,
        user_metrics=user_metrics,
        error_logs=error_logs,
        security_logs=security_logs,
        total_platform_balance=total_platform_balance
    )

def get_error_logs(limit=50):
    """Get the most recent error logs"""
    try:
        with get_db() as db:
            cursor = db.cursor()

            cursor.execute("""
                SELECT 
                id, error_type, error_message, severity, 
                user_id, created_at as timestamp, level
                FROM error_logs
                ORDER BY created_at DESC
                LIMIT ?


            """, (limit,))

            logs = cursor.fetchall()
            return [dict(log) for log in logs] if logs else []
    except Exception as e:
        print(f"Error retrieving error logs: {e}")
        return []

def get_security_logs(limit=50):
    """Get the most recent security logs"""
    try:
        with get_db() as db:
            cursor = db.cursor()

            cursor.execute("""
                SELECT 
                id, event_type as action, description, threat_level,
                user_id, admin_id, ip_address, status,
                created_at as timestamp,
                (SELECT username FROM users WHERE id = s.user_id) as user
                FROM security_logs s
                ORDER BY created_at DESC
                LIMIT ?


            """, (limit,))

            logs = cursor.fetchall()
            return [dict(log) for log in logs] if logs else []
    except Exception as e:
        print(f"Error retrieving security logs: {e}")
        return []

# Add debug routes
try:
    from debug_routes import add_debug_routes
    add_debug_routes(app)
    print("Debug routes added successfully")
except Exception as e:
    print(f"Error adding debug routes: {e}")

@app.before_request
def set_test_user_for_development():
    """Set a test user for development purposes"""
    # Skip for static files
    if request.path.startswith('/static'):
        return

    # If no user is logged in, set a test user for development
    if 'user_id' not in session:
        print("Setting test user ID to 4 for development testing")
        session['user_id'] = 4
        session['email'] = 'testuser@example.com'
        session['first_name'] = 'Test'
        session['last_name'] = 'User'
        
        # Get actual user data if possible
        try:
            with get_db() as db:
                cursor = db.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (4,))
                user = cursor.fetchone()
                if user:
                    session['email'] = user['email']
                    session['first_name'] = user['first_name']
                    session['last_name'] = user['last_name']
        except Exception as e:
            print(f"Error fetching test user data: {e}")

@app.route("/api/transaction-data")
def api_transaction_data():
    """API endpoint to fetch real transaction data for the financial performance chart"""
    from datetime import datetime, timedelta
    import sqlite3
    
    # Get user ID from session or from query parameter
    user_id = request.args.get('user_id', None)
    
    # If no user_id in query, use the session's user_id
    if not user_id:
        user_id = session.get('user_id')
    
    print(f"[Direct Route] Fetching transaction data for user_id: {user_id}")
    
    # Get the time period from query param, default to 12 months
    period = request.args.get('period', '1Y')
    print(f"[Direct Route] Requested time period: {period}")
    
    # Calculate date range based on period
    now = datetime.now()
    if period == '1M':
        months = 1
        prev_months = 1  # Previous month for comparison
    elif period == '3M':
        months = 3
        prev_months = 3  # Previous 3 months for comparison
    elif period == '6M':
        months = 6
        prev_months = 6  # Previous 6 months for comparison
    elif period == '1Y':
        months = 12
        prev_months = 12  # Previous year for comparison
    else:  # 'ALL'
        months = 60  # Just use a large number for all data
        prev_months = 60  # Previous period for comparison
    
    start_date = (now - timedelta(days=30 * months)).strftime('%Y-%m-%d')
    # Calculate previous period for percentage change
    prev_start_date = (now - timedelta(days=30 * (months + prev_months))).strftime('%Y-%m-%d')
    prev_end_date = start_date
    
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # First get the account IDs for this user
            cursor.execute('''
                SELECT id FROM accounts WHERE user_id = ?
            ''', (user_id,))
            
            account_ids = [row['id'] for row in cursor.fetchall()]
            
            if not account_ids:
                print(f"[Direct Route] No accounts found for user_id: {user_id}")
                return jsonify({
                    'success': False,
                    'message': 'No accounts found for this user'
                }), 404
            
            print(f"[Direct Route] Found account ids: {account_ids}")
            
            # Then get transactions for these accounts grouped by month and type
            placeholders = ','.join(['?' for _ in account_ids])
            cursor.execute(f'''
                SELECT 
                    strftime('%Y-%m', created_at) as month,
                    transaction_type,
                    SUM(amount) as total_amount
                FROM transactions
                WHERE account_id IN ({placeholders})
                AND created_at >= ?
                AND status = 'completed'
                GROUP BY month, transaction_type
                ORDER BY month
            ''', account_ids + [start_date])
            
            transactions = cursor.fetchall()
            print(f"[Direct Route] Found {len(transactions)} transaction records")
            
            # Get transaction totals for current period
            cursor.execute(f'''
                SELECT 
                    transaction_type,
                    SUM(amount) as total_amount
                FROM transactions
                WHERE account_id IN ({placeholders})
                AND created_at >= ?
                AND status = 'completed'
                GROUP BY transaction_type
            ''', account_ids + [start_date])
            
            totals = cursor.fetchall()
            print(f"[Direct Route] Found totals: {totals}")
            
            # Get transaction totals for previous period to calculate percentage changes
            cursor.execute(f'''
                SELECT 
                    transaction_type,
                    SUM(amount) as total_amount
                FROM transactions
                WHERE account_id IN ({placeholders})
                AND created_at >= ? AND created_at < ?
                AND status = 'completed'
                GROUP BY transaction_type
            ''', account_ids + [prev_start_date, prev_end_date])
            
            prev_totals = cursor.fetchall()
            print(f"[Direct Route] Found previous period totals: {prev_totals}")
            
        # Process data for chart
        months_list = []
        deposits = {}
        withdrawals = {}
        
        # Initialize with zero values for each month in range
        current = datetime.strptime(start_date, '%Y-%m-%d')
        while current <= now:
            month_key = current.strftime('%Y-%m')
            month_display = current.strftime('%b %Y')
            months_list.append(month_display)
            deposits[month_key] = 0
            withdrawals[month_key] = 0
            current = (current.replace(day=1) + timedelta(days=32)).replace(day=1)
        
        # Fill in actual values
        for transaction in transactions:
            month = transaction['month']
            if transaction['transaction_type'].lower() == 'deposit':
                deposits[month] = transaction['total_amount']
            elif transaction['transaction_type'].lower() == 'withdrawal':
                withdrawals[month] = transaction['total_amount']
        
        # Create arrays for chart
        deposits_data = [deposits.get(datetime.strptime(month, '%b %Y').strftime('%Y-%m'), 0) for month in months_list]
        withdrawals_data = [withdrawals.get(datetime.strptime(month, '%b %Y').strftime('%Y-%m'), 0) for month in months_list]
        # Corrected profit calculation for trading accounts: withdrawals - deposits
        profits_data = [w - d for w, d in zip(withdrawals_data, deposits_data)]
        
        # Process totals for summary cards
        total_deposits = 0
        total_withdrawals = 0
        prev_total_deposits = 0
        prev_total_withdrawals = 0
        
        for total in totals:
            if total['transaction_type'].lower() == 'deposit':
                total_deposits = total['total_amount']
            elif total['transaction_type'].lower() == 'withdrawal':
                total_withdrawals = total['total_amount']
        
        for total in prev_totals:
            if total['transaction_type'].lower() == 'deposit':
                prev_total_deposits = total['total_amount']
            elif total['transaction_type'].lower() == 'withdrawal':
                prev_total_withdrawals = total['total_amount']
        
        # Calculate total profit - CORRECTED CALCULATION
        # For trading accounts, profit is calculated as: withdrawals - deposits
        total_profit = total_withdrawals - total_deposits
        prev_total_profit = prev_total_withdrawals - prev_total_deposits
        
        # Calculate percentage changes
        deposit_percentage = calculate_percentage_change(prev_total_deposits, total_deposits)
        withdrawal_percentage = calculate_percentage_change(prev_total_withdrawals, total_withdrawals)
        profit_percentage = calculate_percentage_change(prev_total_profit, total_profit)
        
        print(f"[Direct Route] Total deposits: {total_deposits}, withdrawals: {total_withdrawals}, profit: {total_profit}")
        print(f"[Direct Route] Percentage changes - deposits: {deposit_percentage}%, withdrawals: {withdrawal_percentage}%, profit: {profit_percentage}%")
        
        return jsonify({
            'success': True,
            'labels': months_list,
            'deposits': deposits_data,
            'withdrawals': withdrawals_data,
            'profits': profits_data,
            'summary': {
                'totalDeposits': total_deposits,
                'totalWithdrawals': total_withdrawals,
                'totalProfit': total_profit,
                'depositPercentage': deposit_percentage,
                'withdrawalPercentage': withdrawal_percentage,
                'profitPercentage': profit_percentage
            }
        })
        
    except sqlite3.Error as e:
        print(f"[Direct Route] Database error: {e}")
        return jsonify({
            'success': False,
            'message': f'Database error: {str(e)}'
        }), 500
    except Exception as e:
        print(f"[Direct Route] Unexpected error: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

def calculate_percentage_change(prev_value, current_value):
    """Calculate percentage change between two values"""
    if prev_value == 0:
        return 100 if current_value > 0 else 0
    return ((current_value - prev_value) / abs(prev_value)) * 100

@app.route("/api/debug/user-transactions/<int:user_id>")
def debug_user_transactions(user_id):
    """Debug endpoint to view transaction data for a specific user"""
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # First get the account IDs for this user
            cursor.execute('''
                SELECT id FROM accounts WHERE user_id = ?
            ''', (user_id,))
            
            account_ids = [row['id'] for row in cursor.fetchall()]
            
            if not account_ids:
                return jsonify({
                    'success': False,
                    'message': f'No accounts found for user_id: {user_id}'
                })
            
            # Get all transactions for these accounts
            placeholders = ','.join(['?' for _ in account_ids])
            cursor.execute(f'''
                SELECT 
                    t.*,
                    a.account_number
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.account_id IN ({placeholders})
                ORDER BY t.created_at DESC
                LIMIT 50
            ''', account_ids)
            
            transactions = cursor.fetchall()
            
            # Count of transactions by status
            cursor.execute(f'''
                SELECT 
                    status,
                    COUNT(*) as count
                FROM transactions
                WHERE account_id IN ({placeholders})
                GROUP BY status
            ''', account_ids)
            
            status_counts = cursor.fetchall()
            
            # Count by type
            cursor.execute(f'''
                SELECT 
                    transaction_type,
                    COUNT(*) as count,
                    SUM(amount) as total
                FROM transactions
                WHERE account_id IN ({placeholders})
                AND status = 'completed'
                GROUP BY transaction_type
            ''', account_ids)
            
            type_counts = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'user_id': user_id,
                'account_ids': account_ids,
                'transactions_count': len(transactions),
                'transactions': [dict(t) for t in transactions[:10]],  # First 10 for brevity
                'status_counts': [dict(s) for s in status_counts],
                'type_counts': [dict(t) for t in type_counts]
            })
            
    except Exception as e:
        print(f"Debug endpoint error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

def send_email(to_email, subject, body):
    """
    Send an email with the given subject and body to the specified recipient.
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        body (str): Email body content (HTML format)
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # For development/testing, just log the email instead of sending
        # In production, replace with actual email sending logic
        logger.info(f"MOCK EMAIL: To: {to_email}, Subject: {subject}")
        logger.info(f"MOCK EMAIL BODY: {body}")
        
        # Uncomment and configure for actual email sending:
        # from_email = "your-system-email@example.com"
        # message = MIMEMultipart()
        # message["From"] = from_email
        # message["To"] = to_email
        # message["Subject"] = subject
        # message.attach(MIMEText(body, "html"))
        # 
        # with smtplib.SMTP_SSL("smtp.example.com", 465) as server:
        #     server.login("username", "password")
        #     server.send_message(message)
        
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def send_email_to_user(email, subject, message):
    """
    Send an email to a user.
    
    Args:
        email (str): The recipient's email address
        subject (str): The email subject
        message (str): The email message content
        
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    try:
        # In a production environment, this would use SMTP or an email service
        # For this example, we'll just log that the email would be sent
        print(f"Email would be sent to {email}")
        print(f"Subject: {subject}")
        print(f"Message: {message}")
        
        # Get SMTP settings from system_settings table
        with get_db() as db:
            cursor = db.cursor()
            
            cursor.execute("SELECT key, value FROM system_settings WHERE key IN ('smtp_server', 'smtp_port', 'smtp_username', 'smtp_password', 'email_from_address', 'email_from_name')")
            settings = {row['key']: row['value'] for row in cursor.fetchall()}
            
            # Log the email for audit purposes
            cursor.execute(
                "INSERT INTO email_logs (recipient, subject, created_at) VALUES (?, ?, ?)",
                (email, subject, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            db.commit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def get_admin_by_id(admin_id):
    """
    Get admin data by ID.
    
    Args:
        admin_id (int): The admin ID
        
    Returns:
        dict: Admin data or None if not found
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("SELECT * FROM admins WHERE id = ?", (admin_id,))
        admin = cursor.fetchone()
        
        if admin:
            admin_dict = dict(admin)
            # Remove sensitive information
            if 'password' in admin_dict:
                del admin_dict['password']
            return admin_dict
        return None
    except Exception as e:
        print(f"Error getting admin by ID: {str(e)}")
        return None

@app.route('/admin/debug/session')
def admin_debug_session():
    """Debug route to show session data (admin use only)"""
    session_data = dict(session)
    admin_id = session.get('admin_id')
    
    output = []
    output.append("<h1>Session Debug</h1>")
    output.append(f"<p>Admin ID in session: {admin_id}</p>")
    
    if admin_id:
        admin = get_admin_data(admin_id)
        output.append(f"<p>Admin data from database: {admin}</p>")
    
    output.append("<h2>All Session Data:</h2>")
    output.append("<pre>")
    for key, value in session_data.items():
        output.append(f"{key}: {value}")
    output.append("</pre>")
    
    return "".join(output)

@app.route("/admin/user/<int:user_id>/generate-statement")
@admin_required
def admin_generate_user_statement(user_id):
    """Generate a transaction statement for a specific user"""
    
    admin_id = get_current_admin_id()
    log_admin_activity(admin_id, f"generated statement for user {user_id}")
    
    # Get user data
    with get_db() as db:
        cursor = db.cursor()
        
        # Get user information
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash("User not found", "error")
            return redirect(url_for('admin_users'))
        
        # Get all user accounts
        cursor.execute("SELECT * FROM accounts WHERE user_id = ?", (user_id,))
        accounts = cursor.fetchall()
        
        account_ids = [account['id'] for account in accounts]
        
        if not account_ids:
            flash("No accounts found for this user", "error")
            return redirect(url_for('admin_user_detail', user_id=user_id))
        
        # Get transactions for all user accounts, sorted by date descending
        account_ids_str = ','.join(['?' for _ in account_ids])
        cursor.execute(f"""
            SELECT t.*, a.account_number, a.account_name, a.account_type 
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE t.account_id IN ({account_ids_str})
            ORDER BY t.created_at DESC
        """, account_ids)
        
        transactions = cursor.fetchall()
        
        # Get system settings
        cursor.execute("SELECT key, value FROM system_settings WHERE key IN ('site_name', 'contact_email', 'currency_symbol')")
        settings = {row['key']: row['value'] for row in cursor.fetchall()}
    
    # Prepare statement data
    statement_data = {
        'user': dict(user),
        'accounts': [dict(account) for account in accounts],
        'transactions': [dict(transaction) for transaction in transactions],
        'settings': settings,
        'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'period_start': (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        'period_end': datetime.now().strftime("%Y-%m-%d")
    }
    
    return render_template('admin/user_statement.html', **statement_data)

@app.route('/admin/system-metrics')
@admin_required
def admin_system_metrics():
    """Display comprehensive system metrics and financial analysis"""
    # Log admin activity
    admin_id = get_current_admin_id()
    log_admin_activity(admin_id, "viewed system metrics")

    # Get admin data
    admin_data = get_admin_data(admin_id)

    with get_db() as db:
        cursor = db.cursor()

        # Total deposits (all time)
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions 
            WHERE transaction_type = 'deposit' AND status = 'completed'
        """)
        total_deposits = cursor.fetchone()[0]

        # Total withdrawals (all time)
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions 
            WHERE transaction_type = 'withdrawal' AND status = 'completed'
        """)
        total_withdrawals = cursor.fetchone()[0]

        # Net profit (simplified calculation)
        # In a real system, this would include fees, commissions, etc.
        cursor.execute("""
            SELECT COALESCE(SUM(amount * 0.01), 0) FROM transactions 
            WHERE status = 'completed'
        """)
        total_fees = cursor.fetchone()[0]
        net_profit = total_fees

        # Transaction volume (last 7 days)
        cursor.execute("""
            SELECT COUNT(*) FROM transactions 
            WHERE created_at >= datetime('now', '-7 days')
        """)
        weekly_transaction_volume = cursor.fetchone()[0]

        # Transaction volume (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) FROM transactions 
            WHERE created_at >= datetime('now', '-1 day')
        """)
        daily_transaction_volume = cursor.fetchone()[0]

        # Active users (users with transactions in last 30 days)
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM transactions 
            WHERE created_at >= datetime('now', '-30 days')
        """)
        active_transacting_users = cursor.fetchone()[0]

        # Scam/Fraud alerts (transactions marked as suspicious)
        cursor.execute("""
            SELECT COUNT(*) FROM transactions 
            WHERE status = 'flagged'
        """)
        fraud_alerts = cursor.fetchone()[0]

        # Most used payment methods
        cursor.execute("""
            SELECT payment_method, COUNT(*) as count 
            FROM transactions 
            WHERE payment_method IS NOT NULL AND payment_method != ''
            GROUP BY payment_method 
            ORDER BY count DESC
            LIMIT 5
        """)
        payment_methods = cursor.fetchall()

        # Growth rate (new users in last 30 days vs. total)
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE created_at >= datetime('now', '-30 days')
        """)
        new_users = cursor.fetchone()[0]
        
        growth_rate = round((new_users / max(1, total_users)) * 100, 1)

        # Support requests (from notifications or a dedicated support_tickets table if available)
        cursor.execute("""
            SELECT COUNT(*) FROM notifications 
            WHERE title LIKE '%support%' OR message LIKE '%support%'
        """)
        support_requests = cursor.fetchone()[0]

        # Total platform balance (sum of all account balances)
        cursor.execute("""
            SELECT COALESCE(SUM(balance), 0) FROM accounts
            WHERE is_active = 1
        """)
        total_platform_balance = cursor.fetchone()[0]

        # Monthly transaction data for charts (last 6 months)
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as transaction_count,
                COALESCE(SUM(CASE WHEN transaction_type = 'deposit' THEN amount ELSE 0 END), 0) as deposit_amount,
                COALESCE(SUM(CASE WHEN transaction_type = 'withdrawal' THEN amount ELSE 0 END), 0) as withdrawal_amount
            FROM transactions
            WHERE created_at >= datetime('now', '-6 months')
            GROUP BY month
            ORDER BY month
        """)
        monthly_data = cursor.fetchall()

    # Prepare chart data
    months = []
    deposit_data = []
    withdrawal_data = []
    transaction_counts = []

    for row in monthly_data:
        months.append(row['month'])
        deposit_data.append(float(row['deposit_amount']))
        withdrawal_data.append(float(row['withdrawal_amount']))
        transaction_counts.append(row['transaction_count'])

    metrics_data = {
        'admin': admin_data,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'net_profit': net_profit,
        'active_transacting_users': active_transacting_users,
        'weekly_transaction_volume': weekly_transaction_volume,
        'daily_transaction_volume': daily_transaction_volume,
        'fraud_alerts': fraud_alerts,
        'payment_methods': payment_methods,
        'growth_rate': growth_rate,
        'support_requests': support_requests,
        'total_platform_balance': total_platform_balance,
        'months': months,
        'deposit_data': deposit_data,
        'withdrawal_data': withdrawal_data,
        'transaction_counts': transaction_counts
    }

    return render_template('admin/system_metrics.html', **metrics_data)

def get_error_logs(limit=50):
    """Get the most recent error logs"""
    try:
        with get_db() as db:
            cursor = db.cursor()

            cursor.execute("""
                SELECT 
                id, error_type, error_message, severity, 
                user_id, created_at as timestamp, level
                FROM error_logs
                ORDER BY created_at DESC
                LIMIT ?


            """, (limit,))

            logs = cursor.fetchall()
            return [dict(log) for log in logs] if logs else []
    except Exception as e:
        print(f"Error retrieving error logs: {e}")
        return []

def get_security_logs(limit=50):
    """Get the most recent security logs"""
    try:
        with get_db() as db:
            cursor = db.cursor()

            cursor.execute("""
                SELECT 
                id, event_type as action, description, threat_level,
                user_id, admin_id, ip_address, status,
                created_at as timestamp,
                (SELECT username FROM users WHERE id = s.user_id) as user
                FROM security_logs s
                ORDER BY created_at DESC
                LIMIT ?


            """, (limit,))

            logs = cursor.fetchall()
            return [dict(log) for log in logs] if logs else []
    except Exception as e:
        print(f"Error retrieving security logs: {e}")
        return []

@app.route("/transaction/<reference>")
@login_required
def transaction_detail(reference):
    """
    Route to show transaction details for a user
    """
    user_id = session.get('user_id')

    try:
        with get_db() as db:
            cursor = db.cursor()

            # Get transaction details
            cursor.execute("""
                SELECT t.*, a.account_number, a.account_name
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                WHERE t.reference = ? AND a.user_id = ?
            """, (reference, user_id))

            transaction = cursor.fetchone()

            if not transaction:
                flash("Transaction not found", "error")
                return redirect(url_for('transactions'))

            # Convert to dict for easier handling
            transaction = dict(transaction)

            # Process date fields
            transaction = process_date_fields(transaction)
            
            # Get user data
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                flash("User not found", "error")
                return redirect(url_for('login'))
                
            # Convert to dict for template
            user = dict(user)
            
            # Check for forex metadata
            forex_data = None
            if transaction.get('metadata'):
                try:
                    import json
                    metadata = json.loads(transaction['metadata']) if isinstance(transaction['metadata'], str) else transaction['metadata']
                    
                    if isinstance(metadata, dict) and 'forex_rate' in metadata:
                        forex_data = metadata
                        
                        # Ensure we have the correct keys for template display
                        if 'converted_amount_kes' not in forex_data and 'kes_amount' in forex_data:
                            forex_data['converted_amount_kes'] = forex_data['kes_amount']
                            
                        # Calculate net USD amount if not present
                        if 'net_usd' not in forex_data and 'fee_usd' in forex_data and transaction.get('amount'):
                            amount = float(transaction['amount'])
                            fee = float(forex_data.get('fee_usd', 0))
                            forex_data['net_usd'] = amount - fee
                            
                except Exception as e:
                    print(f"Error parsing transaction metadata: {str(e)}")
                    print(f"Raw metadata: {transaction.get('metadata')}")

            # Log user activity
            log_user_activity(user_id, 'view_transaction_detail', f'Viewed transaction detail for reference: {reference}')

            return render_template('transaction_detail.html',
                                transaction=transaction,
                                user=user,
                                forex_data=forex_data)
    except Exception as e:
        # Log the error for administrators but don't show technical details to users
        print(f"Transaction detail error: {str(e)}")
        traceback.print_exc()
        
        # Only redirect to login for authentication issues
        if "user_id" not in session:
            return redirect(url_for('login'))
            
        # Generic error message for users
        flash("Unable to display transaction details. Please try again later.", "error")
        return redirect(url_for('transactions'))

@app.route("/admin/forex", methods=["GET"])
@admin_required
def admin_forex():
    """Admin page to view and manage forex rates"""
    admin_id = get_current_admin_id()
    
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # Get forex rate history
            cursor.execute("""
                SELECT currency, rate, updated_at
                FROM forex_rates
                ORDER BY updated_at DESC
                LIMIT 50
            """)
            rate_history = cursor.fetchall()
            
            # Get current rate
            forex_rate, updated_at = get_latest_forex_rate()
            
            # Get some sample calculations for display
            sample_deposit = calculate_deposit_amount(1000)
            sample_withdrawal = calculate_withdrawal_amount(1000)
            
            # Log admin activity
            log_admin_activity(admin_id, 'view_forex_rates', 'Viewed forex rates management page')
            
            return render_template(
                'admin/forex.html',
                admin=get_admin_data(admin_id),
                rate_history=rate_history,
                current_rate=forex_rate,
                updated_at=updated_at,
                sample_deposit=sample_deposit,
                sample_withdrawal=sample_withdrawal
            )
    except Exception as e:
        flash(f"Error loading forex data: {str(e)}", "error")
        return redirect(url_for('admin_dashboard'))

@app.route("/admin/forex/update", methods=["POST"])
@admin_required
def admin_update_forex():
    """Admin action to manually update forex rates"""
    admin_id = get_current_admin_id()
    
    try:
        # Check if manual rate was provided
        manual_rate = request.form.get('manual_rate')
        
        if manual_rate:
            try:
                # Convert to float and validate
                rate = float(manual_rate)
                if rate <= 0:
                    flash("Rate must be greater than zero", "error")
                    return redirect(url_for('admin_forex'))
                    
                # Store manual rate
                store_forex_rate(rate)
                flash(f"Forex rate manually updated to {rate}", "success")
                
                # Log admin activity
                log_admin_activity(admin_id, 'update_forex_rate', f'Manually updated USD/KES rate to {rate}')
            except ValueError:
                flash("Invalid rate format. Please enter a valid number.", "error")
                return redirect(url_for('admin_forex'))
        else:
            # Fetch from API
            rate = fetch_forex_rate()
            
            if rate:
                flash(f"Forex rate updated successfully to {rate}", "success")
                log_admin_activity(admin_id, 'update_forex_rate', f'Updated USD/KES rate to {rate} via API')
            else:
                flash("Failed to update forex rate from API", "error")
                
        return redirect(url_for('admin_forex'))
    except Exception as e:
        flash(f"Error updating forex rate: {str(e)}", "error")
        return redirect(url_for('admin_forex'))

@app.route('/api/forex/latest', methods=['GET'])
def get_latest_forex_rate_api():
    """API endpoint to get the latest forex rate for client-side display"""
    try:
        # Get the latest forex rate (base rate)
        base_rate, updated_at = get_latest_forex_rate()
        
        # Get deposit and withdrawal rates with spreads
        deposit_rate, _ = get_deposit_rate()
        withdrawal_rate, _ = get_withdrawal_rate()
        
        if base_rate is not None:
            # Round all rates to exactly 2 decimal places for consistent display
            return jsonify({
                'success': True,
                'base_rate': round(base_rate, 2),
                'deposit_rate': round(deposit_rate, 2),
                'withdrawal_rate': round(withdrawal_rate, 2),
                'updated_at': updated_at.isoformat() if isinstance(updated_at, datetime) else updated_at
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No forex rate available'
            }), 404
    except Exception as e:
        logger.error(f"Error retrieving latest forex rate API: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error retrieving forex rate'
        }), 500

if __name__ == '__main__':
    # Initialize database
    init_db()

    # Run initial health check and start scheduler
    record_system_health()

    # Set up a scheduler to run health checks every 15 minutes
    def run_scheduled_health_checks():
        import time
        while True:
            time.sleep(900)  # 15 minutes = 900 seconds
            print("Running scheduled health check...")
            record_system_health()

    # Start the health check scheduler in a background thread
    health_scheduler = threading.Thread(target=run_scheduled_health_checks)
    health_scheduler.daemon = True
    health_scheduler.start()
    
    # Initialize the forex rate scheduler (using APScheduler)
    print("Initializing forex rate scheduler...")
    forex_scheduler = scheduler.init_scheduler()
    
    # Register shutdown function
    import atexit
    atexit.register(scheduler.shutdown_scheduler)

    # Run the app
    app.run(host="0.0.0.0", port=80, debug=True)