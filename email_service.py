import smtplib
import random
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from database import get_db
import traceback

# SMTP server details (Zoho Mail)
SMTP_SERVER = "smtp.zoho.com"
SMTP_PORT = 465  # Use SSL port for secure sending
EMAIL_ADDRESS = "no-reply@dervolt.site"  # Your Zoho email
EMAIL_PASSWORD = "4YDFVx2CZBLF"  # Use Zoho app password

def generate_otp(length=6):
    """Generate a lowercase alphanumeric OTP."""
    characters = string.ascii_lowercase + string.digits  # a-z, 0-9
    return ''.join(random.choice(characters) for _ in range(length))

def save_otp_to_db(email, otp, purpose="password_reset"):
    """Save OTP to database with expiration time (30 minutes)
    
    Args:
        email: User's email address
        otp: Generated OTP code
        purpose: Either "password_reset" or "password_change"
    """
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            print(f"Saving OTP: email={email}, otp={otp}, purpose={purpose}")
            
            # Calculate expiration time (30 minutes from now) - using ISO format for SQLite compatibility
            expires_at = (datetime.now() + timedelta(minutes=30)).isoformat()
            print(f"OTP will expire at: {expires_at}")
            
            if purpose == "password_reset":
                # Handle password reset OTP (forgot password)
                cursor.execute(
                    "UPDATE password_reset_otps SET is_used = 1 WHERE email = ?", 
                    (email,)
                )
                
                # Insert new OTP
                cursor.execute(
                    "INSERT INTO password_reset_otps (email, otp_code, expires_at) VALUES (?, ?, ?)",
                    (email, otp, expires_at)
                )
                print(f"Saved password reset OTP for email: {email}")
            
            elif purpose == "password_change":
                # Handle password change OTP (settings page)
                # First get the user_id from email
                cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                user = cursor.fetchone()
                
                if not user:
                    print(f"User not found with email: {email}")
                    return False
                
                # Invalidate existing OTPs
                cursor.execute(
                    "UPDATE password_change_otps SET is_used = 1 WHERE user_id = ? AND is_used = 0", 
                    (user['id'],)
                )
                
                # Insert new OTP
                cursor.execute(
                    "INSERT INTO password_change_otps (user_id, otp_code, expires_at) VALUES (?, ?, ?)",
                    (user['id'], otp, expires_at)
                )
                print(f"Saved password change OTP for user_id: {user['id']}")
            
            # Get the ID of the inserted OTP record
            cursor.execute("SELECT last_insert_rowid()")
            otp_id = cursor.fetchone()[0]
            print(f"Created OTP record with ID: {otp_id}")
            
            return True
    except Exception as e:
        print(f"Error saving OTP: {e}")
        traceback.print_exc()
        return False

def verify_otp(email, otp, purpose="password_reset", mark_as_used=True):
    """Verify if OTP is valid and not expired
    
    Args:
        email: User's email address
        otp: OTP code to verify
        purpose: Either "password_reset" or "password_change"
        mark_as_used: Whether to mark the OTP as used if valid
    """
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            # Debug logging to help find issues
            print(f"Verifying OTP: email={email}, otp={otp}, purpose={purpose}")
            
            if purpose == "password_reset":
                # Verify password reset OTP
                cursor.execute(
                    """
                    SELECT * FROM password_reset_otps
                    WHERE email = ? AND otp_code = ? AND is_used = 0
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (email, otp)
                )
                result = cursor.fetchone()
                
                if result and mark_as_used:
                    cursor.execute(
                        "UPDATE password_reset_otps SET is_used = 1 WHERE id = ?", 
                        (result['id'],)
                    )
                    db.commit()
            
            elif purpose == "password_change":
                # Verify password change OTP
                # First get the user_id from email
                cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                user = cursor.fetchone()
                
                if not user:
                    print(f"User not found with email: {email}")
                    return False
                
                # Debugging: Check all unused OTPs for this user
                cursor.execute(
                    """
                    SELECT * FROM password_change_otps
                    WHERE user_id = ? AND is_used = 0
                    ORDER BY created_at DESC
                    """,
                    (user['id'],)
                )
                all_otps = cursor.fetchall()
                if all_otps:
                    for otp_rec in all_otps:
                        print(f"Found OTP record: id={otp_rec['id']}, code={otp_rec['otp_code']}")
                else:
                    print(f"No unused OTPs found for user_id: {user['id']}")
                    
                # Try simplified query without timestamp comparison
                cursor.execute(
                    """
                    SELECT * FROM password_change_otps
                    WHERE user_id = ? AND otp_code = ? AND is_used = 0
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (user['id'], otp)
                )
                result = cursor.fetchone()
                
                if result:
                    print(f"Found matching OTP with id: {result['id']}")
                    
                    # Mark as used
                    if mark_as_used:
                        try:
                            cursor.execute(
                                "UPDATE password_change_otps SET is_used = 1 WHERE id = ?", 
                                (result['id'],)
                            )
                            db.commit()
                            print(f"Marked OTP as used: id={result['id']}")
                        except Exception as e:
                            print(f"Error marking OTP as used: {e}")
                            # Continue even if marking as used fails
                    
                    return True
                else:
                    print(f"No matching OTP found for user_id={user['id']} and otp={otp}")
            
            return result is not None
    except Exception as e:
        print(f"Error in verify_otp: {e}")
        traceback.print_exc()
        # Return False on any error to be safe
        return False

def send_otp_email(user_email, otp, purpose="Reset Your Password"):
    """Send OTP to the user's email
    
    Args:
        user_email: Recipient's email address
        otp: The OTP code to send
        purpose: Purpose text for the email subject (e.g., "Reset Your Password", "Change Your Password")
    """
    try:
        # Create the email message
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = user_email
        msg["Subject"] = f"🔒 {purpose} - Der-Volt"
        
        # HTML Email Template
        html_content = f"""
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
                .otp {{
                    font-size: 22px;
                    font-weight: bold;
                    color: #27AE60;
                    background: #ecf0f1;
                    padding: 10px;
                    display: inline-block;
                    border-radius: 5px;
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
                <h2>🔐 {purpose}</h2>
                <p>Hello,</p>
                <p>We received a request to {purpose.lower()} for your Der-Volt account.</p>
                <p>Your OTP code is:</p>
                <p class="otp">{otp}</p>
                <p>Please enter this code on the website to verify your identity.</p>
                <p>If you didn't request this, please ignore this email or secure your account immediately.</p>
                <p>Thank you,<br><b>Der-Volt Team</b></p>
                <p class="footer">This is an automated email. Please do not reply.</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_content, "html"))
        
        # Connect to SMTP server and send email
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)  # Use SSL connection
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, user_email, msg.as_string())
        server.quit()

        print(f"✅ OTP Email sent successfully to {user_email}!")
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {user_email}: {e}")
        return False

def process_password_reset_request(email):
    """Process a password reset request - generate OTP, save to DB, and send email"""
    # Check if user exists
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            return False, "Email not found"
    
    # Generate OTP
    otp = generate_otp()
    
    # Save OTP to database
    save_otp_to_db(email, otp, purpose="password_reset")
    
    # Send OTP email
    email_sent = send_otp_email(email, otp, purpose="Reset Your Password")
    
    if email_sent:
        return True, "OTP sent successfully"
    else:
        return False, "Failed to send OTP email"

def process_password_change_request(email):
    """Process a password change request - generate OTP, save to DB, and send email
    
    Similar to password reset but for the settings page
    """
    # Generate OTP
    otp = generate_otp()
    
    # Save OTP to database
    save_success = save_otp_to_db(email, otp, purpose="password_change")
    
    if not save_success:
        return False, "Failed to save OTP"
    
    # Send OTP email
    email_sent = send_otp_email(email, otp, purpose="Change Your Password")
    
    if email_sent:
        return True, "OTP sent successfully"
    else:
        return False, "Failed to send OTP email" 