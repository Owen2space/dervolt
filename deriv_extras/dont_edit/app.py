from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import requests
import json

from config import deriv_oauth_url

from deriv_functions import fetch_deriv_user_info, extract_tokens_from_url
from db_functions import save_user_info, get_user_by_id, get_user_by_email, set_user_password
from config import app_id

app = Flask(__name__)

app.secret_key = 'your_secret_key'  # Replace with a secure secret key in production


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    # print("user_id", user_id)
    if not user_id:
        return redirect(url_for('index'))
    username = session.get('username')
    
    # fetch user info from db
    user_info = get_user_by_id(user_id)
    # print("user_info", user_info)
    is_active = user_info[0]["is_active"]

    # Check if user is active
    if is_active == "0":
        return redirect(url_for('password_form'))
    
    
    return render_template('dashboard.html', user_id=user_id, username=username)

@app.route('/deriv_oauth')
def deriv_oauth():
    return redirect(deriv_oauth_url)

@app.route('/oauth/', methods=['GET'])
def oauth():
    full_url = request.url 
    query_string = full_url.split('/oauth/')[1]
    account_list = extract_tokens_from_url(query_string)
    real_account = account_list[1]
    # print("session_token", real_account)
    
    success, user_data = fetch_deriv_user_info(real_account)
    # print(success, user_data)

    user_exists = False
    
    if success:
        # Convert the JSON string to a Python dictionary
        user_data_dict = json.loads(user_data)
        authorize_data = user_data_dict.get('authorize', {})
        user_name = authorize_data.get('fullname')
        user_id = authorize_data.get('loginid')

        # print("id", user_id)
        if not user_id:
            return json.dumps({
                "success": False,
                "error": "User ID not found in the data"
            })
        
        # check if user is already in db
        user_info = get_user_by_id(user_id)
        if user_info:
            user_exists = True

        # Save the user information to the database
        db_success, db_message, account_login_id = save_user_info(user_data_dict, real_account)
        
        if not db_success:
            print(f"Database error: {db_message}")

        #create session
        session['user_id'] = account_login_id
        session['username'] = user_name

        if user_exists:
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('password_form'))
    else:
        return json.dumps({
            "success": success,
            "error": user_data
        })
    
@app.route('/login', methods=['GET'])
def login():
    user_id = session.get('user_id')
    if user_id:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/auth_login', methods=['POST'])
def login_password():
    data = request.get_json()
    login_email = data.get('email')
    password = data.get('password')
    
    if not login_email or not password:
        return jsonify({
            "success": False,
            "error": "User ID and password are required"
        })
    
    # Get user information from the database
    user_info = get_user_by_email(login_email)
    
    if not user_info:
        return jsonify({
            "success": False,
            "error": "User not found"
        })
    
    
    stored_password = user_info[0]["password"]
    user_id = user_info[0]["loginid_accountid"]
    
    # Simple password check (in a real app, use proper password hashing)
    if stored_password != password:
        return jsonify({
            "success": False,
            "error": "Wrong password"
        })
    
    # Set user session
    session['user_id'] = user_id
    session['username'] = user_info[0]["fullname"]
    
    return jsonify({
        "success": True,
        "message": f"Welcome back {session['username']}"
    })
    

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET'])
def profile():
    user_id = session.get('user_id')
    username = session.get('username')


    if not user_id:
        return redirect(url_for('index'))
    
    return jsonify({
        "success": True,
        "user_id": user_id,
        "username": username
    })

@app.route('/password_form')
def password_form():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    user_info = get_user_by_id(user_id)
    is_active = user_info[0]["is_active"]

    if is_active == "1":
        return redirect(url_for('dashboard'))
    

    return render_template('password_form.html')


@app.route('/set_password', methods=['POST'])
def set_password():
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if password != confirm_password:
        return jsonify({"success": False, "error": "Passwords do not match"})
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "User ID not found"})
    
    # update password in db
    success, message = set_user_password(user_id, password)
    if not success:
        return jsonify({"success": False, "error": message})
    
    return jsonify({"success": True, "message": "Password set successfully"})
    


if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
