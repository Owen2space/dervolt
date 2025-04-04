from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import requests
import json

from config import deriv_oauth_url

from deriv_functions import fetch_deriv_user_info, extract_tokens_from_url
from db_functions import save_user_info, get_user_by_id
from config import app_id

app = Flask(__name__)

app.secret_key = 'your_secret_key'  # Replace with a secure secret key in production


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    username = session.get('username')
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

        # Save the user information to the database
        db_success, db_message, account_login_id = save_user_info(user_data_dict, real_account)
        
        if not db_success:
            print(f"Database error: {db_message}")

        #create session
        session['user_id'] = account_login_id
        session['username'] = user_name
        # Redirect to the specified dashboard URL
        # return redirect("https://trail.dervolt.site/dashboard")
        return redirect(url_for('dashboard'))
    else:
        return json.dumps({
            "success": success,
            "error": user_data
        })
    
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    username = session.get('username')

    # print("profile",user_id, username)

    if not user_id:
        return redirect(url_for('index'))
    
    return jsonify({
        "success": True,
        "user_id": user_id,
        "username": username
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
