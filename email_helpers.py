def send_password_reset_email(user_email, user_name, temp_password, send_email_func):
    """
    Send a password reset email to a user with their temporary password
    
    Args:
        user_email (str): The user's email address
        user_name (str): The user's full name
        temp_password (str): The temporary password
        send_email_func (function): The function to use for sending the email
        
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    email_subject = 'Your Password Has Been Reset'
    email_message = f"""
Dear {user_name},

Your account password has been reset by an administrator.

Your temporary password is: {temp_password}

Please log in using this temporary password. You will be required to set a new password after logging in.

Note: This is a temporary password and should be changed immediately for security reasons.

Thank you,
The DerVolt Team
"""
    
    return send_email_func(user_email, email_subject, email_message) 