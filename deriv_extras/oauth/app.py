from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import requests
import json

from config import deriv_oauth_url

from deriv_functions import fetch_deriv_user_info, extract_tokens_from_url_1
from db_functions import save_user_info_1, get_user_by_id_1
from config import app_id

app = Flask(__name__)

app.secret_key = 'your_secret_key'  # Replace with a secure secret key in production



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/deriv_oauth')
def deriv_oauth():
    return redirect(deriv_oauth_url)

@app.route('/oauth/', methods=['GET'])
def oauth():
    full_url = request.url 
    query_string = full_url.split('/oauth/')[1]
    account_list = extract_tokens_from_url_1(query_string)
    real_account = account_list[1]
    print(account_list)
    
    success, user_data = fetch_deriv_user_info(real_account, app_id)
    # print(success, user_data)
    
    if success:
        # Convert the JSON string to a Python dictionary
        user_data_dict = json.loads(user_data)
        authorize_data = user_data_dict.get('authorize', {})
        user_name = authorize_data.get('fullname')
        user_id = authorize_data.get('loginid')

        print("id", user_id)

        #check if user exists
        if not user_id:
            return json.dumps({
                "success": False,
                "error": "User ID not found in the data"
            })
        
        #check if user exists in database
        user_info = get_user_by_id_1(user_id)

        print(user_info)
        if user_info:
            #create session
            session['user_id'] = user_id
            session['username'] = user_name
            # Redirect to the specified dashboard URL
            # return redirect("https://trail.dervolt.site/dashboard")
            return redirect(url_for('dashboard'))
        
        # Save the user information to the database
        db_success, db_message, user_id = save_user_info_1(user_data_dict)
        
        if not db_success:
            print(f"Database error: {db_message}")
            
        # return json.dumps({
        #     "success": success,
        #     "user_data": user_data_dict,
        #     "db_result": {
        #         "success": db_success,
        #         "message": db_message
        #     }
        # })

        #create session
        session['user_id'] = user_id
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

    print("profile",user_id, username)

    if not user_id:
        return redirect(url_for('index'))
    
    return jsonify({
        "success": True,
        "user_id": user_id,
        "username": username
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')


#https://oauth.deriv.com/oauth2/authorize?app_id=70905