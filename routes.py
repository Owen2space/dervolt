"""
Routes for the Der-volt application.
This file contains all route definitions to ensure consistency across the application.
"""

from flask import Blueprint, redirect, url_for, render_template, session, flash, request, jsonify, send_from_directory, make_response
from functools import wraps
from datetime import datetime
import json
import time

# Create blueprints for organizing routes
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
auth_bp = Blueprint('auth', __name__)
user_bp = Blueprint('user', __name__)
pwa_bp = Blueprint('pwa', __name__)  # New blueprint for PWA routes

# Helper functions
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            session.clear()
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            session.clear()
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def log_admin_activity(admin_id, action):
    """Log admin activity for audit purposes"""
    # Implementation would go here
    pass

def get_current_admin_id():
    """Get current admin ID from session"""
    return session.get('admin_id')

# Admin routes
@admin_bp.route('/login', methods=['GET'])
def login():
    """Admin login page"""
    return render_template('admin/login.html')

@admin_bp.route('/login', methods=['POST'])
def login_post():
    """Process admin login"""
    # Implementation would go here
    # On success:
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/logout')
def logout():
    """Admin logout"""
    session.pop('admin_id', None)
    session.pop('admin_role', None)
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('admin.login'))

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard"""
    admin_id = get_current_admin_id()
    log_admin_activity(admin_id, "Viewed admin dashboard")
    # Implementation would go here
    return render_template('admin/dashboard.html')

@admin_bp.route('/users')
@admin_required
def users():
    """Admin users list page"""
    admin_id = get_current_admin_id()
    log_admin_activity(admin_id, "Viewed user list")
    # Implementation would go here
    return render_template('admin/users.html')

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def user_edit(user_id):
    """Edit user details"""
    admin_id = get_current_admin_id()
    log_admin_activity(admin_id, f"Edited user with ID {user_id}")
    # Implementation would go here
    return render_template('admin/user_edit.html')

@admin_bp.route('/users/<int:user_id>/transactions')
@admin_required
def user_transactions(user_id):
    """View transactions for a specific user"""
    admin_id = get_current_admin_id()
    log_admin_activity(admin_id, f"Viewed transactions for user with ID {user_id}")
    # Implementation would go here
    return render_template('admin/user_transactions.html')

@admin_bp.route('/transactions')
@admin_required
def transactions():
    """Admin transactions list page"""
    admin_id = get_current_admin_id()
    log_admin_activity(admin_id, "Viewed transactions list")
    # Implementation would go here
    return render_template('admin/transactions.html')

@admin_bp.route('/transactions/<reference>')
@admin_required
def transaction_detail(reference):
    """View transaction details by reference"""
    admin_id = get_current_admin_id()
    log_admin_activity(admin_id, f"Viewed transaction details for reference {reference}")
    # Implementation would go here
    return render_template('admin/transaction_detail.html')

@admin_bp.route('/settings')
@admin_required
def settings():
    """Admin settings page"""
    admin_id = get_current_admin_id()
    log_admin_activity(admin_id, "Viewed settings")
    # Implementation would go here
    return render_template('admin/settings.html')

# Auth routes
@auth_bp.route('/login')
def login():
    """User login page"""
    success_message = request.args.get('success_message')
    return render_template('login.html', success_message=success_message)

@auth_bp.route('/signup')
def signup():
    """User signup page"""
    return render_template('signup.html')

@auth_bp.route('/logout')
def logout():
    """User logout"""
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot')
def forgot():
    """Forgot password page"""
    return render_template('forgot.html')

# User routes
@user_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    # Implementation would go here
    return render_template('dashboard.html')

@user_bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    # Implementation would go here
    return render_template('settings.html')

@user_bp.route('/transactions')
@login_required
def transactions():
    """User transactions page"""
    # Implementation would go here
    return render_template('transactions.html', user=session)

@user_bp.route('/help')
@login_required
def help():
    """Help and support page"""
    # Implementation would go here
    return render_template('help.html')

@user_bp.route('/notifications')
@login_required
def notifications():
    """User notifications page"""
    # Implementation would go here
    return render_template('notifications.html')

@user_bp.route('/api/transaction-data')
@login_required
def transaction_data():
    """API endpoint to fetch real transaction data for the financial performance chart"""
    from database import get_db_connection
    import sqlite3
    from datetime import datetime, timedelta
    
    # Get user ID from session
    user_id = session.get('user_id')
    print(f"Fetching transaction data for user_id: {user_id}")
    
    # Get the time period from query param, default to 12 months
    period = request.args.get('period', '1Y')
    print(f"Requested time period: {period}")
    
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
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First get the account IDs for this user
        cursor.execute('''
            SELECT id FROM accounts WHERE user_id = ?
        ''', (user_id,))
        
        account_ids = [row['id'] for row in cursor.fetchall()]
        
        if not account_ids:
            print(f"No accounts found for user_id: {user_id}")
            return jsonify({
                'success': False,
                'message': 'No accounts found for this user'
            }), 404
        
        print(f"Found account ids: {account_ids}")
        
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
            GROUP BY month, transaction_type
            ORDER BY month
        ''', account_ids + [start_date])
        
        transactions = cursor.fetchall()
        print(f"Found {len(transactions)} transaction records")
        
        # Get transaction totals for current period
        cursor.execute(f'''
            SELECT 
                transaction_type,
                SUM(amount) as total_amount
            FROM transactions
            WHERE account_id IN ({placeholders})
            AND created_at >= ?
            GROUP BY transaction_type
        ''', account_ids + [start_date])
        
        totals = cursor.fetchall()
        print(f"Found totals: {totals}")
        
        # Get transaction totals for previous period to calculate percentage changes
        cursor.execute(f'''
            SELECT 
                transaction_type,
                SUM(amount) as total_amount
            FROM transactions
            WHERE account_id IN ({placeholders})
            AND created_at >= ? AND created_at < ?
            GROUP BY transaction_type
        ''', account_ids + [prev_start_date, prev_end_date])
        
        prev_totals = cursor.fetchall()
        print(f"Found previous period totals: {prev_totals}")
        
        conn.close()
        
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
        profits_data = [d - w for d, w in zip(deposits_data, withdrawals_data)]
        
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
        
        # Calculate profit values
        total_profit = total_deposits - total_withdrawals
        prev_total_profit = prev_total_deposits - prev_total_withdrawals
        
        # Calculate percentage changes
        def calculate_percentage_change(prev_value, current_value):
            """Calculate percentage change between two values"""
            if prev_value == 0:
                return 100 if current_value > 0 else 0
            return ((current_value - prev_value) / abs(prev_value)) * 100
            
        deposit_percentage = calculate_percentage_change(prev_total_deposits, total_deposits)
        withdrawal_percentage = calculate_percentage_change(prev_total_withdrawals, total_withdrawals)
        profit_percentage = calculate_percentage_change(prev_total_profit, total_profit)
        
        print(f"Total deposits: {total_deposits}, withdrawals: {total_withdrawals}, profit: {total_profit}")
        print(f"Percentage changes - deposits: {deposit_percentage}%, withdrawals: {withdrawal_percentage}%, profit: {profit_percentage}%")
        
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
        print(f"Database error: {e}")
        return jsonify({
            'success': False,
            'message': f'Database error: {str(e)}'
        }), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# Main routes
def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(pwa_bp)  # Register the new PWA blueprint
    
    @app.route('/')
    def index():
        """Landing page"""
        return render_template('index.html')

# PWA routes
@pwa_bp.route('/service-worker.js')
def service_worker():
    """Serve the service worker file from the correct path"""
    response = make_response(send_from_directory('static', 'service-worker.js'))
    # Set the correct MIME type for JavaScript
    response.headers['Content-Type'] = 'application/javascript'
    # Disable caching for service worker
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@pwa_bp.route('/manifest.json')
def manifest():
    """Serve the manifest file for PWA"""
    return send_from_directory('static', 'manifest.json')

@pwa_bp.route('/offline')
def offline():
    """Serve the offline page when the user is not connected to the internet"""
    return send_from_directory('static', 'offline.html') 