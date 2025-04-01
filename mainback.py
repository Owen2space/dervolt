from flask import Flask, session, redirect, url_for, request, render_template, flash, jsonify, make_response
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import sqlite3
import json
import time
import traceback
import logging
import uuid
from routes import register_blueprints

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_development_only')

# Configure app
app.config['DATABASE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SECURE'] = True  # Require HTTPS
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)  # Session expires after 1 hour

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Database helper functions
def get_db():
    """Get database connection with row factory set to sqlite3.Row"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with schema"""
    with app.app_context():
        with get_db() as db:
            cursor = db.cursor()
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql'), 'r') as f:
                cursor.executescript(f.read())
            db.commit()

def get_system_setting(key, default=None):
    """Get a system setting from the database"""
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            if result:
                return result['value']
            return default
    except Exception as e:
        logger.error(f"Error getting system setting {key}: {e}")
        return default

# Add CORS headers
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

# Add cache prevention headers for authenticated pages
@app.after_request
def add_header(response):
    if 'user_id' in session or 'admin_id' in session:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Check for maintenance mode
@app.before_request
def check_maintenance_mode():
    # Skip for static files
    if request.path.startswith('/static'):
        return
    
    maintenance_mode = get_system_setting('maintenance_mode', 'off')
    if maintenance_mode == 'on' and request.path != '/maintenance' and not request.path.startswith('/admin'):
        message = get_system_setting('maintenance_message', 'The site is currently undergoing scheduled maintenance. Please check back later.')
        return render_template('maintenance.html', message=message)

# Check for session timeout
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
                return redirect(url_for('auth.login'))

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
                return redirect(url_for('admin.login'))

        # Update admin last activity timestamp
        session['admin_last_activity'] = time.time()

# Initialize database if needed
@app.before_request
def initialize_database_if_needed():
    if not os.path.exists(app.config['DATABASE']):
        try:
            init_db()
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return "Database error. Please contact support.", 500

# Register all routes
register_blueprints(app)

# Handle 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="Page not found"), 404

# Handle 500 errors
@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error="Internal server error"), 500

# Handle maintenance route
@app.route("/maintenance")
def maintenance():
    message = get_system_setting('maintenance_message', 'The site is currently undergoing scheduled maintenance. Please check back later.')
    return render_template('maintenance.html', message=message)
# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    return True

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    return True

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)